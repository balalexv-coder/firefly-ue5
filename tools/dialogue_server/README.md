# Dialogue Server

FastAPI-сервис, превращающий состояние разговора в реплики экипажа через Claude с tool-use / structured output. Используется Blueprint'ом `BP_CabinFlow` в UE5 как единственный источник реплик.

---

## Установка

```bash
cd tools/dialogue_server
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# отредактируйте .env: вставьте ANTHROPIC_API_KEY
```

## Запуск

```bash
uvicorn server:app --reload --port 8765
```

Сервер поднимется на `http://127.0.0.1:8765`. Плюс:
- Swagger UI: `http://127.0.0.1:8765/docs`
- OpenAPI JSON: `http://127.0.0.1:8765/openapi.json`

## Тест

В отдельном терминале (с активированным venv):

```bash
python test_client.py
```

Выведется первая реплика Мала и три варианта ответа. 1/2/3 — выбор, `q` — выход.

## Эндпойнты

| Метод | Путь | Назначение |
|---|---|---|
| GET  | `/health`  | проверка живости |
| POST | `/start`   | новая сессия, opener + options |
| POST | `/turn`    | основной — следующий раунд |
| GET  | `/docs`    | Swagger UI |

Контракты и пример JSON — в [../../docs/DIALOGUE_SYSTEM.md](../../docs/DIALOGUE_SYSTEM.md).

## Модель и стоимость

Настраивается в `.env`:

- `DIALOGUE_MODEL=claude-opus-4-7` — лучший ролевой отыгрыш, ~10× дороже sonnet.
- `DIALOGUE_MODEL=claude-sonnet-4-6` — дешевле, быстрее, чуть менее «живой» стиль.

**Prompt caching** включён для system prompt (~2500 токенов). Кеш живёт 5 минут, сессия длится ~5–10 минут → кеш почти всегда горячий → cache-hit rate > 80%. Реальная стоимость раунда — в несколько раз ниже неоптимизированной.

## Логи

Все запросы и ответы пишутся в `./logs/<session_id>.jsonl` — удобно смотреть, как ИИ вёл разговор и не фуерагил ли.

Сброс: `rm logs/*.jsonl`.

## TTS (future)

Текущая версия **не озвучивает реплики** — возвращает `audio_url: null`. Реплики UE либо читает тишиной с сабами, либо UE сам дёргает внешний TTS.

Для интеграции TTS в сервер:
1. В `server.py` добавить `/tts` роут.
2. В `_normalize_output` — если `tts_enabled`, синтезировать каждую `line`, класть mp3 в `tts_cache/`, подставлять URL.
3. Варианты провайдеров и voice mapping: [../../docs/LIP_SYNC.md](../../docs/LIP_SYNC.md).

## Частые проблемы

### `ANTHROPIC_API_KEY is not set`

Не создан `.env` рядом с `server.py`, либо в нём пустая переменная.

### `LLM did not call emit_turn tool`

Редко: модель ответила текстом вместо tool_call. Обычно следствие edge-case входа (очень странная история). Перезапустите раунд. Если повторяется — в `prompts.py → system_prompt` усилить требование к tool-use.

### Сервер возвращает 502 / LLM error

- Проверьте ключ и баланс на [console.anthropic.com](https://console.anthropic.com).
- Возможно rate limit — повторите через 5 сек.

### UE не может достучаться до `localhost:8765`

- Если UE в редакторе — работает `127.0.0.1`.
- Если UE в билде, запущенном от другого пользователя — Firewall может блочить. Разрешить `uvicorn` в Windows Defender.
