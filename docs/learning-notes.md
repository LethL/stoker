# Learning notes

Автоконспект новых для автора концепций. Накапливается по ходу вех.

---

### 2026-06-22: uv (пакетный менеджер Python)
**Где встретилось:** `agent/`, `server/` (M1.1), `pyproject.toml`, `uv.lock`
**Что это:** быстрый менеджер пакетов и проектов на Rust; заменяет pip/poetry/pyenv.
**Зачем в проекте:** каждый Python-пакет — свой uv-проект (`uv init --package`,
src-layout); `uv add` ставит зависимости, `uv run` запускает в окружении проекта.
**Аналог в JS:** pnpm + nvm в одном: `uv add` ≈ `pnpm add`, `uv.lock` ≈ `pnpm-lock.yaml`,
`uv run` ≈ `pnpm exec`, плюс uv сам ставит нужный Python (как nvm — node).
**Что почитать:** https://docs.astral.sh/uv/
**Подводные камни:** `uv run --frozen` (в CI) падает, если lock устарел против
pyproject — менять зависимости только через `uv add/remove`, не руками.

### 2026-06-22: ruff + mypy (--strict)
**Где встретилось:** `[tool.ruff]`, `[tool.mypy]` в обоих pyproject (M1.1)
**Что это:** ruff — линтер+форматтер на Rust; mypy — статический тайпчекер.
**Зачем в проекте:** качество кода обязательно (CLAUDE.md). ruff = lint+format,
mypy strict требует типизации всех функций.
**Аналог в JS:** ruff ≈ ESLint + Prettier (в одном, очень быстрый); mypy ≈ `tsc`
со строгими флагами (`strict: true`).
**Что почитать:** https://docs.astral.sh/ruff/ · https://mypy.readthedocs.io/
**Подводные камни:** mypy в src-layout нужно подсказать, где искать пакет
(`mypy_path="src"`, `explicit_package_bases=true`); для Pydantic — `plugins =
["pydantic.mypy"]`, иначе ложные ошибки на моделях.

### 2026-06-22: pydantic-settings + tomllib
**Где встретилось:** `server/config.py`, `agent/config.py` (M1.2/M1.3)
**Что это:** `BaseSettings` — модель конфига, читающая значения из env (и др.
источников) с валидацией; `tomllib` — stdlib-парсер TOML (3.11+).
**Зачем в проекте:** типизированный конфиг сервера (env `STOKER_*`) и агента
(TOML-файл на риге).
**Аналог в JS:** как Zod-схема для `process.env` / конфиг-файла: валидирует,
типизирует, даёт дефолты.
**Что почитать:** https://docs.pydantic.dev/latest/concepts/pydantic_settings/
**Подводные камни:** kwargs в конструктор `Settings(**data)` имеют приоритет над
env — удобно для детерминизма в тестах; env-префикс задаётся в `model_config`.

### 2026-06-22: prometheus-client + make_asgi_app
**Где встретилось:** `agent/metrics.py`, `agent/main.py` (M1.3)
**Что это:** клиент Prometheus; `Gauge` — метрика «вверх-вниз» с лейблами;
`make_asgi_app()` отдаёт текущий registry как ASGI-приложение для scrape.
**Зачем в проекте:** агент выставляет `/metrics`, который скрейпит Prometheus
(pull-модель, ADR 0002/0006).
**Аналог в JS:** prom-client (та же концепция Gauge/Counter/Histogram).
**Что почитать:** https://prometheus.github.io/client_python/
**Подводные камни:** один процесс — один глобальный registry; не трогать
multiprocess-режим. Имена метрик — с unit-суффиксами (`_celsius`, `_watts`).

### 2026-06-22: asyncio.TaskGroup + graceful shutdown
**Где встретилось:** `agent/main.py` (M1.3)
**Что это:** `TaskGroup` (3.11+) — structured concurrency: супервизит группу
задач, при падении одной отменяет остальные и поднимает `ExceptionGroup`.
SIGTERM/SIGINT ловим через `loop.add_signal_handler` → `stop`-event.
**Зачем в проекте:** агент держит несколько долгоживущих задач (HTTP `/metrics`,
поллер, позже WS-клиент); нужен надёжный supervisor и чистое завершение под systemd.
**Аналог в JS:** `Promise.all`, но с гарантированной отменой остальных при первом
провале + автоматическая чистка (как AbortController, встроенный в группу).
**Что почитать:** https://docs.python.org/3/library/asyncio-task.html#task-groups
**Подводные камни:** uvicorn по умолчанию **сам перехватывает сигналы**
(`capture_signals`) и переподнимает их — конфликтует с нашим обработчиком и
подвешивает/убивает процесс. Решение: субкласс `Server` с no-op `capture_signals`,
сигналами управляет наш единый `stop`-event. `loop.add_signal_handler` — только Unix.

### 2026-06-22: FastAPI + lifespan
**Где встретилось:** `server/main.py` (M1.2)
**Что это:** FastAPI — async веб-фреймворк; эндпоинты типизированы Pydantic;
`lifespan` — контекст для setup/teardown ресурсов на старте/остановке приложения.
**Зачем в проекте:** REST API сервера; `/healthz`; в lifespan позже — инициализация
БД (SQLite/SQLModel) и WS-хаба.
**Аналог в JS:** Express/NestJS, но типы и OpenAPI генерятся из моделей; lifespan ≈
хуки `onModuleInit`/`onModuleDestroy` в NestJS.
**Что почитать:** https://fastapi.tiangolo.com/advanced/events/
**Подводные камни:** тестировать async-эндпоинты через `httpx.AsyncClient` +
`ASGITransport` (без реальной сети); у httpx нет WS-клиента (для WS — Starlette TestClient).

### 2026-06-22: Vue 3.5 + Vite + Tailwind v4 + Vitest
**Где встретилось:** `web/` (M1.1; ADR 0007)
**Что это:** Vue 3.5 SFC с `<script setup lang="ts">` (Composition API); Vite —
сборщик/dev-сервер; Tailwind v4 — utility-CSS (подключается Vite-плагином + один
`@import "tailwindcss"`, без `tailwind.config.js`); Vitest — тест-раннер на Vite.
**Зачем в проекте:** UI (M3). Vue выбран ради роста (второй фреймворк после React).
**Аналог в JS:** это и есть JS-мир. Для React-бэкграунда: `<script setup>` ≈ тело
функционального компонента; `ref`/`reactive` ≈ `useState`, но с прокси-реактивностью;
SFC `<template>` ≈ JSX, но отдельной секцией.
**Что почитать:** https://vuejs.org/ · https://tailwindcss.com/ · https://vitest.dev/
**Подводные камни:** typecheck для Vue — `vue-tsc` (не `tsc`), т.к. нужны типы из SFC;
Tailwind v4 настраивается иначе, чем v3 (нет config-файла по умолчанию).
