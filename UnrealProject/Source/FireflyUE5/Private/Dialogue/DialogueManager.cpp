// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/DialogueManager.h"

#include "Animation/AnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieSceneSequencePlaybackSettings.h"
#include "UObject/SoftObjectPath.h"

namespace
{
    constexpr const TCHAR* GeneratedRoot = TEXT("/Game/Audio/Dialogue/Generated");
    constexpr const TCHAR* BodyComponentName = TEXT("Body");
    constexpr const TCHAR* IsSpeakingPropName = TEXT("IsSpeaking");
}

ADialogueManager::ADialogueManager()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ADialogueManager::BeginPlay()
{
    Super::BeginPlay();

    if (bPlayWelcomeOnBeginPlay && !WelcomeSpeaker.IsEmpty() && !WelcomeLineID.IsEmpty())
    {
        UE_LOG(LogTemp, Log, TEXT("[DialogueManager] BeginPlay welcome: %s / %s"),
            *WelcomeSpeaker, *WelcomeLineID);
        PlayLine(WelcomeSpeaker, WelcomeLineID);
    }
}

void ADialogueManager::PlayLine(const FString& SpeakerName, const FString& LineID)
{
    // Если уже играет — мягко завершить предыдущую (без Broadcast,
    // потому что новая реплика "проглатывает" старую).
    if (CurrentLSActor || CurrentSpeaker)
    {
        CleanupCurrentLine();
    }

    // Найти speaker actor.
    TObjectPtr<AActor>* SpeakerPtr = Speakers.Find(SpeakerName);
    if (!SpeakerPtr || !*SpeakerPtr)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] Unknown speaker '%s' (not in Speakers map)"), *SpeakerName);
        return;
    }
    AActor* Speaker = *SpeakerPtr;

    // Собрать путь и загрузить LS синхронно.
    const FString AssetName = FString::Printf(TEXT("LS_%s_%s"), *SpeakerName, *LineID);
    const FString FullPath = FString::Printf(TEXT("%s/%s/%s/%s"),
        GeneratedRoot, *SpeakerName, *LineID, *AssetName);

    FSoftObjectPath SoftPath(FullPath);
    UObject* LoadedObj = SoftPath.TryLoad();
    ULevelSequence* LS = Cast<ULevelSequence>(LoadedObj);
    if (!LS)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] Failed to load LevelSequence at '%s'"), *FullPath);
        return;
    }

    // Включить IsSpeaking на speaker (тело пойдёт в Talking state machine).
    SetSpeakerIsSpeaking(Speaker, true);

    // Spawn LevelSequencePlayer + Actor.
    FMovieSceneSequencePlaybackSettings PlaybackSettings;
    ALevelSequenceActor* SpawnedActor = nullptr;
    ULevelSequencePlayer* Player = ULevelSequencePlayer::CreateLevelSequencePlayer(
        GetWorld(), LS, PlaybackSettings, SpawnedActor);

    if (!Player || !SpawnedActor)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] CreateLevelSequencePlayer failed for '%s'"), *FullPath);
        SetSpeakerIsSpeaking(Speaker, false);
        return;
    }

    CurrentLSActor = SpawnedActor;
    CurrentSpeaker = Speaker;
    CurrentSpeakerName = SpeakerName;
    CurrentLineID = LineID;

    Player->OnFinished.AddDynamic(this, &ADialogueManager::HandleLSFinished);
    Player->Play();

    UE_LOG(LogTemp, Log, TEXT("[DialogueManager] PlayLine: speaker='%s' line='%s' path='%s'"),
        *SpeakerName, *LineID, *FullPath);
}

void ADialogueManager::StopCurrentLine()
{
    if (!CurrentLSActor && !CurrentSpeaker)
    {
        return;
    }

    const FString FinishedSpeaker = CurrentSpeakerName;
    const FString FinishedLineID = CurrentLineID;
    CleanupCurrentLine();
    OnLineFinished.Broadcast(FinishedSpeaker, FinishedLineID);
}

void ADialogueManager::HandleLSFinished()
{
    const FString FinishedSpeaker = CurrentSpeakerName;
    const FString FinishedLineID = CurrentLineID;

    UE_LOG(LogTemp, Log, TEXT("[DialogueManager] OnLineFinished: speaker='%s' line='%s'"),
        *FinishedSpeaker, *FinishedLineID);

    CleanupCurrentLine();
    OnLineFinished.Broadcast(FinishedSpeaker, FinishedLineID);
}

void ADialogueManager::CleanupCurrentLine()
{
    if (CurrentSpeaker)
    {
        SetSpeakerIsSpeaking(CurrentSpeaker, false);
        CurrentSpeaker = nullptr;
    }

    if (CurrentLSActor)
    {
        CurrentLSActor->Destroy();
        CurrentLSActor = nullptr;
    }

    CurrentSpeakerName.Empty();
    CurrentLineID.Empty();
}

void ADialogueManager::SetSpeakerIsSpeaking(AActor* Speaker, bool bValue)
{
    if (!Speaker)
    {
        return;
    }

    // Найти Body SkeletalMeshComponent — там крутится ABP_Crew (через Live
    // Retarget setup в BP_Cooper). Set Anim Class настраивается в runtime
    // через LiveRetargetSetup, поэтому в shipped/PIE Body.AnimInstance
    // имеет ABP_Crew_C class и переменную IsSpeaking.
    TArray<USkeletalMeshComponent*> SkelMeshes;
    Speaker->GetComponents<USkeletalMeshComponent>(SkelMeshes);

    for (USkeletalMeshComponent* SMC : SkelMeshes)
    {
        if (!SMC || SMC->GetName() != BodyComponentName)
        {
            continue;
        }

        UAnimInstance* AnimInst = SMC->GetAnimInstance();
        if (!AnimInst)
        {
            continue;
        }

        // Reflection-based set — works для BP-defined переменной без C++
        // base class. Trim-сравнение имён робастно к BP-quirk'ам типа
        // случайного trailing space в имени переменной (UE не нормализует
        // имена при создании variable в BP UI).
        UClass* AnimClass = AnimInst->GetClass();
        FString TargetName(IsSpeakingPropName);
        TargetName.TrimStartAndEndInline();

        FBoolProperty* BoolProp = nullptr;
        for (TFieldIterator<FBoolProperty> It(AnimClass); It; ++It)
        {
            FString CandidateName = It->GetName();
            CandidateName.TrimStartAndEndInline();
            if (CandidateName.Equals(TargetName, ESearchCase::IgnoreCase))
            {
                BoolProp = *It;
                break;
            }
        }

        if (BoolProp)
        {
            BoolProp->SetPropertyValue_InContainer(AnimInst, bValue);
        }
        else
        {
            UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] No bool property matching '%s' (case-insensitive, trimmed) on AnimInstance class '%s'"),
                IsSpeakingPropName, *AnimClass->GetName());
        }
        return;
    }

    UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] Speaker '%s' has no '%s' SkeletalMeshComponent"),
        *Speaker->GetName(), BodyComponentName);
}
