// Copyright (c) 2026 balalexv. MIT License.

#include "Dialogue/DialogueClientComponent.h"
#include "FireflyUE5.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

UDialogueClientComponent::UDialogueClientComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UDialogueClientComponent::BeginPlay()
{
	Super::BeginPlay();
	UE_LOG(LogFirefly, Log, TEXT("DialogueClientComponent initialized. Server=%s"), *ServerBaseUrl);
}

// ---------- Public API ----------

void UDialogueClientComponent::StartSession()
{
	TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
	Post(TEXT("/start"), Body, [this](TSharedPtr<FJsonObject> Resp) { HandleStartResponse(Resp); });
}

void UDialogueClientComponent::SubmitChoice(const FString& ChoiceText)
{
	if (SessionId.IsEmpty())
	{
		OnError.Broadcast(TEXT("SubmitChoice called before StartSession."));
		return;
	}

	FDialogueLine PlayerLine;
	PlayerLine.Speaker = TEXT("player");
	PlayerLine.Line    = ChoiceText;
	History.Add(PlayerLine);

	TSharedRef<FJsonObject> Body = BuildTurnBody(ChoiceText);
	Post(TEXT("/turn"), Body, [this](TSharedPtr<FJsonObject> Resp) { HandleTurnResponse(Resp); });
}

void UDialogueClientComponent::RequestNextTurn()
{
	if (SessionId.IsEmpty())
	{
		OnError.Broadcast(TEXT("RequestNextTurn called before StartSession."));
		return;
	}

	TSharedRef<FJsonObject> Body = BuildTurnBody(FString());
	Post(TEXT("/turn"), Body, [this](TSharedPtr<FJsonObject> Resp) { HandleTurnResponse(Resp); });
}

void UDialogueClientComponent::ResetSession()
{
	SessionId.Reset();
	History.Reset();
	OrbitProgress = 0.f;
}

void UDialogueClientComponent::SetOrbitProgress(float NewProgress)
{
	OrbitProgress = FMath::Clamp(NewProgress, 0.f, 1.f);
}

// ---------- HTTP ----------

void UDialogueClientComponent::Post(const FString& Endpoint, const TSharedRef<FJsonObject>& Body,
                                    TFunction<void(TSharedPtr<FJsonObject>)> OnSuccess)
{
	FString BodyStr;
	auto Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&BodyStr);
	FJsonSerializer::Serialize(Body, Writer);

	const FString Url = ServerBaseUrl + Endpoint;

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Req = FHttpModule::Get().CreateRequest();
	Req->SetVerb(TEXT("POST"));
	Req->SetURL(Url);
	Req->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Req->SetTimeout(HttpTimeoutSeconds);
	Req->SetContentAsString(BodyStr);

	TWeakObjectPtr<UDialogueClientComponent> WeakThis(this);
	Req->OnProcessRequestComplete().BindLambda(
		[WeakThis, Endpoint, OnSuccess](FHttpRequestPtr, FHttpResponsePtr Resp, bool bOk)
	{
		if (!WeakThis.IsValid()) return;

		if (!bOk || !Resp.IsValid())
		{
			WeakThis->OnError.Broadcast(FString::Printf(
				TEXT("Dialogue server unreachable at endpoint %s"), *Endpoint));
			return;
		}

		const int32 Code = Resp->GetResponseCode();
		const FString BodyStr = Resp->GetContentAsString();

		if (Code < 200 || Code >= 300)
		{
			WeakThis->OnError.Broadcast(FString::Printf(
				TEXT("Dialogue server %s returned %d: %s"), *Endpoint, Code, *BodyStr));
			return;
		}

		TSharedPtr<FJsonObject> Json;
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(BodyStr);
		if (!FJsonSerializer::Deserialize(Reader, Json) || !Json.IsValid())
		{
			WeakThis->OnError.Broadcast(FString::Printf(
				TEXT("Dialogue server %s returned non-JSON: %s"), *Endpoint, *BodyStr));
			return;
		}

		OnSuccess(Json);
	});
	Req->ProcessRequest();
}

TSharedRef<FJsonObject> UDialogueClientComponent::BuildTurnBody(const FString& PlayerChoice) const
{
	TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
	Body->SetStringField(TEXT("session_id"), SessionId);
	Body->SetStringField(TEXT("player_choice"), PlayerChoice);
	Body->SetNumberField(TEXT("orbit_progress"), OrbitProgress);

	TArray<TSharedPtr<FJsonValue>> HistArr;
	for (const FDialogueLine& Turn : History)
	{
		TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetStringField(TEXT("speaker"), Turn.Speaker);
		Obj->SetStringField(TEXT("line"),    Turn.Line);
		HistArr.Add(MakeShared<FJsonValueObject>(Obj));
	}
	Body->SetArrayField(TEXT("history"), HistArr);
	return Body;
}

// ---------- Parsing ----------

bool UDialogueClientComponent::ParseLine(const TSharedPtr<FJsonObject>& Obj, FDialogueLine& Out)
{
	if (!Obj.IsValid()) return false;
	Obj->TryGetStringField(TEXT("speaker"),  Out.Speaker);
	Obj->TryGetStringField(TEXT("line"),     Out.Line);
	Obj->TryGetStringField(TEXT("emotion"),  Out.Emotion);
	Obj->TryGetStringField(TEXT("audio_url"), Out.AudioUrl);
	int32 Dur = 0;
	Obj->TryGetNumberField(TEXT("duration_ms"), Dur);
	Out.DurationMs = Dur;
	return !Out.Line.IsEmpty();
}

bool UDialogueClientComponent::ParseTurn(const TSharedPtr<FJsonObject>& Obj, FDialogueTurn& Out)
{
	if (!Obj.IsValid()) return false;

	const TArray<TSharedPtr<FJsonValue>>* LinesArr = nullptr;
	if (Obj->TryGetArrayField(TEXT("lines"), LinesArr) && LinesArr)
	{
		for (const TSharedPtr<FJsonValue>& V : *LinesArr)
		{
			FDialogueLine L;
			if (ParseLine(V->AsObject(), L))
				Out.Lines.Add(L);
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* OptsArr = nullptr;
	if (Obj->TryGetArrayField(TEXT("next_player_options"), OptsArr) && OptsArr)
	{
		for (const TSharedPtr<FJsonValue>& V : *OptsArr)
			Out.NextPlayerOptions.Add(V->AsString());
	}

	Obj->TryGetStringField(TEXT("phase"), Out.Phase);
	Obj->TryGetBoolField(TEXT("continue"), Out.bContinue);
	return true;
}

// ---------- Handlers ----------

void UDialogueClientComponent::HandleStartResponse(TSharedPtr<FJsonObject> Json)
{
	Json->TryGetStringField(TEXT("session_id"), SessionId);

	FDialogueTurn Turn;
	if (const TSharedPtr<FJsonObject>* OpenerObj = nullptr;
	    Json->TryGetObjectField(TEXT("opener"), OpenerObj) && OpenerObj)
	{
		FDialogueLine Opener;
		if (ParseLine(*OpenerObj, Opener))
		{
			Turn.Lines.Add(Opener);
			History.Add(Opener);
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* OptsArr = nullptr;
	if (Json->TryGetArrayField(TEXT("next_player_options"), OptsArr) && OptsArr)
	{
		for (const TSharedPtr<FJsonValue>& V : *OptsArr)
			Turn.NextPlayerOptions.Add(V->AsString());
	}

	Json->TryGetStringField(TEXT("phase"), Turn.Phase);
	Turn.bContinue = true;

	UE_LOG(LogFirefly, Log, TEXT("Dialogue session started: %s"), *SessionId);
	OnSessionStarted.Broadcast(Turn);
}

void UDialogueClientComponent::HandleTurnResponse(TSharedPtr<FJsonObject> Json)
{
	FDialogueTurn Turn;
	if (!ParseTurn(Json, Turn))
	{
		OnError.Broadcast(TEXT("Failed to parse /turn response."));
		return;
	}

	for (const FDialogueLine& L : Turn.Lines)
		History.Add(L);

	OnTurnReceived.Broadcast(Turn);
}
