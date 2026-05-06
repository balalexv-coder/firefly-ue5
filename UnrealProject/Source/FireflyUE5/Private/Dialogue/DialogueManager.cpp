// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/DialogueManager.h"

#include "Animation/AnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieSceneSequencePlaybackSettings.h"
#include "ReferenceSkeleton.h"
#include "UObject/SoftObjectPath.h"

namespace
{
    constexpr const TCHAR* GeneratedRoot = TEXT("/Game/Audio/Dialogue/Generated");
    constexpr const TCHAR* BodyComponentName = TEXT("Body");
    constexpr const TCHAR* IsSpeakingPropName = TEXT("IsSpeaking");
    constexpr const TCHAR* HeadRotationPropName = TEXT("HeadRotationCS");
    constexpr const TCHAR* HeadBoneName = TEXT("head");
    constexpr float MaxYawDegrees = 179.f;   // effectively no clamp — debug
    constexpr float MaxPitchDegrees = 89.f;  // effectively no clamp — debug
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
        PlayLine(WelcomeSpeaker, WelcomeLineID, TArray<FString>());
    }
}

void ADialogueManager::PlayLine(const FString& SpeakerName, const FString& LineID,
                                const TArray<FString>& Addressees)
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
    CurrentAddressees = Addressees;

    // Направить взгляд всех слушателей на текущего speaker'а,
    // и говорящего — на первого адресата.
    UpdateListenerLookAtTargets();

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
    // Сбросить look-at у всех слушателей до того как обнулим CurrentSpeaker.
    ClearAllLookAtTargets();

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
    CurrentAddressees.Reset();
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

USkeletalMeshComponent* ADialogueManager::GetBodySkeletalMeshComponent(AActor* Actor) const
{
    if (!Actor) return nullptr;
    TArray<USkeletalMeshComponent*> SkelMeshes;
    Actor->GetComponents<USkeletalMeshComponent>(SkelMeshes);
    for (USkeletalMeshComponent* SMC : SkelMeshes)
    {
        if (SMC && SMC->GetName() == BodyComponentName)
        {
            return SMC;
        }
    }
    return nullptr;
}

// Вернуть Component Space rotation head bone'а в bind pose (reference skeleton).
// Не зависит от текущей анимации — это «нейтральная» ориентация head, к которой
// мы будем применять delta rotation чтобы повернуть head в направлении target.
static FQuat ComputeHeadBindPoseRotationCS(USkeletalMeshComponent* SMC, FName BoneName)
{
    if (!SMC) return FQuat::Identity;
    USkeletalMesh* SkelMesh = SMC->GetSkeletalMeshAsset();
    if (!SkelMesh) return FQuat::Identity;

    const FReferenceSkeleton& RefSkel = SkelMesh->GetRefSkeleton();
    int32 BoneIdx = RefSkel.FindBoneIndex(BoneName);
    if (BoneIdx == INDEX_NONE) return FQuat::Identity;

    const TArray<FTransform>& RefPose = RefSkel.GetRefBonePose();

    // Composed CS bind transform = product of all parent bind transforms.
    FTransform Composed = FTransform::Identity;
    while (BoneIdx != INDEX_NONE)
    {
        Composed = RefPose[BoneIdx] * Composed;
        BoneIdx = RefSkel.GetParentIndex(BoneIdx);
    }
    return Composed.GetRotation();
}

// Вычислить FRotator для head bone актёра, чтобы он смотрел на TargetWS.
// Возвращает rotation в Component Space с учётом bind pose + clamp pitch/yaw.
static FRotator ComputeHeadLookAtRotation(
    USkeletalMeshComponent* ActorSMC,
    const FVector& TargetWS,
    const FQuat& BindRotCS,
    float MaxYawDeg,
    float MaxPitchDeg,
    FName HeadBone,
    FVector& OutToTargetCS,
    float& OutYawDeg,
    float& OutPitchDeg)
{
    // Преобразуем target и head в Component Space актёра.
    const FVector TargetCS =
        ActorSMC->GetComponentTransform().InverseTransformPosition(TargetWS);
    const FVector HeadCS = ActorSMC->GetSocketTransform(
        HeadBone, RTS_Component
    ).GetLocation();

    FVector ToTargetCS = (TargetCS - HeadCS).GetSafeNormal();
    OutToTargetCS = ToTargetCS;
    if (ToTargetCS.IsNearlyZero())
    {
        OutYawDeg = 0.f; OutPitchDeg = 0.f;
        return BindRotCS.Rotator();
    }

    // Mesh visual forward axis в actor frame повёрнут на +90° вокруг Z
    // (mesh forward совпадает с actor +Y). Yaw — относительно mesh forward.
    const float YawDegRaw = FMath::RadiansToDegrees(
        FMath::Atan2(-ToTargetCS.X, ToTargetCS.Y));
    const float HorizontalLen = FMath::Sqrt(
        ToTargetCS.X * ToTargetCS.X + ToTargetCS.Y * ToTargetCS.Y);
    const float PitchDegRaw = FMath::RadiansToDegrees(
        FMath::Atan2(ToTargetCS.Z, HorizontalLen));

    const float YawDeg = FMath::Clamp(YawDegRaw, -MaxYawDeg, MaxYawDeg);
    const float PitchDeg = FMath::Clamp(PitchDegRaw, -MaxPitchDeg, MaxPitchDeg);
    OutYawDeg = YawDeg;
    OutPitchDeg = PitchDeg;

    const float YawRad = FMath::DegreesToRadians(YawDeg);
    const float PitchRad = FMath::DegreesToRadians(PitchDeg);
    const FVector ClampedDirCS(
        -FMath::Cos(PitchRad) * FMath::Sin(YawRad),
         FMath::Cos(PitchRad) * FMath::Cos(YawRad),
         FMath::Sin(PitchRad));

    const FVector MeshForwardCS(0.f, 1.f, 0.f);
    const FQuat DeltaQuat =
        FQuat::FindBetweenNormals(MeshForwardCS, ClampedDirCS);

    const FQuat FinalQuat = DeltaQuat * BindRotCS;
    return FinalQuat.Rotator();
}

void ADialogueManager::UpdateListenerLookAtTargets()
{
    if (!CurrentSpeaker)
    {
        return;
    }

    USkeletalMeshComponent* SpeakerSMC = GetBodySkeletalMeshComponent(CurrentSpeaker);
    if (!SpeakerSMC)
    {
        UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] LookAt: speaker '%s' has no Body SMC"),
            *CurrentSpeaker->GetName());
        return;
    }
    const FVector SpeakerHeadWS = SpeakerSMC->GetSocketLocation(FName(HeadBoneName));

    // Выбрать target для самого говорящего: head bone первого адресата.
    AActor* SpeakerLookAtActor = nullptr;
    FString SpeakerTargetName;
    for (const FString& Addressee : CurrentAddressees)
    {
        TObjectPtr<AActor>* Found = Speakers.Find(Addressee);
        if (Found && *Found && *Found != CurrentSpeaker)
        {
            SpeakerLookAtActor = *Found;
            SpeakerTargetName = Addressee;
            break;
        }
    }

    for (auto& Pair : Speakers)
    {
        AActor* Listener = Pair.Value;
        if (!Listener)
        {
            continue;
        }

        USkeletalMeshComponent* ListenerSMC = GetBodySkeletalMeshComponent(Listener);
        if (!ListenerSMC)
        {
            continue;
        }

        const FQuat BindRotCS =
            ComputeHeadBindPoseRotationCS(ListenerSMC, FName(HeadBoneName));

        // Определяем target: для говорящего — first addressee, для остальных — speaker.
        AActor* TargetActor = nullptr;
        FString TargetName;
        if (Listener == CurrentSpeaker)
        {
            TargetActor = SpeakerLookAtActor;
            TargetName = SpeakerTargetName;
            if (!TargetActor)
            {
                // Нет адресата (или addressee == self) — голова в нейтрали.
                SetSpeakerHeadRotation(Listener, BindRotCS.Rotator());
                continue;
            }
        }
        else
        {
            TargetActor = CurrentSpeaker;
            TargetName = CurrentSpeakerName;
        }

        // Получаем head bone target'а в world space.
        USkeletalMeshComponent* TargetSMC = GetBodySkeletalMeshComponent(TargetActor);
        if (!TargetSMC) { continue; }
        const FVector TargetHeadWS = TargetSMC->GetSocketLocation(FName(HeadBoneName));

        FVector OutToTargetCS;
        float OutYaw, OutPitch;
        const FRotator HeadRot = ComputeHeadLookAtRotation(
            ListenerSMC, TargetHeadWS, BindRotCS,
            MaxYawDegrees, MaxPitchDegrees, FName(HeadBoneName),
            OutToTargetCS, OutYaw, OutPitch);

        UE_LOG(LogTemp, Log,
            TEXT("[LookAt] %s -> %s ToTargetCS=(%.1f,%.1f,%.1f) yaw=%.1f pitch=%.1f"),
            *Listener->GetName(), *TargetActor->GetName(),
            OutToTargetCS.X, OutToTargetCS.Y, OutToTargetCS.Z,
            OutYaw, OutPitch);

        SetSpeakerHeadRotation(Listener, HeadRot);
    }
}

void ADialogueManager::ClearAllLookAtTargets()
{
    // Каждому ставим bind pose CS rotation — head в нейтральной позиции
    // (как если бы Modify Bone не работал, но animation тоже не overrides head).
    for (auto& Pair : Speakers)
    {
        AActor* Listener = Pair.Value;
        if (!Listener) continue;

        USkeletalMeshComponent* SMC = GetBodySkeletalMeshComponent(Listener);
        if (!SMC) continue;

        const FQuat BindRotCS =
            ComputeHeadBindPoseRotationCS(SMC, FName(HeadBoneName));
        SetSpeakerHeadRotation(Listener, BindRotCS.Rotator());
    }
}

void ADialogueManager::SetSpeakerHeadRotation(AActor* Listener, const FRotator& RotationCS)
{
    if (!Listener) return;
    USkeletalMeshComponent* SMC = GetBodySkeletalMeshComponent(Listener);
    if (!SMC) return;
    UAnimInstance* AnimInst = SMC->GetAnimInstance();
    if (!AnimInst) return;

    // Reflection: FStructProperty с UScriptStruct == FRotator и нужным именем.
    UClass* AnimClass = AnimInst->GetClass();
    FString TargetName(HeadRotationPropName);
    TargetName.TrimStartAndEndInline();

    UScriptStruct* RotatorStruct = TBaseStructure<FRotator>::Get();
    FStructProperty* RotProp = nullptr;
    for (TFieldIterator<FStructProperty> It(AnimClass); It; ++It)
    {
        if (It->Struct != RotatorStruct)
        {
            continue;
        }
        FString CandidateName = It->GetName();
        CandidateName.TrimStartAndEndInline();
        if (CandidateName.Equals(TargetName, ESearchCase::IgnoreCase))
        {
            RotProp = *It;
            break;
        }
    }

    if (RotProp)
    {
        RotProp->CopyCompleteValue(RotProp->ContainerPtrToValuePtr<void>(AnimInst), &RotationCS);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("[DialogueManager] No FRotator property '%s' on AnimInstance class '%s' (listener '%s')"),
            HeadRotationPropName, *AnimClass->GetName(), *Listener->GetName());
    }
}
