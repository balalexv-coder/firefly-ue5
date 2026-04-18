// Copyright (c) 2026 balalexv. MIT License.

#include "SeatActor.h"
#include "FireflyUE5.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Animation/AnimMontage.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

ASeatActor::ASeatActor()
{
	PrimaryActorTick.bCanEverTick = false;

	BodyMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("BodyMesh"));
	RootComponent = BodyMesh;
}

void ASeatActor::BeginPlay()
{
	Super::BeginPlay();

	if (TargetChair)
	{
		// Сокет обычно оформлен как SceneComponent с уникальным именем на кресле.
		const FAttachmentTransformRules Rules(EAttachmentRule::SnapToTarget,
		                                       EAttachmentRule::SnapToTarget,
		                                       EAttachmentRule::KeepWorld,
		                                       /*bWeldSimulatedBodies*/ false);
		AttachToActor(TargetChair, Rules, SeatSocketName);
		UE_LOG(LogFirefly, Log, TEXT("%s seated on %s (%s)"),
		       *CharacterKey, *TargetChair->GetName(), *SeatSocketName.ToString());
	}
	else
	{
		UE_LOG(LogFirefly, Warning, TEXT("%s has no TargetChair assigned."), *CharacterKey);
	}
}

void ASeatActor::SpeakLine(const FString& Text, const FString& Emotion,
                           USoundBase* LineAudio, float EstimatedSeconds)
{
	// 1. Подобрать монтаж.
	UAnimMontage* Montage = nullptr;
	if (TObjectPtr<UAnimMontage>* Found = TalkMontagesByEmotion.Find(Emotion))
		Montage = *Found;
	if (!Montage)
		Montage = FallbackTalkMontage;

	// 2. Проиграть монтаж (upper-body по layer-blend настраивается в ABP).
	if (Montage && BodyMesh && BodyMesh->GetAnimInstance())
	{
		BodyMesh->GetAnimInstance()->Montage_Play(Montage, 1.f);
	}

	// 3. Проиграть звук (если есть).
	float AudioDuration = 0.f;
	if (LineAudio)
	{
		UGameplayStatics::PlaySound2D(this, LineAudio);
		AudioDuration = LineAudio->GetDuration();
	}

	// 4. Рассчитать общую длительность и запланировать событие.
	const float WaitTime = FMath::Max(EstimatedSeconds, AudioDuration);
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().SetTimer(LineFinishedHandle, this,
			&ASeatActor::BroadcastFinished, FMath::Max(WaitTime, 0.5f), false);
	}
}

void ASeatActor::BroadcastFinished()
{
	OnLineFinished.Broadcast();
}
