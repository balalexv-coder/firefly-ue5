# tools/

Внешние скрипты и сервисы. Всё, что не ассеты UE.

## dialogue_server/

FastAPI-сервис, генерирующий реплики экипажа. См. [`dialogue_server/README.md`](dialogue_server/README.md).

## (planned) tts_server/

Отдельный сервис-обёртка для TTS (ElevenLabs / Kokoro / OpenAI), с кешированием. Пока логика «dialogue server сам знает про TTS» — добавим когда упрёмся в целесообразность расщепить.

## ue_retarget_mixamo.py

Python-скрипт для **батч-ретаргета** Mixamo анимаций на MetaHuman скелет. Использует `unreal.EditorAssetLibrary` + `IKRetargetBatchOperation`.

**Как запускать:** в UE → Window → Python Editor → Execute File → `tools/ue_retarget_mixamo.py`.

Предусловия (настраиваются в редакторе один раз):
- Mixamo FBX лежат под `/Game/Crew/Animation/Raw/Mixamo/` с общим скелетом.
- Созданы `IK_MixamoYBot`, `IK_MetaHuman`, `RTG_MixamoToMetaHuman`.

См. [../docs/SEATING_ANIMATION.md](../docs/SEATING_ANIMATION.md#шаг-4-ретаргетинг-на-metahuman) и [../docs/WALKTHROUGH.md](../docs/WALKTHROUGH.md#34-ретаргетинг-на-metahuman).
