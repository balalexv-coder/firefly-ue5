// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Dialogue/FireflyDialogueTypes.h"
#include "FireflyDialogueFlowActor.generated.h"

class UDialogueClientComponent;
class UFireflyDialogueHUDWidget;

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

	/** Сколько орбит-прогресса добавляется за один раунд (0..1 за сессию). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Flow", Meta = (ClampMin = "0.01", ClampMax = "1.0"))
	float OrbitProgressPerTurn = 0.15f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Firefly|Flow")
	TObjectPtr<UDialogueClientComponent> DialogueClient;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Firefly|Flow")
	TObjectPtr<UFireflyDialogueHUDWidget> HUDWidget;

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

private:
	TArray<FDialogueLine> PendingLines;
	TArray<FString>       PendingOptions;
	bool                  bLastContinue = true;

	void PlayNextLineOrShowOptions();
	void SetupHUD();
};
