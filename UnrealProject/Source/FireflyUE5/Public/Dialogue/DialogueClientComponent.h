// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Interfaces/IHttpRequest.h"
#include "Dialogue/FireflyDialogueTypes.h"
#include "DialogueClientComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDialogueSessionStarted, const FDialogueTurn&, Opener);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDialogueTurnReceived,   const FDialogueTurn&, Turn);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDialogueError,          const FString&,        ErrorMessage);

/**
 * Actor Component: HTTP-клиент dialogue server'а + состояние сессии.
 *
 * Общий сценарий использования в BP_CabinFlow:
 *   BeginPlay → StartSession() → OnSessionStarted → показать opener → показать варианты
 *   (игрок нажимает) → SubmitChoice(text) → OnTurnReceived → проиграть реплики → показать варианты
 *   ... пока Turn.bContinue == false → TransitionToLanding()
 */
UCLASS(ClassGroup = (Firefly), Meta = (BlueprintSpawnableComponent))
class FIREFLYUE5_API UDialogueClientComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDialogueClientComponent();

	/** Базовый URL сервера, без trailing slash. Например http://127.0.0.1:8765 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
	FString ServerBaseUrl = TEXT("http://127.0.0.1:8765");

	/** Таймаут HTTP-запроса, сек. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Dialogue")
	float HttpTimeoutSeconds = 30.f;

	// ---------- Events ----------

	UPROPERTY(BlueprintAssignable, Category = "Firefly|Dialogue")
	FOnDialogueSessionStarted OnSessionStarted;

	UPROPERTY(BlueprintAssignable, Category = "Firefly|Dialogue")
	FOnDialogueTurnReceived OnTurnReceived;

	UPROPERTY(BlueprintAssignable, Category = "Firefly|Dialogue")
	FOnDialogueError OnError;

	// ---------- Actions ----------

	/** POST /start → opener + 3 опции. */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
	void StartSession();

	/** POST /turn с выбранным текстом. */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
	void SubmitChoice(const FString& ChoiceText);

	/** POST /turn без новой реплики игрока (редко, для «пропустить раунд»). */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
	void RequestNextTurn();

	/** Сбрасывает сессию. */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
	void ResetSession();

	// ---------- State ----------

	UFUNCTION(BlueprintPure, Category = "Firefly|Dialogue")
	const TArray<FDialogueLine>& GetHistory() const { return History; }

	UFUNCTION(BlueprintPure, Category = "Firefly|Dialogue")
	float GetOrbitProgress() const { return OrbitProgress; }

	/** Перезаписать прогресс (вызывается из BP_CabinFlow после каждого раунда). */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Dialogue")
	void SetOrbitProgress(float NewProgress);

protected:
	virtual void BeginPlay() override;

private:
	/** Session id, возвращён сервером в /start. */
	FString SessionId;

	/** Полная история реплик (и экипажа, и игрока). */
	UPROPERTY() TArray<FDialogueLine> History;

	/** [0..1] — сколько «пройдено» по пути к атмосфере. */
	float OrbitProgress = 0.f;

	// ---------- HTTP internals ----------

	void Post(const FString& Endpoint, const TSharedRef<FJsonObject>& Body,
	          TFunction<void(TSharedPtr<FJsonObject>)> OnSuccess);

	TSharedRef<FJsonObject> BuildTurnBody(const FString& PlayerChoice) const;

	void HandleStartResponse(TSharedPtr<FJsonObject> JsonBody);
	void HandleTurnResponse(TSharedPtr<FJsonObject> JsonBody);

	static bool ParseLine(const TSharedPtr<FJsonObject>& Obj, FDialogueLine& Out);
	static bool ParseTurn(const TSharedPtr<FJsonObject>& Obj, FDialogueTurn& Out);
};
