# tools/

Внешние скрипты и сервисы. Всё, что не ассеты UE.

## dialogue_server/

FastAPI-сервис, генерирующий реплики экипажа. См. [`dialogue_server/README.md`](dialogue_server/README.md).

## (planned) tts_server/

Отдельный сервис-обёртка для TTS (ElevenLabs / Kokoro / OpenAI), с кешированием. Пока логика «dialogue server сам знает про TTS» — добавим когда упрёмся в целесообразность расщепить.

## (planned) retargeter.py

Python-скрипт для батч-ретаргета Mixamo анимаций на MetaHuman скелет. Использует `unreal.EditorAssetLibrary` и `IKRetargeter`. Запускается из UE: Window → Python Editor.
