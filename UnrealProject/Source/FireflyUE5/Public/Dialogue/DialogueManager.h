// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DialogueManager.generated.h"

class ULevelSequence;
class ALevelSequenceActor;
class ULevelSequencePlayer;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnLineFinishedSignature, const FString&, SpeakerName, const FString&, LineID);

/**
 * Воспроизводит одну dialogue line: загружает соответствующий LevelSequence
 * по конвенции пути `/Game/Audio/Dialogue/Generated/<Speaker>/<LineID>/LS_<Speaker>_<LineID>`,
 * включает `IsSpeaking=true` на ABP_Crew speaker'а, играет LS, по окончании
 * выключает IsSpeaking, разрушает spawned LevelSequenceActor и стреляет OnLineFinished.
 *
 * Замена BP_DialogueManager BP-логики (Switch on String + Cast + Bind Event +
 * SET IsSpeaking + Create LSP + Play + OnFinished обратка) одним C++ методом.
 *
 * Размещение: один экземпляр на уровне (например в L_SerenityCabin). В
 * Details задайте Speakers map: "Mal" → Mal_MetaHuman, "Zoe" → BP_Zoe и т.д.
 */
UCLASS(Blueprintable, BlueprintType, DisplayName = "Firefly Dialogue Manager")
class FIREFLYUE5_API ADialogueManager : public AActor
{
    GENERATED_BODY()

public:
    ADialogueManager();

    /** Map имени speaker'а (как в LLM JSON: "Mal"/"Zoe"/"Wash"/"Inara") → actor в сцене. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    TMap<FString, TObjectPtr<AActor>> Speakers;

    /**
     * Проиграть dialogue line. Загружает LS по пути
     * `/Game/Audio/Dialogue/Generated/<SpeakerName>/<LineID>/LS_<SpeakerName>_<LineID>`,
     * включает IsSpeaking=true на ABP_Crew speaker'а, играет, на финише
     * выключает IsSpeaking + cleanup'ит spawned actor + Broadcast OnLineFinished.
     *
     * Если уже играет другая реплика — сначала завершает её принудительно.
     */
    UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
    void PlayLine(const FString& SpeakerName, const FString& LineID);

    /** Принудительно остановить текущее воспроизведение (если есть). */
    UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
    void StopCurrentLine();

    /** Стреляет когда LS реплики закончилась (или была остановлена). */
    UPROPERTY(BlueprintAssignable, Category = "Firefly|Dialogue")
    FOnLineFinishedSignature OnLineFinished;

protected:
    UFUNCTION()
    void HandleLSFinished();

private:
    /** Текущий проигрываемый LevelSequenceActor (для cleanup'а). */
    UPROPERTY()
    TObjectPtr<ALevelSequenceActor> CurrentLSActor;

    /** Текущий speaker (для сброса IsSpeaking на финише). */
    UPROPERTY()
    TObjectPtr<AActor> CurrentSpeaker;

    /** Имя текущего speaker'а — отдаётся в OnLineFinished. */
    FString CurrentSpeakerName;

    /** Текущий line ID — отдаётся в OnLineFinished. */
    FString CurrentLineID;

    /** Установить bool-переменную IsSpeaking на ABP_Crew (Body component) speaker'а. */
    void SetSpeakerIsSpeaking(AActor* Speaker, bool bValue);

    /** Cleanup current line state (без Broadcast). */
    void CleanupCurrentLine();
};
