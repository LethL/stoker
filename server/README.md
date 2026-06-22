# stoker-server

FastAPI-приложение: REST API, WebSocket-хаб для агентов, state в SQLite
(SQLModel). Числовые метрики во времени тут **не** хранятся (это Prometheus).

**Статус: M1** — базовый health-check (`/healthz`). API/WS/БД — следующие вехи.

## Запуск (dev)

```bash
uv sync
uv run uvicorn stoker_server.main:app --reload   # M1.2
curl localhost:8000/healthz
```

## Проверки

```bash
uv run ruff check          # линт
uv run ruff format         # формат
uv run mypy                # типы (strict)
uv run pytest              # тесты
```

## Структура (по мере роста)

- `src/stoker_server/api/` — REST endpoints
- `src/stoker_server/ws/` — WebSocket-хаб для агентов
- `src/stoker_server/models/` — SQLModel
- `src/stoker_server/db.py`, `config.py`
