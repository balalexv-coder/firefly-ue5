// Copyright (c) 2026 balalexv. MIT License.

#include "UI/FireflyDialogueHUDWidget.h"
#include "FireflyUE5.h"
#include "Components/TextBlock.h"
#include "Components/Button.h"
#include "Components/PanelWidget.h"
#include "TimerManager.h"

namespace
{
	constexpr int32 kMaxOptions = 3;
}

void UFireflyDialogueHUDWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (Option1Button) Option1Button->OnClicked.AddDynamic(this, &UFireflyDialogueHUDWidget::HandleOption1);
	if (Option2Button) Option2Button->OnClicked.AddDynamic(this, &UFireflyDialogueHUDWidget::HandleOption2);
	if (Option3Button) Option3Button->OnClicked.AddDynamic(this, &UFireflyDialogueHUDWidget::HandleOption3);

	HideOptions();
	SetWaiting(false);
	if (SpeakerNameText) SpeakerNameText->SetText(FText::GetEmpty());
	if (SubtitleText)    SubtitleText->SetText(FText::GetEmpty());
}

void UFireflyDialogueHUDWidget::NativeDestruct()
{
	if (UWorld* World = GetWorld())
		World->GetTimerManager().ClearTimer(FinishedTimer);
	Super::NativeDestruct();
}

void UFireflyDialogueHUDWidget::NativeTick(const FGeometry& MovedGeometry, float DeltaTime)
{
	Super::NativeTick(MovedGeometry, DeltaTime);

	if (!bIsTyping || !SubtitleText) return;

	TypewriterAccum += DeltaTime * TypewriterCharsPerSecond;
	const int32 Target = FMath::Min(FullLine.Len(), FMath::FloorToInt(TypewriterAccum));
	if (Target > LastVisibleCount)
	{
		LastVisibleCount = Target;
		SubtitleText->SetText(FText::FromString(FullLine.Left(Target)));
	}
	if (LastVisibleCount >= FullLine.Len())
		bIsTyping = false;
}

void UFireflyDialogueHUDWidget::PlayLine(const FString& Speaker, const FString& Line, int32 EstimatedMs)
{
	if (SpeakerNameText) SpeakerNameText->SetText(FText::FromString(Speaker));
	if (SubtitleText)    SubtitleText->SetText(FText::GetEmpty());

	FullLine = Line;
	TypewriterAccum = 0.f;
	LastVisibleCount = 0;
	bIsTyping = !Line.IsEmpty();

	const float TypeSeconds = (TypewriterCharsPerSecond > 0)
		? (Line.Len() / TypewriterCharsPerSecond)
		: 0.f;
	const float EstSeconds = FMath::Max(0.f, EstimatedMs / 1000.f);
	const float WaitSeconds = FMath::Max(EstSeconds, TypeSeconds) + PostLinePauseSeconds;

	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(FinishedTimer);
		World->GetTimerManager().SetTimer(FinishedTimer, this,
			&UFireflyDialogueHUDWidget::BroadcastLineFinished,
			FMath::Max(WaitSeconds, 0.2f), false);
	}
}

void UFireflyDialogueHUDWidget::ShowOptions(const TArray<FString>& Options)
{
	CurrentOptions = Options;
	UTextBlock* OptionTexts[kMaxOptions] = { Option1Text, Option2Text, Option3Text };
	UButton*    OptionBtns [kMaxOptions] = { Option1Button, Option2Button, Option3Button };

	for (int32 i = 0; i < kMaxOptions; ++i)
	{
		const bool bHas = Options.IsValidIndex(i);
		if (OptionBtns[i])
		{
			OptionBtns[i]->SetVisibility(bHas ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
			OptionBtns[i]->SetIsEnabled(bHas);
		}
		if (OptionTexts[i])
		{
			OptionTexts[i]->SetText(bHas ? FText::FromString(Options[i]) : FText::GetEmpty());
		}
	}
	if (OptionsContainer)
		OptionsContainer->SetVisibility(ESlateVisibility::Visible);
}

void UFireflyDialogueHUDWidget::HideOptions()
{
	if (OptionsContainer)
		OptionsContainer->SetVisibility(ESlateVisibility::Hidden);

	UButton* OptionBtns[kMaxOptions] = { Option1Button, Option2Button, Option3Button };
	for (int32 i = 0; i < kMaxOptions; ++i)
	{
		if (OptionBtns[i]) OptionBtns[i]->SetIsEnabled(false);
	}
}

void UFireflyDialogueHUDWidget::ClearAll()
{
	if (SpeakerNameText) SpeakerNameText->SetText(FText::GetEmpty());
	if (SubtitleText)    SubtitleText->SetText(FText::GetEmpty());
	HideOptions();
	SetWaiting(false);
	bIsTyping = false;
	FullLine.Reset();
	CurrentOptions.Reset();
	if (UWorld* World = GetWorld())
		World->GetTimerManager().ClearTimer(FinishedTimer);
}

void UFireflyDialogueHUDWidget::SetWaiting(bool bWaiting)
{
	if (WaitingIndicator)
	{
		WaitingIndicator->SetVisibility(bWaiting ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
	}
}

void UFireflyDialogueHUDWidget::HandleOption1() { PickOption(0); }
void UFireflyDialogueHUDWidget::HandleOption2() { PickOption(1); }
void UFireflyDialogueHUDWidget::HandleOption3() { PickOption(2); }

void UFireflyDialogueHUDWidget::PickOption(int32 Index)
{
	if (!CurrentOptions.IsValidIndex(Index)) return;
	const FString Text = CurrentOptions[Index];
	HideOptions();
	OnOptionPicked.Broadcast(Index, Text);
}

void UFireflyDialogueHUDWidget::BroadcastLineFinished()
{
	bIsTyping = false;
	OnLineFinished.Broadcast();
}
