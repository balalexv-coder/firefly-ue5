// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/FireflyDialogueTestActor.h"
#include "FireflyUE5.h"
#include "Dialogue/DialogueClientComponent.h"
#include "Engine/Engine.h"

AFireflyDialogueTestActor::AFireflyDialogueTestActor()
{
	PrimaryActorTick.bCanEverTick = false;

	DialogueClient = CreateDefaultSubobject<UDialogueClientComponent>(TEXT("DialogueClient"));
}

void AFireflyDialogueTestActor::BeginPlay()
{
	Super::BeginPlay();

	if (!DialogueClient)
	{
		Print(TEXT("DialogueClient is null."), FColor::Red);
		return;
	}

	DialogueClient->OnSessionStarted.AddDynamic(this, &AFireflyDialogueTestActor::HandleSessionStarted);
	DialogueClient->OnTurnReceived.AddDynamic(this, &AFireflyDialogueTestActor::HandleTurnReceived);
	DialogueClient->OnError.AddDynamic(this, &AFireflyDialogueTestActor::HandleError);

	if (bAutoStartOnBeginPlay)
	{
		RemainingAutoTurns = AutoTurnsAfterStart;
		Print(FString::Printf(TEXT("Firefly test: contacting %s ..."),
		                      *DialogueClient->ServerBaseUrl), FColor::Yellow);
		DialogueClient->StartSession();
	}
}

void AFireflyDialogueTestActor::HandleSessionStarted(const FDialogueTurn& Opener)
{
	PrintTurn(Opener, TEXT("OPENER"));

	if (RemainingAutoTurns > 0 && Opener.NextPlayerOptions.Num() > 0)
	{
		const FString& Choice = Opener.NextPlayerOptions[0];
		Print(FString::Printf(TEXT("[player -> #1] %s"), *Choice), FColor::Cyan);
		DialogueClient->SubmitChoice(Choice);
	}
	else
	{
		Print(TEXT("=== PIPELINE OK (opener only) ==="), FColor::Magenta);
	}
}

void AFireflyDialogueTestActor::HandleTurnReceived(const FDialogueTurn& Turn)
{
	PrintTurn(Turn, TEXT("TURN"));

	RemainingAutoTurns--;
	if (RemainingAutoTurns > 0 && Turn.NextPlayerOptions.Num() > 0 && Turn.bContinue)
	{
		const FString& Choice = Turn.NextPlayerOptions[0];
		Print(FString::Printf(TEXT("[player -> #1] %s"), *Choice), FColor::Cyan);
		DialogueClient->SubmitChoice(Choice);
	}
	else
	{
		Print(TEXT("=== PIPELINE OK ==="), FColor::Magenta);
	}
}

void AFireflyDialogueTestActor::HandleError(const FString& Err)
{
	Print(FString::Printf(TEXT("ERROR: %s"), *Err), FColor::Red);
}

void AFireflyDialogueTestActor::PrintTurn(const FDialogueTurn& Turn, const FString& Label)
{
	Print(FString::Printf(TEXT("--- %s (phase=%s, continue=%s) ---"),
	                      *Label, *Turn.Phase,
	                      Turn.bContinue ? TEXT("true") : TEXT("false")),
	      FColor::Yellow);

	for (const FDialogueLine& L : Turn.Lines)
	{
		Print(FString::Printf(TEXT("  [%s|%s] %s"), *L.Speaker, *L.Emotion, *L.Line),
		      FColor::Green);
	}
	for (int32 i = 0; i < Turn.NextPlayerOptions.Num(); ++i)
	{
		Print(FString::Printf(TEXT("    #%d: %s"), i + 1, *Turn.NextPlayerOptions[i]),
		      FColor(140, 200, 255));
	}
}

void AFireflyDialogueTestActor::Print(const FString& Msg, const FColor& Color) const
{
	UE_LOG(LogFirefly, Log, TEXT("%s"), *Msg);
	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 25.f, Color, Msg);
	}
}
