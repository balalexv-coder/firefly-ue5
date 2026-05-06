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
     * Yaw offset (degrees) от actor +X axis до character VISUAL forward.
     * MetaHuman + Sitting_Talking_v2 anim обычно даёт +90° (mesh визуально
     * faces actor +Y direction). Если у конкретного actor'а другая bind pose
     * orientation (например, Cooper body imported с другим rotation чем
     * Kristofer) — добавь override в SpeakerYawOffsetOverride с его именем.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    float DefaultMeshForwardYawOffset = 90.f;

    /**
     * Per-speaker override для yaw offset. Ключ = имя speaker'а ("Mal"/"Zoe"/...).
     * Если empty — используется DefaultMeshForwardYawOffset. Если есть — используется
     * заданное значение для этого speaker'а.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    TMap<FString, float> SpeakerYawOffsetOverride;

    /**
     * Если true — на BeginPlay автоматически проигрывает приветственную
     * реплику (WelcomeSpeaker / WelcomeLineID). Полезно как smoke-test
     * audio системы перед тем как ждать LLM. По умолчанию OFF — LLM
     * opener из FireflyDialogueFlow всё равно играет первой репликой
     * демо-пула, дополнительный welcome дублирует.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    bool bPlayWelcomeOnBeginPlay = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    FString WelcomeSpeaker = TEXT("Mal");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
    FString WelcomeLineID = TEXT("intro_atmo");

    /**
     * Проиграть dialogue line. Загружает LS по пути
     * `/Game/Audio/Dialogue/Generated/<SpeakerName>/<LineID>/LS_<SpeakerName>_<LineID>`,
     * включает IsSpeaking=true на ABP_Crew speaker'а, играет, на финише
     * выключает IsSpeaking + cleanup'ит spawned actor + Broadcast OnLineFinished.
     *
     * Addressees — кому обращена реплика (имена speaker'ов из Speakers map).
     * Говорящий поворачивает голову в сторону первого адресата из массива.
     * Если массив пустой — голова в нейтральной позиции (прямо).
     *
     * Если уже играет другая реплика — сначала завершает её принудительно.
     */
    UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
    void PlayLine(const FString& SpeakerName, const FString& LineID,
                  const TArray<FString>& Addressees);

    /** Принудительно остановить текущее воспроизведение (если есть). */
    UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
    void StopCurrentLine();

    /** Стреляет когда LS реплики закончилась (или была остановлена). */
    UPROPERTY(BlueprintAssignable, Category = "Firefly|Dialogue")
    FOnLineFinishedSignature OnLineFinished;

protected:
    virtual void BeginPlay() override;

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

    /** Кому обращена текущая реплика — говорящий смотрит на первого из них. */
    TArray<FString> CurrentAddressees;

    /** Установить bool-переменную IsSpeaking на ABP_Crew (Body component) speaker'а. */
    void SetSpeakerIsSpeaking(AActor* Speaker, bool bValue);

    /** Cleanup current line state (без Broadcast). */
    void CleanupCurrentLine();

    /**
     * Для каждого слушателя посчитать FRotator (Pitch, Yaw) который повернёт
     * его head bone в направлении CurrentSpeaker'а — вычисление чисто
     * тригонометрическое в Component Space, не зависит от bone axis convention.
     * Yaw clamp'ится до ±60°, Pitch до ±30° — чтобы голова не сворачивалась
     * сверх естественного диапазона. Записывает в ABP_Crew переменную
     * `HeadRotationCS` (FRotator).
     *
     * Сам говорящий получает (0,0,0) — голова прямо вперёд.
     */
    void UpdateListenerLookAtTargets();

    /** Сбросить HeadRotationCS у всех в (0,0,0) — после окончания реплики. */
    void ClearAllLookAtTargets();

    /** Найти Body SkeletalMeshComponent у actor'а (по имени "Body"). */
    class USkeletalMeshComponent* GetBodySkeletalMeshComponent(AActor* Actor) const;

    /** Reflection setter для FRotator BP-переменной HeadRotationCS. */
    void SetSpeakerHeadRotation(AActor* Listener, const FRotator& RotationCS);
};
