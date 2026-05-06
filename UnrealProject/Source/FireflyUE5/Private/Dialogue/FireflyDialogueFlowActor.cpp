// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/FireflyDialogueFlowActor.h"
#include "FireflyUE5.h"
#include "Dialogue/DialogueClientComponent.h"
#include "Dialogue/DialogueManager.h"
#include "UI/FireflyDialogueHUDWidget.h"
#include "Blueprint/UserWidget.h"
#include "Engine/Engine.h"

AFireflyDialogueFlowActor::AFireflyDialogueFlowActor()
{
	PrimaryActorTick.bCanEverTick = false;
	DialogueClient = CreateDefaultSubobject<UDialogueClientComponent>(TEXT("DialogueClient"));

	// Default scripted demo pool — 8 реплик Mal/Zoe/Wash/Inara, тексты
	// идентичны generate_demo_lines.py (откуда сгенерены WAV → LS).
	auto MakeLine = [](const TCHAR* Speaker, const TCHAR* LineID, const TCHAR* Text)
	{
		FDialogueLine L;
		L.Speaker = Speaker;
		L.LineID = LineID;
		L.Line = Text;
		L.Emotion = TEXT("calm");
		return L;
	};
	ScriptedDemoLines.Add(MakeLine(TEXT("Mal"),   TEXT("intro_atmo"),
		TEXT("Two hours to atmo, folks. Grab your cups before we get dusty.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Zoe"),   TEXT("status"),
		TEXT("Two klicks out, sir. No patrol activity on the scanner.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Wash"),  TEXT("vote"),
		TEXT("I vote for 'don't explode' again. Always polls well.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Inara"), TEXT("sinclair"),
		TEXT("Malcolm. About tomorrow. You didn't mention the Sinclair family.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Mal"),   TEXT("orders"),
		TEXT("Wash, hold us steady on approach. Zoe, run the cargo manifest one more time.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Zoe"),   TEXT("cargo"),
		TEXT("Cargo's all secure below. Wouldn't want to start the day apologizing again.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Wash"),  TEXT("dramatic"),
		TEXT("If anyone needs me, I'll be dramatically not crashing the ship.")));
	ScriptedDemoLines.Add(MakeLine(TEXT("Inara"), TEXT("surprise"),
		TEXT("Try to act surprised when this goes sideways. It's a small kindness.")));
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

	if (DialogueManager)
	{
		DialogueManager->OnLineFinished.AddDynamic(
			this, &AFireflyDialogueFlowActor::HandleDialogueManagerLineFinished);
	}

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
	// Scripted demo: skip LLM/HTTP, проигрываем pre-gen pool по очереди.
	if (bUseScriptedDemo)
	{
		UE_LOG(LogFirefly, Log, TEXT("FlowActor: scripted demo mode — %d lines"),
			ScriptedDemoLines.Num());
		PendingLines = ScriptedDemoLines;
		PendingOptions.Empty();
		bLastContinue = false;
		if (HUDWidget)
		{
			HUDWidget->ClearAll();
			HUDWidget->SetWaiting(false);
		}
		PlayNextLineOrShowOptions();
		return;
	}

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
	// HUD-таймер стреляет даже когда мы играем LS (он не знает про DialogueManager).
	// В LS-режиме настоящий финиш приходит через HandleDialogueManagerLineFinished —
	// игнорируем HUD-сигнал.
	if (bWaitingForLSFinish)
	{
		return;
	}
	PlayNextLineOrShowOptions();
}

void AFireflyDialogueFlowActor::HandleDialogueManagerLineFinished(const FString& Speaker, const FString& LineID)
{
	UE_LOG(LogFirefly, Log, TEXT("FlowActor: DialogueManager finished line speaker='%s' id='%s'"),
		*Speaker, *LineID);
	bWaitingForLSFinish = false;
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

		// Если есть DialogueManager + LineID → проигрываем через LS
		// (lipsync + body gesture). HUD используется параллельно для
		// субтитров (без timer-based finish — финиш приходит от LS).
		const bool bUseLSPlayback =
			DialogueManager != nullptr &&
			!Line.LineID.IsEmpty() &&
			Line.Speaker != TEXT("player");

		UE_LOG(LogFirefly, Log, TEXT("FlowActor: line speaker='%s' line_id='%s' DM=%s → bUseLS=%d"),
			*Line.Speaker, *Line.LineID,
			(DialogueManager ? *DialogueManager->GetName() : TEXT("NULL")),
			bUseLSPlayback ? 1 : 0);

		if (bUseLSPlayback)
		{
			if (HUDWidget)
			{
				HUDWidget->PlayLine(Line.Speaker, Line.Line, /*DurationMs=*/0);
			}
			bWaitingForLSFinish = true;
			DialogueManager->PlayLine(Line.Speaker, Line.LineID);
			// Завершение придёт через HandleDialogueManagerLineFinished.
			// HUD-finish от 0.2с-таймера будет проигнорирован (см. HandleLineFinished).
			return;
		}

		// Fallback: HUD-only текстовый режим (для player'а или
		// если LineID не указан / DialogueManager не задан).
		bWaitingForLSFinish = false;
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
