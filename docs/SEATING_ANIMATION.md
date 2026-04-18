# Рассадка и анимация MetaHuman за столом

Это самая часто задаваемая задача в UE5, когда нужна сцена диалога. Решение — комбинация **Mixamo animations + IK Retargeter + Chair Actor с сокетами + State machine AnimBP**.

---

## Что понадобится

1. MetaHuman-персонаж, собранный и импортированный в проект (через Quixel Bridge).
2. Анимации сидения и разговора — качать с **Mixamo** (https://www.mixamo.com), бесплатно после регистрации Adobe.
3. Плагин **IK Retargeter** (встроен в UE5).

---

## Шаг 1. Модульная мебель

1. Создайте `BP_DiningTable` — Static Mesh стола.
2. Создайте `BP_ChairActor` — Static Mesh стула + **Scene Component "SeatSocket"**.
   - SeatSocket располагается на высоте сиденья, чуть впереди спинки, нулевым поворотом.
   - Это точка, где окажется pelvis MetaHuman'а в сидячей позе.
3. Расставьте 9 стульев вокруг стола согласно [CHARACTERS.md](CHARACTERS.md#итоговая-рассадка-за-столом).

## Шаг 2. Скачать анимации Mixamo

Нужны (все с **"In Place"** включённым):
- `Sitting Idle` — базовая поза.
- `Sitting Talking 1` / `2` / `3` — с разными жестами.
- `Sitting Yell` — для раздражения / Jayne.
- `Sitting Clap` / `Sitting Rub Hands` / `Sitting Dying` (случайные idle fillers).
- `Sitting Thumbs Up`, `Sitting Victory` — эмоциональные акценты.

**Совет:** в Mixamo выберите персонажа `Y-Bot` и скачайте с настройками:
- Format: FBX Binary (.fbx)
- Skin: Without Skin
- Frames per Second: 30 (или 60)
- Keyframe Reduction: none

## Шаг 3. Ретаргетинг на MetaHuman

Mixamo анимации — на своём скелете (`Mixamo_rig`). MetaHuman — на `metahuman_base_skel`. Прямой импорт на работает, нужен **IK Retargeter**.

1. Импортировать FBX с анимацией в `Content/Crew/Animation/Raw/Mixamo/`. UE спросит про skeleton — создайте новый `SK_MixamoYBot_Skeleton` один раз, дальше используйте его.
2. Создать **IK Rig** для Mixamo skeleton: `Animation → IK Rig → IK_MixamoYBot`.
   - Goals на кисти, стопы, голову, pelvis.
3. Аналогично **IK Rig для MetaHuman:** `IK_MetaHuman` (или использовать готовый из MetaHuman плагина).
4. **IK Retargeter** `RTG_MixamoToMetaHuman`:
   - Source: `IK_MixamoYBot`.
   - Target: `IK_MetaHuman`.
   - Chain mapping: автоматика обычно покрывает 90%, допилить руки.
5. В retargeter'e выделить все Mixamo анимации → `Export Selected Animations` → сохранить в `Content/Crew/Animation/Retargeted/`.

**Проверка:** откройте полученную `SitTalk_1_MH.uasset` в MetaHuman-скелете — анимация проигрывается без багов суставов.

## Шаг 4. AnimBlueprint для сидящего

`ABP_SeatedCrew` (или по-персонажно, если нужен character-specific override).

State machine верхнего уровня:

```
    [Entry]
       │
       ▼
   ┌───────┐   bIsTalking=true    ┌───────────┐
   │ Idle  │────────────────────►│  Talking  │
   │       │◄────────────────────│           │
   └──┬────┘   bIsTalking=false   └────┬──────┘
      │                                │
      │ bIsReacting=true               │
      ▼                                │
   ┌───────┐                           │
   │React  │                           │
   └───────┘                           │
```

**Idle state** → Blend Space из SitIdle_A / B / C (мелкая случайная вариация каждые 5–10 сек).

**Talking state** → случайный Montage из пула SitTalk_1/2/3; запускается через `Play Montage` в BP_SeatActor.SpeakLine; проигрывается поверх Idle через **Layered Blend Per Bone** (только upper-body, чтобы ноги не дёргались).

**Reacting state** → для моментов «удивился», «напрягся» — короткий Montage (0.5–1.5 сек).

**Aim Offset** на голове: `LookAt` в сторону говорящего — постоянно включено. Голова мягко поворачивается на того, кто сейчас говорит (переменная `CurrentSpeakerDir`).

## Шаг 5. BP_SeatActor — Actor, который «садит» MetaHuman

```
Components:
  SkeletalMesh  — assign MetaHuman body mesh
  (плюс все MetaHuman face meshes child-of body)

Properties:
  TargetChair (BP_ChairActor reference)
  SeatSocketName = "SeatSocket"

BeginPlay():
  1. attach self (root) to TargetChair.SeatSocket with "Keep World" → "Snap to Target"
  2. set ABP instance to ABP_SeatedCrew (or a character-specific subclass)
  3. play SitIdle montage once (enter pose)

SpeakLine(FString Text, FString Emotion, FString AudioUrl):
  1. ABP.bIsTalking = true
  2. pick montage from TalkMontagesByEmotion[Emotion]
  3. PlayMontage
  4. if AudioUrl not empty:
       a. async fetch / stream audio as SoundWave
       b. PlaySound2D or spatialized
     else:
       calculate duration from text length (words * 0.35s)
  5. OnMontageEnded (or audio ended, whichever later):
       ABP.bIsTalking = false
       broadcast OnLineFinished delegate
```

## Шаг 6. HTTP wrapper (C++)

Минимальный actor component для вызова dialogue server. Кладётся на `BP_CabinFlow`.

```cpp
// DialogueClientComponent.h (упрощённо)
USTRUCT(BlueprintType)
struct FDialogueLine
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FString Speaker;
    UPROPERTY(BlueprintReadOnly) FString Line;
    UPROPERTY(BlueprintReadOnly) FString Emotion;
    UPROPERTY(BlueprintReadOnly) FString AudioUrl;
    UPROPERTY(BlueprintReadOnly) int32   DurationMs = 0;
};

// DialogueClientComponent.cpp (ключевой фрагмент)
void UDialogueClientComponent::SubmitChoice(const FString& Text)
{
    History.Add({TEXT("player"), Text, TEXT("neutral"), TEXT(""), 0});

    TSharedRef<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField("session_id",  SessionId);
    Body->SetStringField("player_choice", Text);
    Body->SetNumberField("orbit_progress", OrbitProgress);

    TArray<TSharedPtr<FJsonValue>> HistArr;
    for (const FDialogueLine& Turn : History)
    {
        auto Obj = MakeShared<FJsonObject>();
        Obj->SetStringField("speaker", Turn.Speaker);
        Obj->SetStringField("line",    Turn.Line);
        HistArr.Add(MakeShared<FJsonValueObject>(Obj));
    }
    Body->SetArrayField("history", HistArr);

    FString BodyStr;
    auto Writer = TJsonWriterFactory<>::Create(&BodyStr);
    FJsonSerializer::Serialize(Body, Writer);

    SendPost(TEXT("/turn"), BodyStr, [this](TSharedPtr<FJsonObject> Resp)
    {
        TArray<FDialogueLine> Lines;
        for (const auto& V : Resp->GetArrayField("lines"))
        {
            auto O = V->AsObject();
            FDialogueLine L;
            L.Speaker    = O->GetStringField("speaker");
            L.Line       = O->GetStringField("line");
            L.Emotion    = O->GetStringField("emotion");
            L.AudioUrl   = O->GetStringField("audio_url");
            L.DurationMs = O->GetIntegerField("duration_ms");
            Lines.Add(L);
            History.Add(L);
        }
        TArray<FString> Options;
        for (const auto& V : Resp->GetArrayField("next_player_options"))
            Options.Add(V->AsString());

        bool bCont = Resp->GetBoolField("continue");
        FString Phase = Resp->GetStringField("phase");

        OnTurnReceived.Broadcast(Lines, Options, Phase, bCont);
    });
}
```

(Полный код будет в `Source/FireflyUE5/Dialogue/` при реальной реализации — в репо пока нет `.uproject`, только инструкции.)

---

## Распространённые проблемы и решения

| Проблема | Симптом | Решение |
|---|---|---|
| MetaHuman **проваливается в стул** | Ноги торчат из пола | SeatSocket в BP_ChairActor выше на 5-10 см; или в BP_SeatActor добавить Mesh offset. |
| **Кривые локти** после retargeting | Руки выгибаются | В IK Retargeter: настроить Twist и Chain Alpha для руки. Часто помогает включить "Stretch" на roots. |
| Анимация **не проигрывается поверх idle** | Talking работает, но ноги дёргаются | Layered Blend Per Bone по `spine_03` — upper-body only. |
| **Голова не смотрит на говорящего** | Все смотрят в никуда | Aim Offset + `LookAt Modify Bone` в AnimBP post-process, source — `CurrentSpeakerDir` из BP_CabinFlow. |
| MetaHuman **мерцает** в Sequencer | Швы между lod | Force LOD 0 через `Set Forced LOD` в BP. Для massive сцены: LOD 1 для дальних. |
| **Звук опережает анимацию** | Липсинк отстаёт | Play montage и sound в одном тике, запускать звук через `PlaySound2D` сразу после `PlayMontage`. Лучше — через `AnimNotify` в montage'е. |

---

## Чек-лист фазы 3

- [ ] 9 стульев + стол в `L_SerenityCabin`.
- [ ] У каждого стула есть socket `SeatSocket`.
- [ ] 5+ retargeted talk montages в `Content/Crew/Animation/Retargeted/`.
- [ ] ABP_SeatedCrew собран, state machine работает.
- [ ] BP_SeatActor.SpeakLine проигрывает случайный talk montage.
- [ ] Все 9 MetaHuman'ов занимают свои места при BeginPlay.
- [ ] Head LookAt двигается к говорящему.
- [ ] Без заметных артефактов на 1080p.
