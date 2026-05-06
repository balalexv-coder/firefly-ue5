// Copyright (c) 2026 balalexv. MIT License.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "FireflyDialogueTypes.generated.h"

/** Одна реплика (от экипажа или игрока). */
USTRUCT(BlueprintType)
struct FIREFLYUE5_API FDialogueLine
{
	GENERATED_BODY()

	/** Ключ персонажа (Mal/Zoe/.../Book) или литерал "player". */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) FString Speaker;

	/** Текст реплики. */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) FString Line;

	/**
	 * Стабильный ID реплики, по которому ADialogueManager строит путь
	 * к LS ассету: `/Game/Audio/Dialogue/Generated/<Speaker>/<LineID>/LS_<Speaker>_<LineID>`.
	 * Пусто — будем показывать только субтитры через HUD без LS playback.
	 * Сервер должен заполнять это поле (для демо-реплик уже сгенерённых
	 * Python pipeline'ом — соответственно intro_atmo / orders / status / etc).
	 */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) FString LineID;

	/**
	 * Кому обращена реплика (массив имён speaker'ов как в ключах Speakers map:
	 * "Mal"/"Zoe"/"Wash"/"Inara"). Может быть пустым (общая реплика — никому
	 * конкретно), или содержать одного, или нескольких адресатов.
	 *
	 * Используется DialogueManager: говорящий поворачивает голову к первому
	 * адресату из массива. Слушатели (не addressees) смотрят на говорящего.
	 */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) TArray<FString> Addressees;

	/** Эмоциональный тон: calm, gruff, bright, dry, cryptic, warm, flirty, amused, serious, deadpan. */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) FString Emotion;

	/** Опционально: URL (или path) к озвучке. Пусто — играем с сабами без звука. */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) FString AudioUrl;

	/** Оценочная длительность для планирования камер/монтажей, мс. */
	UPROPERTY(BlueprintReadWrite, EditAnywhere) int32 DurationMs = 0;
};

/** Полный ответ сервера на /turn (или /start). */
USTRUCT(BlueprintType)
struct FIREFLYUE5_API FDialogueTurn
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite) TArray<FDialogueLine> Lines;

	UPROPERTY(BlueprintReadWrite) TArray<FString> NextPlayerOptions;

	/** "cruise" / "approach" / "atmo_entry". */
	UPROPERTY(BlueprintReadWrite) FString Phase;

	/** true — ждать выбор игрока; false — пора запускать синематик посадки. */
	UPROPERTY(BlueprintReadWrite) bool bContinue = true;
};

UENUM(BlueprintType)
enum class EDialoguePhase : uint8
{
	Cruise      UMETA(DisplayName = "Cruise"),
	Approach    UMETA(DisplayName = "Approach"),
	AtmoEntry   UMETA(DisplayName = "Atmo Entry"),
};
