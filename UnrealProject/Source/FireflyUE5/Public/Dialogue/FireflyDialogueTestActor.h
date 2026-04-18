// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Dialogue/FireflyDialogueTypes.h"
#include "FireflyDialogueTestActor.generated.h"

class UDialogueClientComponent;

/**
 * Тест-актёр для end-to-end проверки dialogue pipeline.
 *
 * Поместите в любой уровень, нажмите Play — актёр:
 *   1. Вызовет /start у dialogue server'а (ollama:8765 по умолчанию).
 *   2. Распечатает opener-реплику от Мала в Output Log и на экран.
 *   3. Выберет первую опцию и вызовет /turn.
 *   4. Распечатает 2-3 реплики экипажа и опции.
 *   5. Напишет "=== PIPELINE OK ===" если всё прошло.
 *
 * Если server недоступен / ollama не запущен — увидите красное ERROR:.
 */
UCLASS(Blueprintable, BlueprintType, DisplayName = "Firefly Dialogue Test Actor")
class FIREFLYUE5_API AFireflyDialogueTestActor : public AActor
{
	GENERATED_BODY()

public:
	AFireflyDialogueTestActor();

	/** Если true — при BeginPlay сразу вызовет StartSession. Если false —
	 *  ждёт ручного вызова через blueprint / console. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Test")
	bool bAutoStartOnBeginPlay = true;

	/** Как много раундов прогнать автоматически после start (0 = только opener). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Test", Meta = (ClampMin = 0, ClampMax = 10))
	int32 AutoTurnsAfterStart = 1;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Firefly|Test")
	TObjectPtr<UDialogueClientComponent> DialogueClient;

protected:
	virtual void BeginPlay() override;

	UFUNCTION() void HandleSessionStarted(const FDialogueTurn& Opener);
	UFUNCTION() void HandleTurnReceived(const FDialogueTurn& Turn);
	UFUNCTION() void HandleError(const FString& Err);

private:
	int32 RemainingAutoTurns = 0;

	void PrintTurn(const FDialogueTurn& Turn, const FString& Label);
	void Print(const FString& Msg, const FColor& Color = FColor::Green) const;
};
