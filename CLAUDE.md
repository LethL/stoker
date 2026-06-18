# Stoker

Self-hosted мониторинг и базовое управление майнинг-ригами.
Pet-проект, используется автором на личных ригах.

Приложение поверх Ubuntu/Debian (не дистрибутив, не OS-образ).
Если окажется полезен ещё кому-то — отлично, но это не первичная цель.

## Цели проекта

1. **Полезность** — рабочий инструмент управления своими ригами,
   заменяющий критичные функции HiveOS на личных машинах.
2. **Обучение** — Python, React 19, FastAPI, Prometheus, Grafana,
   работа с агентскими системами (Claude Code).
3. **Дисциплина итераций** — каждая M-веха самодостаточна,
   проект остаётся полезным на любой точке остановки.

## Scope

**Что Stoker делает (после M4):** мониторинг ригов с историческими
графиками, удалённый запуск/остановка майнера, базовый UI со списком
ригов и статусом.

**Чем Stoker НЕ является:**

- Не альтернатива HiveOS целиком **на этапе M0–M4**. При этом
  **HiveOS — долгосрочный эталон (north star) по функциональности и UX**:
  полноценное управление (flight sheets, кошельки, пулы, настройки карт) —
  цель, к которой ведёт roadmap после M4. Это **аспирация, не обязательство
  по фичам и срокам** (детали и прогрессия — в `docs/roadmap.md`).
- Не OS-дистрибутив. Не делаем ISO, не патчим ядро,
  не собираем драйверы.
- Не SaaS, не multi-tenant, не для community-релиза
  на этапе M0-M4. Возможно позже, но без обязательств.

**Целевой профиль пользователя:** Linux-грамотный человек,
комфортный с SSH, systemd, docker-compose. Не для новичков.

## Контекст автора (для калибровки объяснений)

- Frontend-разработчик, глубоко знает JS/TS/React
- Python изучает в процессе работы над проектом — объясняй
  концепции с аналогиями из JS-мира где уместно
- Опыт работы с Linux, SSH, hardware diagnostics, mining
- Pet-проект, нет дедлайнов — приоритет на качество объяснений
  и понимание автором каждого решения

## Архитектура

```
┌────────────────────────────────────────────────────┐
│  React 19 UI (web)                                 │
│  Управление + embedded Grafana панели              │
└────────────────────────────────────────────────────┘
           ↑                          ↑
┌──────────────────┐      ┌──────────────────────┐
│ FastAPI server   │      │ Prometheus + Grafana │
│ Команды, конфиги │      │ Метрики, графики,    │
│ State (SQLite)   │      │ алерты (позже)       │
└──────────────────┘      └──────────────────────┘
           ↑                          ↑
┌────────────────────────────────────────────────────┐
│  Agent на риге (Python)                            │
│  WS-клиент к серверу (команды/конфиги)             │
│  /metrics endpoint (Prometheus scrape)             │
│  Управление майнерами                              │
└────────────────────────────────────────────────────┘
```

### Разделение ответственности

| Слой | За что отвечает |
|------|-----------------|
| **agent/** | Сбор GPU-метрик через слой `GpuCollector` (Nvidia/pynvml сейчас, AMD позже), телеметрия майнера через `MinerDriver`, выставление `/metrics`, выполнение команд от сервера, запуск/остановка майнеров |
| **server/** (FastAPI + SQLite) | API, WebSocket-хаб для агентов, хранение state (конфиги ригов, команды, события), авторизация |
| **Prometheus** | Хранение всех time-series метрик (hashrate, температуры, fan, power) |
| **Grafana** | Все исторические графики, дашборды, алерты (в будущих вехах) |
| **web/** (React 19) | Управляющий UI, список ригов, статус, embedded Grafana панели через iframe |

**Принцип границы:** числовые метрики во времени → Prometheus.
Всё остальное (state, конфиги, события, команды) → SQLite через сервер.

## Стек

| Слой | Технологии |
|------|-----------|
| Python | 3.12+, **uv** (package manager), **ruff** (lint+format), **mypy** (strict), **pytest** |
| Backend | **FastAPI**, **SQLModel**, **Pydantic**, **httpx**, **WebSockets** |
| Metrics collection | **prometheus-client** (Python), **pynvml** (Nvidia сейчас; AMD через rocm-smi/sysfs позже — см. ADR 0004) |
| Mining infra | **Prometheus**, **Grafana** (через docker-compose) |
| БД | **SQLite** (один файл, без отдельного сервера) |
| Frontend | **React 19** + **Vite** + **TypeScript**, **TanStack Query**, **TanStack Router**, **Zustand**, **Tailwind CSS** |
| Deploy | **Docker Compose** (сервер), **systemd unit** (агент) |
| CI | **GitHub Actions** |

### Почему именно так

- **uv** вместо pip/poetry — современный быстрый менеджер,
  активно развивается, проще onboarding нового пакета.
- **SQLModel** вместо raw SQLAlchemy — Pydantic + SQLAlchemy
  в одном, типизация наследуется в API.
- **SQLite, не PostgreSQL** — на 3 рига более чем достаточно.
  Если когда-нибудь упрёмся — миграция через SQLModel почти бесплатна.
- **React 19, не Vue** — у автора уже сильный React-бэкграунд.
  Не размазываем когнитивную нагрузку: новое в проекте — Python,
  DevOps-стек, метрики. Фронт в знакомом фреймворке.
  React 19 сам по себе достаточно новый (Server Components,
  Actions, useOptimistic, React Compiler).
- **TanStack Router** вместо React Router — лучшая типизация,
  type-safe params, повод изучить.
- **Zustand** вместо Redux — простой клиентский стейт,
  для дашборда более чем достаточно.
- **Prometheus + Grafana**, а не своя реализация метрик —
  индустриальный стандарт, меньше кода писать, навык универсальный.

### Чего НЕ используем

- ❌ `requests` — только `httpx` (async-friendly, современный API)
- ❌ Raw SQLAlchemy — только через `SQLModel`
- ❌ `pip`/`poetry`/`pipenv` — только `uv`
- ❌ Redux/Redux-Toolkit — `Zustand` для клиентского стейта
- ❌ React Router — `TanStack Router`
- ❌ axios — `fetch` через `TanStack Query`, нативный API
- ❌ Синхронные обработчики в FastAPI без явной причины (всё async)

## Структура репозитория

```
stoker/
├── CLAUDE.md                    # этот файл
├── README.md
├── docker-compose.yml           # server + prometheus + grafana
├── .gitignore
├── .claude/
│   ├── agents/                  # subagent definitions
│   │   └── researcher.md
│   └── commands/                # custom slash commands
│       ├── test.md
│       └── explain.md
├── agent/                       # Python демон, ставится на риг
│   ├── pyproject.toml           # uv project
│   ├── src/stoker_agent/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── collectors/          # GpuCollector: nvidia (pynvml) сейчас, amd позже; system
│   │   ├── miners/              # MinerDriver: wildrig сейчас, t-rex/др. позже
│   │   ├── transport/           # WS client, /metrics endpoint
│   │   └── commands/            # обработчики команд от сервера
│   ├── tests/
│   └── README.md
├── server/                      # FastAPI приложение
│   ├── pyproject.toml
│   ├── src/stoker_server/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── api/                 # REST endpoints
│   │   ├── ws/                  # WebSocket хаб для агентов
│   │   ├── models/              # SQLModel
│   │   ├── db.py
│   │   └── config.py
│   ├── tests/
│   └── README.md
├── web/                         # React 19 SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── routes/              # TanStack Router
│   │   ├── components/
│   │   ├── api/                 # клиент для сервера
│   │   └── stores/              # Zustand
│   └── README.md
├── infra/
│   ├── prometheus/
│   │   └── prometheus.yml       # scrape configs
│   └── grafana/
│       ├── provisioning/        # datasources, dashboards autoload
│       └── dashboards/          # JSON определения дашбордов
├── .github/
│   └── workflows/
│       └── ci.yml               # lint + test для agent, server, web
└── docs/
    ├── architecture.md          # высокоуровневая архитектура
    ├── agent-protocol.md        # формат WS-сообщений
    ├── metrics.md               # список Prometheus метрик
    ├── decisions/               # ADRs
    │   ├── 0001-not-an-os.md
    │   ├── 0002-prometheus-for-metrics.md
    │   ├── 0003-miner-driver-abstraction.md
    │   ├── 0004-gpu-collector-abstraction.md
    │   ├── 0005-miner-api-localhost-binding.md
    │   └── 0006-metrics-transport-reachability.md
    ├── research/                # отчёты сабагентов
    ├── roadmap.md               # "если захочется" фичи без обязательств
    └── learning-notes.md        # автоконспект новых концепций
```

**Это монорепа** в смысле "один git-репозиторий, три независимых
пакета". Без unified build system (без Nx/Turborepo/workspaces).
Каждый пакет (agent, server, web) собирается своим менеджером.
Шарить код между пакетами не нужно. Если возникнет необходимость
шарить схемы протокола — генерировать из JSON Schema/OpenAPI,
не через shared package.

## Конвенции

### Python

- **Типизация обязательна.** mypy в strict режиме на CI,
  все функции типизированы.
- **Pydantic-модели** для всех данных, пересекающих границы
  (API, WS-сообщения, конфиги, парсинг внешних данных).
- **Async везде** — никаких блокирующих вызовов в event loop.
  Если нужен sync I/O — через `asyncio.to_thread`.
- **httpx** для HTTP, не requests.
- **SQLModel** для БД, не raw SQLAlchemy.
- **На каждую функцию с логикой — pytest-тест.**
- Формат: `ruff format`. Линт: `ruff check`. Оба до коммита.

### TypeScript / React

- **strict: true** в tsconfig, никаких `any` без явного обоснования.
- Компоненты — функциональные, hooks.
- Server state через **TanStack Query**, не useState с fetch.
- Client state через **Zustand**, не useContext для глобального.
- Стили — **Tailwind utility classes**, без styled-components.

### Git

- **Conventional Commits**: `feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`, `ci:`.
- Коммит после каждой осмысленной единицы (не "WIP" каждые 5 минут,
  но и не один мега-коммит на всю фичу).
- Никаких креденшалов, секретов, ключей в коде.
  Только через env / `.env` файлы (которые в `.gitignore`).

### Документация и решения

- **ADR на каждое архитектурное решение.**
  Файл `docs/decisions/NNNN-<slug>.md`, формат:
  Контекст → Решение → Обоснование → Последствия → Альтернативы.
- README в каждом пакете (`agent/`, `server/`, `web/`) — как запустить
  локально, как тестировать, что внутри.
- API документация генерируется FastAPI автоматически (OpenAPI),
  доступна по `/docs` в dev режиме.

## Режим обучения

Автор — frontend-разработчик, изучает технологии через этот проект.
Это **обучающий проект**, не "решить задачу как можно быстрее".

### Перед реализацией каждого осмысленного блока

(модуль, фича, нетривиальная функция)

1. Кратко объясни **что** будешь делать
2. Объясни **зачем** именно так, не иначе
3. Назови ключевые концепции/паттерны/библиотеки и **что они делают**
4. Если есть альтернативы — упомяни их и почему отверг
5. **Аналогии из JS/TS-мира приветствуются**, например:
   - "Pydantic BaseModel — как Zod schema, валидирует и типизирует"
   - "FastAPI Depends — DI через параметры функции, концептуально
     близко к NestJS providers"
   - "async/await в Python такой же как в JS, но event loop
     запускается явно через asyncio.run"
   - "SQLModel — как Prisma в TS-мире, ORM с генерацией типов"

### Во время реализации

- Комментируй неочевидное в коде с префиксом `# learn:`
  (или `// learn:` в TS).
  Эти комментарии можно потом убрать одним grep.
- Не комментируй очевидное (что такое функция, что такое if).

### После реализации

- Краткое резюме: что нового использовали, что стоит запомнить,
  ссылки на официальную документацию.
- Если ввели новую концепцию/библиотеку — добавь запись
  в `docs/learning-notes.md` по шаблону:

```markdown
  ### YYYY-MM-DD: <Концепция/библиотека>
  **Где встретилось:** ссылка на файл/коммит
  **Что это:** 1-2 предложения сути
  **Зачем в проекте:** конкретное применение
  **Аналог в JS:** если есть
  **Что почитать:** ссылки на официальные доки
  **Подводные камни:** что может укусить
```

### Чего НЕ делать в объяснениях

- Не лить воду — объяснения плотные, по делу.
- Не повторять то что уже объяснял в этой сессии.
- Не превращать каждый commit message в эссе.
- Не объяснять очевидные базовые концепции (функции, циклы, классы).

## Чего НЕ делать в проекте

- Не расширять scope без явного запроса от автора.
  Если кажется что нужна доп фича — спроси, не делай.
- Не делать OS-дистрибутив, не лезть в ядро/драйверы/initramfs.
- Не добавлять PostgreSQL, Redis, Celery, Kafka и подобную
  тяжёлую инфраструктуру без явного обоснования и ADR.
- Не делать свой майнинг-пул, прокси, кошелёк, биржевой адаптер.
- Не добавлять multi-user / RBAC / OAuth до явного запроса.
- Не реализовывать веб-SSH, web-консоль к ригу — security риск,
  нужен отдельный ADR с серьёзным обоснованием.
- Не использовать в коде запрещённые библиотеки (см. секцию
  "Чего НЕ используем" в Стеке).

## Запуск локально

```bash
# Сервер + Prometheus + Grafana
docker compose up -d

# Сервер dev-режим (с auto-reload)
cd server && uv run uvicorn stoker_server.main:app --reload

# Агент (на риге или локально с моком GPU)
cd agent && uv run python -m stoker_agent --config dev.toml

# Frontend
cd web && pnpm dev

# Тесты
cd agent && uv run pytest
cd server && uv run pytest
cd web && pnpm test

# Линт
cd agent && uv run ruff check && uv run mypy .
cd server && uv run ruff check && uv run mypy .
cd web && pnpm lint && pnpm typecheck
```

## Roadmap

Развитие через самодостаточные **M-вехи**. Каждая веха:
- даёт работающий, проверяемый функционал;
- может оказаться последней — проект остаётся полезным;
- не блокируется отсутствием будущих вех.

### Текущий план

- **M0** — Research-фаза. Анализ существующих open-source аналогов,
  проверка имени проекта, фиксация выводов в `docs/research/`.
- **M1** — Скелет monorepo, CI (GitHub Actions), базовый health-check
  на сервере, агент-заглушка отправляет фейковые метрики.
- **M2a** — Агент выставляет `/metrics` endpoint с реальными GPU-метриками.
  Слой `GpuCollector` (ADR 0004); реализуется Nvidia/pynvml (первый риг),
  AMD-реализация отложена за той же границей.
- **M2b** — docker-compose с Prometheus и Grafana, Prometheus
  scrape-ит агента.
- **M2c** — Первый Grafana дашборд: hashrate, температуры,
  fan, power. Provisioned автоматически.
- **M2d** — WebSocket агент↔сервер для команд и состояния
  (не для метрик — метрики идут через Prometheus).
- **M3** — React 19 UI: список ригов, статус подключения,
  embedded Grafana панели через iframe.
- **M4** — Запуск/остановка майнера с UI. Первый драйвер — WildRig Multi
  (`MinerDriver`, ADR 0003); API майнера на localhost, контроль брокерится
  агентом (ADR 0005). Конфиг майнера в TOML файле на риге.

**После M4 — пауза, рефлексия, решение.**

Идеи для дальнейших опциональных вех собраны в `docs/roadmap.md`
(AMD, alerts через Alertmanager, watchdog, flight sheets,
overclock, multi-pool failover, и т.д.) — **без сроков и без
обязательств**. Делается только то что хочется делать.

## Принципы работы

### Plan mode — для всего нетривиального

Перед реализацией задачи сложнее "поправь типо" — составить план,
показать автору, получить подтверждение, **только потом** писать
код. Не "иди делай и посмотрим что получится".

### Контекст — ресурс

`/clear` между несвязанными задачами. Контекст забивается → качество
ответов падает.

### Самодостаточные коммиты

После каждой логической единицы — коммит с осмысленным сообщением.
Это и точка отката, и контекст для агента (читает `git log`).

### ADR на каждое архитектурное решение

`docs/decisions/NNNN-<slug>.md`. Формат:

```markdown
# ADR NNNN: <title>
## Контекст
## Решение
## Обоснование
## Последствия
## Альтернативы и почему отвергнуты
```

### Бизнес-логика — в основном чате, не у сабагентов

Автор учится. Делегировать незнакомый код сабагенту = получить
работающий проект, который автор не понимает. Сабагентам отдавать:
research, тесты, code review, рутину.

## Сабагенты

На старте проекта настроен только:

- **researcher** (`/.claude/agents/researcher.md`) — исследовательские
  задачи, анализ внешних проектов, библиотек, технологий.
  Возвращает структурированные отчёты в `docs/research/`.

По мере роста проекта (после M2) могут быть добавлены:

- **python-builder** — реализация Python модулей по чёткому ТЗ.
  Использовать **осторожно** — только когда автор сам понимает
  что делает агент.
- **reviewer** — code review без правок, отчёт с замечаниями.
  Полезен перед коммитом крупных изменений.

## Текущий статус

**Проект на этапе M0 (research).** Pre-flight выполнен, выводы в
`docs/research/`:

- **0001** — имя «Stoker» свободно (PyPI/Docker Hub чисты; npm занят чужим
  пакетом, но фронт в npm не публикуется) → используем как есть.
- **0002** — живых open-source аналогов с control-plane нет (все мертвы либо
  закрытый SaaS); метрики не переизобретаем (Prometheus/Grafana), control-plane
  строим сами.
- **0003** — API майнера WildRig Multi: HTTP-JSON (XMRig-style), telemetry-only
  + best-effort pause/resume; lifecycle — через процесс/systemd.

Зафиксированы решения: ADR 0001–0005 (`docs/decisions/`). Ключевое уточнение
против исходного плана: парк **смешанный (AMD+Nvidia)**, поэтому сбор GPU-метрик
и майнер вынесены за абстракции (`GpuCollector`, `MinerDriver`); реализуется
Nvidia + WildRig первыми, AMD/другие майнеры — за теми же границами позже.

**Следующий шаг:** глубокий архитектурный research проектов схожей формы
(агент↔сервер, Prometheus, WebSocket-команды, веб-дашборд) для валидации плана
и сбора best practices. После него — старт M1 (скелет monorepo + CI +
health-check + агент-заглушка).