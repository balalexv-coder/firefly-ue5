// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Dialogue/FireflyDialogueTypes.h"
#include "FireflyDialogueFlowActor.generated.h"

class UDialogueClientComponent;
class UFireflyDialogueHUDWidget;
class ADialogueManager;

/**
 * Мастер-актёр диалоговой сцены.
 *
 *   1. Спавнит HUD-виджет (HUDWidgetClass), показывает в Viewport.
 *   2. Стартует сессию через UDialogueClientComponent.
 *   3. По OnSessionStarted/OnTurnReceived — проигрывает реплики последовательно
 *      через HUD (PlayLine → ждём OnLineFinished → следующая).
 *   4. После последней реплики — HUD.ShowOptions(...) ждёт клика игрока.
 *   5. HUD.OnOptionPicked → SubmitChoice и по новой.
 *   6. Если сервер вернёт continue=false — просто прячет HUD (позже —
 *      триггерит TransitionToLanding).
 *
 * Поместите в уровень, в Details задайте HUDWidgetClass = WBP_DialogueHUD.
 */
UCLASS(Blueprintable, BlueprintType, DisplayName = "Firefly Dialogue Flow")
class FIREFLYUE5_API AFireflyDialogueFlowActor : public AActor
{
	GENERATED_BODY()

public:
	AFireflyDialogueFlowActor();

	/** Класс виджета HUD. Ставьте сюда WBP_DialogueHUD (наследник UFireflyDialogueHUDWidget). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow")
	TSubclassOf<UFireflyDialogueHUDWidget> HUDWidgetClass;

	/** Стартовать сессию автоматически на BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow")
	bool bAutoStartOnBeginPlay = true;

	/**
	 * Скриптованный demo-режим: при BeginPlay сразу проигрывает фиксированную
	 * последовательность реплик из pre-gen pool без обращения к LLM-серверу.
	 * Удобно для демо-сценок и smoke-теста аудио/жестов без задержки на LLM.
	 *
	 * Реплики берутся из ScriptedDemoLines (заполняется по умолчанию в
	 * конструкторе восемью реплицами Mal/Zoe/Wash/Inara из pre-gen demo pool).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow")
	bool bUseScriptedDemo = false;

	/** Прошитая очередь реплик для bUseScriptedDemo. По умолчанию 8 demo lines. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow")
	TArray<FDialogueLine> ScriptedDemoLines;

	/** Сколько орбит-прогресса добавляется за один раунд (0..1 за сессию). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow", Meta = (ClampMin = "0.01", ClampMax = "1.0"))
	float OrbitProgressPerTurn = 0.15f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Firefly|Flow")
	TObjectPtr<UDialogueClientComponent> DialogueClient;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Firefly|Flow")
	TObjectPtr<UFireflyDialogueHUDWidget> HUDWidget;

	/**
	 * Опциональная ссылка на ADialogueManager в сцене. Если задан и у line
	 * есть LineID — реплика проигрывается через LS playback (lipsync + body
	 * gesture) ВМЕСТО HUD-only текстового режима. HUD всё равно показывает
	 * субтитры. Установи в Outliner Details для BP_DialogueFlowActor.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow")
	TObjectPtr<ADialogueManager> DialogueManager;

	/** Вызвать ручной старт, если bAutoStartOnBeginPlay=false. */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Flow")
	void StartDialogue();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	UFUNCTION() void HandleSessionStarted(const FDialogueTurn& Opener);
	UFUNCTION() void HandleTurnReceived(const FDialogueTurn& Turn);
	UFUNCTION() void HandleError(const FString& Err);

	UFUNCTION() void HandleLineFinished();
	UFUNCTION() void HandleOptionPicked(int32 Index, const FString& OptionText);

	/** Обработчик OnLineFinished от ADialogueManager (LS закончила играть). */
	UFUNCTION() void HandleDialogueManagerLineFinished(const FString& Speaker, const FString& LineID);

private:
	TArray<FDialogueLine> PendingLines;
	TArray<FString>       PendingOptions;
	bool                  bLastContinue = true;

	/**
	 * true когда сейчас играет LS через DialogueManager. Используется
	 * чтобы игнорировать HUD's OnLineFinished таймер (он стреляет через
	 * 0.2с на DurationMs=0) и ждать настоящий финиш от LS playback.
	 */
	bool                  bWaitingForLSFinish = false;

	void PlayNextLineOrShowOptions();
	void SetupHUD();
};
