# Research 0005: Best practices реализации стека Stoker

**Дата:** 2026-06-18
**Этап:** M0 (глубокий архитектурный research)
**Вопрос:** конкретные паттерны и грабли (2025–2026) под наш стек — Python-агент
(один asyncio-процесс: `/metrics` + WS-клиент + поллеры) и FastAPI WS-хаб +
SQLModel/SQLite.

## Summary

Форма «один async-процесс делает три долгоживущие вещи» (агент) и «FastAPI-хаб с
многими WS-соединениями + крошечный SQLite-state» (сервер). В нашем масштабе
(~3 рига, один оператор) почти у каждой «очевидно сложной проблемы» — скучный
правильный ответ, а спорные выборы (async-SQLite, prometheus в потоке vs ASGI) в
основном не важны — берём проще. **Реально кусают только две вещи:** (a) детект
мёртвого WS-соединения / реконнект на агенте, (b) backpressure к медленному/
мёртвому агенту на хабе. Туда — бюджет внимания.

Решения «сверху»:
- **Метрики агента:** `make_asgi_app()` на uvicorn ИЛИ потоковый
  `start_http_server` — оба ок, поток здесь нормален.
- **Конкурентность агента:** `asyncio.TaskGroup` + `loop.add_signal_handler(SIGTERM)`.
- **WS-клиент агента:** библиотека **`websockets`**, цикл `async for ws in connect(...)`.
  Не хардкодить реконнект руками.
- **Хаб сервера:** `ConnectionManager` (dict по agent_id), try/except на каждый
  send, чистка мёртвых. Токен в заголовке при connect.
- **БД сервера:** честно — **sync SQLModel в threadpool FastAPI лучше** для нашего
  масштаба, чем async+aiosqlite. Если async ради обучения — ок, но PRAGMA через
  `engine.sync_engine`.

## 1. Агент: `/metrics` + WS-клиент + поллеры в одном процессе

**1a. Prometheus без блокировки loop.** Вариант A: `start_http_server(port)` —
свой daemon-поток, loop не трогается, метрики — это чтение in-memory счётчиков,
GIL-контеншн ничтожен. Вариант B (чище): `make_asgi_app()` на uvicorn в том же
loop, без потока. **Грабли:** не лезть в `multiprocessing`-режим
prometheus-client — один процесс, один registry.

**1b. TaskGroup + SIGTERM.** `asyncio.TaskGroup` (3.11+) супервизит три цикла;
SIGTERM через `loop.add_signal_handler` → ставит `asyncio.Event`, циклы выходят
чисто. **Не** полагаться на дефолт `asyncio.run` (он не ловит SIGTERM от systemd,
рвёт всё резко). `TaskGroup` = structured concurrency: падение любого таска
отменяет соседей и поднимает `ExceptionGroup` (ловить через `except*`). JS-аналог:
как `Promise.all`, но с гарантированной отменой остальных при первом провале.
**Грабли:** `add_signal_handler` — только Unix, только внутри loop; не глотать
`CancelledError` (это `BaseException`, `except Exception` его не ловит — хорошо,
а `except BaseException` сломает отмену).

**1c. pynvml из async.** Пакет `nvidia-ml-py` (импорт `pynvml`). `nvmlInit()` один
раз на старте, `nvmlShutdown()` один раз на стопе, каждый блокирующий вызов в
`asyncio.to_thread`. **Грабли:** сбои драйвера/карты (`NVMLError_GpuIsLost`)
ловить **per-device, per-call** — одна отвалившаяся карта не должна ронять поллер.
Хэндлы перечислять заново при ошибке (индексы сдвигаются после reset драйвера).

## 2. Агент: устойчивый долгоживущий WS-клиент

**Библиотека: `websockets`** (`from websockets.asyncio.client import connect`), не
httpx (нет WS-клиента). Цикл `async for ws in connect(uri, ping_interval=20,
ping_timeout=20, additional_headers={"Authorization": ...})` — авто-реконнект с
экспоненциальным backoff на транзиентных ошибках, встроенный keepalive.
**Главная граблина: тихие half-open соединения.** Без keepalive соединение, где
сервер исчез (питание/NAT-таймаут/кабель), выглядит живым вечно — висишь в
`recv()` и не реконнектишь. `ping_interval`/`ping_timeout` это и ловят —
**не ставить `ping_timeout=None` на агенте.** Ещё: не блокировать loop в
обработчике команд (иначе keepalive ложно таймаутит); ограничивать очередь
отправки.

## 3. Сервер: FastAPI WS-хаб для многих агентов

**ConnectionManager** = `dict[str, WebSocket]` по agent_id (не list — нужен
targeted send команде конкретному ригу). Регистрация на connect, удаление на
disconnect, чистка при ошибке send (try/except вокруг каждого `send_json`).

**Auth на хендшейке:** валидировать токен **до `accept()`**. Агент — Python-клиент
(не браузер), поэтому **заголовок `Authorization: Bearer` — чисто и норм** (в
браузере нельзя — это главная путаница туториалов, но к нам не относится). Плохой
токен → `await ws.close(code=1008)` (policy violation).

**Грабли — backpressure:** медленный/мёртвый агент блокирует хаб. `await
ws.send_json()` может зависнуть и застопорить остальные отправки. Митигации:
try/except + prune (мёртвый сокет удаляется, а не ретраится в строке); broadcast
через `asyncio.gather(..., return_exceptions=True)`; для истинно медленного —
ограниченная per-agent `asyncio.Queue` с writer-таском. **Redis не нужен** — это
для горизонтального масштабирования; **один uvicorn-воркер** → in-memory dict
корректен.

## 4. Сервер: FastAPI + SQLModel + SQLite

**Честный вывод первым:** на 3 рига **sync SQLModel в threadpool FastAPI — проще и
надёжнее**, чем async+aiosqlite, если async-SQLite не самоцель обучения. SQLite
single-writer независимо от async; `aiosqlite` сам — обёртка с фоновым потоком на
соединение (т.е. потоки и так под капотом); `def`-эндпоинт FastAPI авто-уводится
в threadpool. Async тут почти ничего не покупает (нет высоконагруженной БД).

**Если async (ради обучения):** драйвер `aiosqlite`, `AsyncEngine` +
`async_sessionmaker(expire_on_commit=False)`, dependency `get_session` (yield),
`lifespan` для `create_all`.

**SQLite-грабли:** `journal_mode=WAL` (читатели + один писатель сосуществуют);
`busy_timeout=5000` (дефолт 0 → спонтанные «database is locked»); PRAGMA вешать на
**`engine.sync_engine`**, не на async-engine (иначе PRAGMA молча не применяются);
`expire_on_commit=False` (иначе lazy-refetch → неявный IO / `MissingGreenlet`).
SQLite **single-writer** — async даёт неблокирующую запись со стороны loop, но
сериализованную в БД; транзакции держать короткими.

**SQLModel (2025–2026):** ещё `0.0.x`, рабочий happy-path, но тонкий. Для
mypy-strict (требование CLAUDE.md): включить **Pydantic mypy-plugin**
(`init_typed`, `init_forbid_extra`); `Relationship()` аннотировать явно
(`list["Rig"]`, кавычки-форвард-рефы); часть Pydantic `Field`-параметров (`strict`,
`validate_default`, `kw_only`) не проброшены в SQLModel `Field`. **Паттерн:**
держать table-модели (`table=True`) отдельно от API request/response-моделей; не
отдавать table-модели наружу напрямую.

## 5. Сквозные грабли

- prometheus-поток × asyncio: апдейт метрик из loop при чтении из потока — безопасно
  (registry thread-safe). Не лезть в multiprocess. В кастомном `Collector` не `await`.
- **Тесты:** `httpx.AsyncClient(transport=ASGITransport(app=app))` для REST;
  **Starlette `TestClient` для WebSocket** (у httpx нет WS-клиента); async-тесты
  через `@pytest.mark.anyio`/pytest-asyncio. Manager/engine/config — инъектируемые
  (`app.dependency_overrides`), не import-time глобалы.
- **Конфиг:** `pydantic-settings` + `tomllib` (stdlib 3.11+) или
  `TomlConfigSettingsSource` (≥2.2) — TOML не читается нативно старым
  pydantic-settings. Типизированный валидируемый конфиг = «Zod-схема для конфига».
- Не блокировать loop в WS-хэндлерах с обеих сторон; всё блокирующее — через
  `to_thread` или `httpx.AsyncClient` (miner JSON API).
- **Один uvicorn-воркер** на сервере: in-memory хаб + SQLite-WAL корректны только
  так. Без `--workers N`.

## Чеклист граблей для Stoker

- [ ] Агент WS: **никогда не отключать `ping_timeout`**; цикл `async for ws in connect(...)`.
- [ ] Агент: **не блокировать loop** — pynvml и любой sync I/O через `to_thread`.
- [ ] Агент shutdown: **SIGTERM через `loop.add_signal_handler`**, супервизия 3
      циклов через `TaskGroup`, быстрый finalize (systemd SIGKILL по `TimeoutStopSec`).
- [ ] Агент NVML: **per-device, per-call `try/except NVMLError`**; init/shutdown по разу.
- [ ] Хаб: **dict по agent_id**; try/except на каждый send + prune мёртвых.
- [ ] Хаб: **валидировать токен до `accept()`**; агент — Python-клиент, заголовок ок.
- [ ] Сервер: **один uvicorn-воркер**; без Redis.
- [ ] SQLite: **WAL + busy_timeout=5000 через `@event.listens_for(engine.sync_engine, "connect")`**.
- [ ] **Рассмотреть sync SQLModel-в-threadpool** вместо async+aiosqlite в нашем масштабе.
- [ ] SQLModel mypy-strict: Pydantic-плагин; аннотировать `Relationship()`;
      table-модели отдельно от API-схем.
- [ ] prometheus-client: только single-process registry.
- [ ] Тесты: `httpx.AsyncClient`+`ASGITransport` для REST; Starlette `TestClient` для WS.
- [ ] Конфиг: pydantic-settings + `tomllib`.

## Источники

- https://prometheus.github.io/client_python/exporting/http/asgi/
- https://docs.python.org/3/library/asyncio-task.html#task-groups
- https://pypi.org/project/nvidia-ml-py/
- https://websockets.readthedocs.io/en/stable/topics/keepalive.html
- https://fastapi.tiangolo.com/advanced/websockets/
- https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- https://sqlmodel.tiangolo.com/release-notes/
- https://docs.pydantic.dev/latest/integrations/mypy/
- https://fastapi.tiangolo.com/advanced/async-tests/
