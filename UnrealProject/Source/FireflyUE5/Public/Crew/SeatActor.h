// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SeatActor.generated.h"

class USkeletalMeshComponent;
class UAnimMontage;
class USoundBase;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSeatedLineFinished);

/**
 * BP_SeatActor: ставит MetaHuman-сетку в кресло и играет реплики.
 *
 * В шапке используется SkeletalMeshComponent + ABP_SeatedCrew (назначить в BP).
 * Кресло — внешний BP_ChairActor с сокетом SeatSocket; этот актёр при BeginPlay
 * аттачится к своему SeatSocket через TargetChair reference.
 */
UCLASS(Blueprintable, BlueprintType)
class FIREFLYUE5_API ASeatActor : public AActor
{
	GENERATED_BODY()

public:
	ASeatActor();

	/** Ключ персонажа (Mal, Zoe, ...), используется для выбора камеры и голоса. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Crew")
	FString CharacterKey;

	/** Актёр кресла. В нём должен быть компонент SeatSocket (SceneComponent). */
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Firefly|Crew")
	TObjectPtr<AActor> TargetChair = nullptr;

	/** Имя сокета/компонента в TargetChair, куда приклеиваемся. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Crew")
	FName SeatSocketName = TEXT("SeatSocket");

	/** Набор talk-монтажей по эмоции. Заполняется в BP. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Crew|Anim")
	TMap<FString, TObjectPtr<UAnimMontage>> TalkMontagesByEmotion;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Firefly|Crew|Anim")
	TObjectPtr<UAnimMontage> FallbackTalkMontage = nullptr;

	/** Называется из BP_CabinFlow при получении реплики. */
	UFUNCTION(BlueprintCallable, Category = "Firefly|Crew")
	void SpeakLine(const FString& Text, const FString& Emotion,
	               USoundBase* LineAudio, float EstimatedSeconds);

	UPROPERTY(BlueprintAssignable)
	FOnSeatedLineFinished OnLineFinished;

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> BodyMesh;

private:
	FTimerHandle LineFinishedHandle;

	void BroadcastFinished();
};
