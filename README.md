# Stoker

Self-hosted мониторинг и базовое управление майнинг-ригами. Pet-проект.
Приложение поверх Ubuntu/Debian (не OS-дистрибутив).

Подробности архитектуры, конвенций и roadmap — в [`CLAUDE.md`](CLAUDE.md);
решения — в [`docs/decisions/`](docs/decisions/); research — в
[`docs/research/`](docs/research/).

## Монорепа

Один git-репозиторий, три независимых пакета (без общего билда):

| Пакет | Что | Стек |
|-------|-----|------|
| [`agent/`](agent/) | демон на риге: метрики + команды | Python 3.12, uv, FastAPI/prometheus-client |
| [`server/`](server/) | API, WS-хаб, state | Python 3.12, uv, FastAPI, SQLModel/SQLite |
| [`web/`](web/) | управляющий UI | Vue 3.5, Vite, TypeScript, Tailwind |
| `infra/` | Prometheus + Grafana | docker-compose (с M2b) |

## Статус: M1 (скелет)

Каркас монорепы, CI (GitHub Actions), health-check сервера, агент-заглушка с
`/metrics`. Реальные GPU-метрики (M2a), Prometheus/Grafana (M2b–c), WebSocket
(M2d), UI (M3), управление майнером (M4) — следующие вехи.

## Локальный запуск

```bash
# агент
cd agent && uv run python -m stoker_agent --config dev.toml

# сервер
cd server && uv run uvicorn stoker_server.main:app --reload

# фронт
cd web && pnpm dev
```

## Проверки (как в CI)

```bash
cd agent  && uv run ruff check && uv run mypy && uv run pytest
cd server && uv run ruff check && uv run mypy && uv run pytest
cd web    && pnpm lint && pnpm typecheck && pnpm test
```
