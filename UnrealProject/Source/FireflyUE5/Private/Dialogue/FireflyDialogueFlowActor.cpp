// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/FireflyDialogueFlowActor.h"
#include "FireflyUE5.h"
#include "Dialogue/DialogueClientComponent.h"
#include "UI/FireflyDialogueHUDWidget.h"
#include "Blueprint/UserWidget.h"
#include "Engine/Engine.h"

AFireflyDialogueFlowActor::AFireflyDialogueFlowActor()
{
	PrimaryActorTick.bCanEverTick = false;
	DialogueClient = CreateDefaultSubobject<UDialogueClientComponent>(TEXT("DialogueClient"));
}

void AFireflyDialogueFlowActor::BeginPlay()
{
	Super::BeginPlay();

	if (!DialogueClient)
	{
		UE_LOG(LogFirefly, Error, TEXT("FlowActor: DialogueClient is null."));
		return;
	}

	DialogueClient->OnSessionStarted.AddDynamic(this, &AFireflyDialogueFlowActor::HandleSessionStarted);
	DialogueClient->OnTurnReceived.AddDynamic(this, &AFireflyDialogueFlowActor::HandleTurnReceived);
	DialogueClient->OnError.AddDynamic(this, &AFireflyDialogueFlowActor::HandleError);

	SetupHUD();

	if (bAutoStartOnBeginPlay)
		StartDialogue();
}

void AFireflyDialogueFlowActor::EndPlay(const EEndPlayReason::Type Reason)
{
	if (HUDWidget)
	{
		HUDWidget->RemoveFromParent();
		HUDWidget = nullptr;
	}
	Super::EndPlay(Reason);
}

void AFireflyDialogueFlowActor::SetupHUD()
{
	if (!HUDWidgetClass)
	{
		UE_LOG(LogFirefly, Warning, TEXT("FlowActor: HUDWidgetClass is not set — no HUD will be shown."));
		return;
	}

	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC)
	{
		UE_LOG(LogFirefly, Warning, TEXT("FlowActor: no PlayerController yet — HUD skipped."));
		return;
	}

	HUDWidget = CreateWidget<UFireflyDialogueHUDWidget>(PC, HUDWidgetClass);
	if (!HUDWidget)
	{
		UE_LOG(LogFirefly, Error, TEXT("FlowActor: failed to create HUD widget."));
		return;
	}

	HUDWidget->AddToViewport();
	HUDWidget->OnLineFinished.AddDynamic(this, &AFireflyDialogueFlowActor::HandleLineFinished);
	HUDWidget->OnOptionPicked.AddDynamic(this, &AFireflyDialogueFlowActor::HandleOptionPicked);

	// Мышка видна для клика по опциям.
	PC->bShowMouseCursor = true;
	FInputModeGameAndUI InputMode;
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	InputMode.SetHideCursorDuringCapture(false);
	PC->SetInputMode(InputMode);
}

void AFireflyDialogueFlowActor::StartDialogue()
{
	if (!DialogueClient) return;
	if (HUDWidget)
	{
		HUDWidget->ClearAll();
		HUDWidget->SetWaiting(true);
	}
	DialogueClient->StartSession();
}

void AFireflyDialogueFlowActor::HandleSessionStarted(const FDialogueTurn& Opener)
{
	if (HUDWidget) HUDWidget->SetWaiting(false);
	PendingLines   = Opener.Lines;
	PendingOptions = Opener.NextPlayerOptions;
	bLastContinue  = Opener.bContinue;
	PlayNextLineOrShowOptions();
}

void AFireflyDialogueFlowActor::HandleTurnReceived(const FDialogueTurn& Turn)
{
	if (HUDWidget) HUDWidget->SetWaiting(false);
	PendingLines   = Turn.Lines;
	PendingOptions = Turn.NextPlayerOptions;
	bLastContinue  = Turn.bContinue;

	if (DialogueClient)
	{
		DialogueClient->SetOrbitProgress(DialogueClient->GetOrbitProgress() + OrbitProgressPerTurn);
	}

	PlayNextLineOrShowOptions();
}

void AFireflyDialogueFlowActor::HandleError(const FString& Err)
{
	UE_LOG(LogFirefly, Error, TEXT("FlowActor: %s"), *Err);
	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 15.f, FColor::Red,
			FString::Printf(TEXT("Dialogue ERROR: %s"), *Err));
	}
	if (HUDWidget) HUDWidget->SetWaiting(false);
}

void AFireflyDialogueFlowActor::HandleLineFinished()
{
	PlayNextLineOrShowOptions();
}

void AFireflyDialogueFlowActor::HandleOptionPicked(int32 Index, const FString& OptionText)
{
	if (!DialogueClient) return;
	if (HUDWidget)
	{
		HUDWidget->HideOptions();
		HUDWidget->SetWaiting(true);
	}
	DialogueClient->SubmitChoice(OptionText);
}

void AFireflyDialogueFlowActor::PlayNextLineOrShowOptions()
{
	if (PendingLines.Num() > 0)
	{
		FDialogueLine Line = PendingLines[0];
		PendingLines.RemoveAt(0);
		if (HUDWidget)
			HUDWidget->PlayLine(Line.Speaker, Line.Line, Line.DurationMs);
		else
			HandleLineFinished(); // нет HUD — сразу дальше
		return;
	}

	// Все реплики проиграны. Либо показываем опции, либо завершаем.
	if (!bLastContinue)
	{
		UE_LOG(LogFirefly, Log, TEXT("FlowActor: dialogue ended (continue=false). TODO: trigger landing."));
		if (HUDWidget) HUDWidget->ClearAll();
		return;
	}

	if (HUDWidget && PendingOptions.Num() > 0)
		HUDWidget->ShowOptions(PendingOptions);
}
