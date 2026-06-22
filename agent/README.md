# stoker-agent

Демон, ставится на риг. Собирает GPU-метрики (`GpuCollector` — Nvidia/pynvml
сейчас, AMD позже), телеметрию майнера (`MinerDriver` — WildRig сначала),
выставляет `/metrics` для Prometheus и (позже) держит WS-канал к серверу.

**Статус: M1** — заглушка, выставляющая `/metrics` с фейковыми значениями
(реальные метрики — M2a).

## Запуск (dev)

```bash
uv sync
uv run python -m stoker_agent --config dev.toml   # M1.3
curl localhost:9101/metrics
```

## Проверки

```bash
uv run ruff check          # линт
uv run ruff format         # формат
uv run mypy                # типы (strict)
uv run pytest              # тесты
```

## Структура

- `src/stoker_agent/collectors/` — `GpuCollector` (nvidia/amd), system
- `src/stoker_agent/miners/` — `MinerDriver` (wildrig, …)
- `src/stoker_agent/transport/` — WS-клиент, `/metrics` endpoint
- `src/stoker_agent/commands/` — обработчики команд от сервера
