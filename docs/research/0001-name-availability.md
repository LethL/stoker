# Research 0001: Доступность имени «Stoker»

**Дата:** 2026-06-17
**Этап:** Pre-M0 (pre-flight)
**Метод:** веб-поиск по GitHub, PyPI, npm, Docker Hub, общим коллизиям.

## Вердикт

Имя **«Stoker» разумно безопасно** для self-hosted pet-проекта по мониторингу
ригов. Самая заметная коллизия — npm-пакет `stoker` (утилита для Hono/OpenAPI,
~437★, ~8.4k загрузок/нед), но это чужой namespace (web-tooling, не майнинг/ops).
**PyPI `stoker` свободен** (404) — а это для нас важнее всего, т.к. agent и
server на Python/`uv`. Проектов по мониторингу майнинга с таким именем нет —
риск путаницы в нише низкий.

## GitHub

- **`w3cj/stoker`** — https://github.com/w3cj/stoker — утилиты для Hono и
  `@hono/zod-openapi` (HTTP-статусы, middleware, OpenAPI). TS, MIT, ~437★,
  активно поддерживается. Единственный заметный «Stoker»-проект, но другой домен.
- В нише майнинг/rig-monitoring/DevOps-monitoring проектов с именем «stoker» нет.
- Не-коллизии (похожее написание): `openstorage/stork`, `aauren/stork`
  (ISC Stork — мониторинг Kea DHCP/BIND), `fodinabor/stoke`.

**Severity: Low** — npm-namespace занят, но в поиске по майнингу имя свободно.

## PyPI

- **`stoker` не существует** (404). Свободно.
- `stoker-agent` / `stoker-server` — тоже свободны.
- Похожие, но не коллизии: `stoke` (PyTorch), `stocker` (stock-price ANN).

**Severity: None** — самый важный для проекта namespace чист.

## npm

- **`stoker`** — занят пакетом `w3cj/stoker` (Hono/OpenAPI).

**Severity: Low** — публикация npm-пакета не планируется; React-фронт имел бы
своё имя. Если когда-то понадобится — скоупить: `@yourname/stoker-web`.

## Docker Hub

- Заметных/официальных `stoker`-образов нет. `stoker-server` / `stoker-agent`
  свободны для публикации. Несвязанное: `openstorage/stork`, древний
  `chrisciborowski/stokerweb` (~8 лет назад).

**Severity: Negligible.**

## Прочее / культурный контекст

- Нишевый headless-CMS «Stoker» (`stoker-website.web.app`) — другой домен.
- BBQ/smoker-контроллеры «Stoker» / «Savannah Stoker» — железо-термостаты,
  тематически близко («управляет тем, что греется»), но другой рынок.
- Сильного защищённого софт-трейдмарка нет. «Stoker» — словарное слово
  (кочегар, тот кто топит печь) — ровно та метафора для горячих ригов, плюс
  Bram Stoker и фильм «Stoker» (2013) размывают термин в нашу пользу.

**Severity: Low.**

## Рекомендация

**Использовать «Stoker» как есть** для проекта, репо и Python-пакетов:
- **PyPI**: `stoker-agent`, `stoker-server` свободны — занять при публикации.
- **Docker Hub**: `stoker-server` / `stoker-agent` свободны.
- **Не публиковать публичный npm-пакет `stoker`** (занят) — для фронта неактуально.

Опциональный дисамбигуатор для майнинг-ниши: `stoker-mon` / `stoker-rigs`, но не
обязателен.

## Источники

- https://github.com/w3cj/stoker
- https://www.npmjs.com/package/stoker
- https://pypi.org/pypi/stoker/json (404)
- https://stoker-website.web.app/
- https://www.savannahstoker.com/
- https://hub.docker.com/r/chrisciborowski/stokerweb
