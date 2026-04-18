# Dialogue Server

FastAPI-сервис, генерирующий реплики экипажа структурированным JSON через LLM. Используется `BP_CabinFlow` в UE5 как единственный источник реплик.

Поддерживает два backend'а (выбирается переменной `DIALOGUE_BACKEND`):

| Backend | Когда | Стоимость | Качество |
|---|---|---|---|
| **ollama** (дефолт) | разработка, отладка, частые итерации | бесплатно, локально | хорошее (на qwen3.5:9b), без интернета |
| **anthropic** | финальное демо, запись ролика | платно (~$0.01–0.05 / раунд) | pro, самый живой ролеплей |

Для v0.1 разработки используем **Ollama**, потом переключаем `DIALOGUE_BACKEND=anthropic` одной строкой в `.env`.

---

## Установка

```bash
cd tools/dialogue_server
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
```

## Предусловия — Ollama

Должен быть установлен и запущен Ollama (https://ollama.com). Проверить:
```bash
curl http://localhost:11434/api/tags
```

Рекомендованная модель для dev — `qwen3.5:9b`:
```bash
ollama pull qwen3.5:9b
```

Другие поддерживаемые варианты в [`.env.example`](.env.example).

## Запуск

```bash
uvicorn server:app --reload --port 8765
# или из PowerShell:
.venv\Scripts\python -m uvicorn server:app --reload --port 8765
```

Сервер поднимется на `http://127.0.0.1:8765`. Swagger UI: `/docs`.

## Тест

```bash
python test_client.py
```

Выведется opener Мала + 3 варианта ответа. 1/2/3 — выбор, `q` — выход.

## Переключение на Claude

В `.env`:
```
DIALOGUE_BACKEND=anthropic
ANTHROPIC_API_KEY=sk-ant-...
DIALOGUE_MODEL=claude-opus-4-7
```

Рестартанули сервер — сразу работает без изменений кода/UE.

## Эндпойнты

| Метод | Путь | Назначение |
|---|---|---|
| GET  | `/health`  | проверка живости (`{"status":"ok","backend":"ollama"}`) |
| POST | `/start`   | новая сессия, opener + options |
| POST | `/turn`    | основной — следующий раунд |
| GET  | `/docs`    | Swagger UI |

Контракт JSON — в [`../../docs/DIALOGUE_SYSTEM.md`](../../docs/DIALOGUE_SYSTEM.md).

## Как это работает

1. `system_prompt()` и `turn_schema()` готовятся в [`prompts.py`](prompts.py).
2. Backend (Ollama или Anthropic) принимает `(system, user, schema)` и возвращает dict, **гарантированно** соответствующий схеме:
   - **Ollama** — через `format: <JSON Schema>` параметр в `/api/chat` (feature появился в Ollama 0.5+). Qwen3.5 с `think: false`.
   - **Anthropic** — через tool_use с `tool_choice={"type":"tool","name":"emit_turn"}`.
3. Сервер нормализует (добавляет `audio_url: null` и estimated `duration_ms`), логирует в `logs/<session>.jsonl`, отдаёт клиенту.

## Логи

`./logs/<session_id>.jsonl` — каждый раунд с request, raw-ответом LLM и нормализованным выходом. Смотреть как ИИ ведёт разговор, ловить артефакты.

```bash
# Показать последний ответ
tail -1 logs/*.jsonl | python -m json.tool
```

## TTS (планируется)

Текущая версия возвращает `audio_url: null` — без озвучки. Пайплайн TTS описан в [`../../docs/LIP_SYNC.md`](../../docs/LIP_SYNC.md).

## Частые проблемы

### `requests.exceptions.ConnectionError: localhost:11434`
Ollama не запущен. Запустить: `ollama serve`, или через Ollama app-tray.

### `Ollama returned invalid JSON despite format schema`
Версия Ollama < 0.5 — нет поддержки `format: <schema>`. Обновить: `winget upgrade Ollama.Ollama` или `curl -fsSL https://ollama.com/install.sh | sh`.

### Qwen долго генерирует (5+ сек на раунд)
Первый запрос после старта — модель грузится в VRAM (5–20 сек). Последующие — в разы быстрее, кеш горячий. Если всё равно медленно — модель не влезает в VRAM, свалилась на CPU. Проверить: `ollama ps`.

### Ответы короткие / персонажи ошибаются
Проверить что `DIALOGUE_TEMPERATURE=0.85` в `.env` (ниже — стерильно, выше — бред). Если на qwen3.5:9b стиль всё равно бедный — попробовать `qwen3.5:9b-q8_0` или переключиться на Anthropic.

### `LLM did not call emit_turn tool` (только Anthropic)
Редкое — модель вернула текст вместо tool_call. Повторить запрос. Если повторяется — усилить требование в system_prompt.
