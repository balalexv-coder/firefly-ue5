// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Dialogue/FireflyDialogueTypes.h"
#include "FireflyDialogueHUDWidget.generated.h"

class UTextBlock;
class UButton;
class UPanelWidget;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnDialogueOptionPicked, int32, Index, const FString&, OptionText);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnLinePlaybackFinished);

/**
 * Базовый C++ HUD-виджет для диалоговой сцены.
 *
 * В WBP_DialogueHUD (наследник) положите на Canvas следующие виджеты с
 * ТАКИМИ ЖЕ именами (BindWidget подхватит их автоматически):
 *
 *     SpeakerNameText    : TextBlock  — имя говорящего
 *     SubtitleText       : TextBlock  — сам текст реплики (typewriter)
 *     OptionsContainer   : любой Panel (Vertical/HorizontalBox) — контейнер кнопок
 *     Option1Button      : Button
 *     Option2Button      : Button
 *     Option3Button      : Button
 *     Option1Text        : TextBlock  — текст внутри кнопки 1
 *     Option2Text        : TextBlock
 *     Option3Text        : TextBlock
 *
 * Есть опциональные:
 *     SpeakerPlate       : любой виджет  — контейнер имени+портрета (fade при смене)
 *     WaitingIndicator   : любой виджет  — крутилка «печатает...» (show/hide во время LLM)
 *
 * Внешнее API (вызывается из AFireflyDialogueFlowActor):
 *     PlayLine(speaker, text, estimated_ms)
 *     ShowOptions(TArray<FString>)
 *     ClearAll()
 *     SetWaiting(bool)
 */
UCLASS(Abstract, BlueprintType, Blueprintable, DisplayName = "Firefly Dialogue HUD")
class FIREFLYUE5_API UFireflyDialogueHUDWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	// ---------- Config ----------

	/** Символов в секунду для typewriter. 60 — комфортно. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|HUD")
	float TypewriterCharsPerSecond = 60.f;

	/** Пауза между окончанием реплики и появлением опций, сек. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|HUD")
	float PostLinePauseSeconds = 0.4f;

	// ---------- Events (bindable from BP / Actor) ----------

	UPROPERTY(BlueprintAssignable, Category = "Firefly|HUD")
	FOnDialogueOptionPicked OnOptionPicked;

	UPROPERTY(BlueprintAssignable, Category = "Firefly|HUD")
	FOnLinePlaybackFinished OnLineFinished;

	// ---------- Public API ----------

	/** Начать проигрывание реплики (typewriter). Бродкастит OnLineFinished через
	 *  max(EstimatedMs/1000, длительность typewriter + PostLinePauseSeconds). */
	UFUNCTION(BlueprintCallable, Category = "Firefly|HUD")
	void PlayLine(const FString& Speaker, const FString& Line, int32 EstimatedMs);

	UFUNCTION(BlueprintCallable, Category = "Firefly|HUD")
	void ShowOptions(const TArray<FString>& Options);

	UFUNCTION(BlueprintCallable, Category = "Firefly|HUD")
	void HideOptions();

	UFUNCTION(BlueprintCallable, Category = "Firefly|HUD")
	void ClearAll();

	UFUNCTION(BlueprintCallable, Category = "Firefly|HUD")
	void SetWaiting(bool bWaiting);

protected:
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MovedGeometry, float DeltaTime) override;

	// ---------- BindWidget (UMG will auto-fill these from WBP) ----------

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UTextBlock> SpeakerNameText;

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UTextBlock> SubtitleText;

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UPanelWidget> OptionsContainer;

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UButton> Option1Button;
	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UButton> Option2Button;
	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UButton> Option3Button;

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UTextBlock> Option1Text;
	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UTextBlock> Option2Text;
	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidget))
	TObjectPtr<UTextBlock> Option3Text;

	/** Опционально. Если есть — прячем при SetWaiting(false). */
	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidgetOptional))
	TObjectPtr<UPanelWidget> WaitingIndicator;

	UPROPERTY(BlueprintReadOnly, Category = "Firefly|HUD", Meta = (BindWidgetOptional))
	TObjectPtr<UPanelWidget> SpeakerPlate;

private:
	UFUNCTION() void HandleOption1();
	UFUNCTION() void HandleOption2();
	UFUNCTION() void HandleOption3();
	void PickOption(int32 Index);

	TArray<FString> CurrentOptions;

	// Typewriter state
	FString FullLine;
	float   TypewriterAccum = 0.f;
	int32   LastVisibleCount = 0;
	bool    bIsTyping = false;

	// Line scheduling
	FTimerHandle FinishedTimer;
	void BroadcastLineFinished();
};
