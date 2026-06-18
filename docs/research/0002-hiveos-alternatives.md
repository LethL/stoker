# Research 0002: Open-source аналоги HiveOS и архитектурные выводы

**Дата:** 2026-06-17
**Этап:** Pre-M0 (pre-flight)
**Метод:** веб-поиск по open-source rig-менеджерам, GPU-экспортёрам, miner API.

## Summary

**Нет живого open-source проекта, делающего то, что планирует Stoker**
(agent-на-риге + центральный FastAPI/SQLite control-server + Prometheus/Grafana +
React UI с удалённым start/stop майнера). Ближайшие «rig manager» (MiningMonitor,
Minera, cryptoGlance, rigsmonitoring) — **мертвы/заархивированы (2019–2021)**,
на C#/PHP/CoffeeScript, под ASIC/Ethash-эпоху. Живая экосистема разделилась:

1. **Метрики/мониторинг** — решено зрелыми Prometheus-экспортёрами
   (`utkuozdemir/nvidia_gpu_exporter`, `NVIDIA/dcgm-exporter`) + Grafana.
   Это commodity, переизобретать не нужно.
2. **Fleet management / control** — доминирует закрытый SaaS (HiveOS, minerstat,
   Foreman, Awesome Miner). Открыт только *агент сбора* у Foreman; control-plane
   закрыт/облачный.

**Вывод:** мониторинг-половина Stoker — тонкая интеграция поверх готовых
экспортёров; control-половина (WS-команды, lifecycle майнера, React UI) — реально
не закрытая ниша, она и оправдывает разработку. Переиспользуем метрики, строим
control-plane.

## По проектам

### GPU-экспортёры (переиспользуемый слой)

- **utkuozdemir/nvidia_gpu_exporter** — https://github.com/utkuozdemir/nvidia_gpu_exporter
  — ~1.5k★, активен, Go, MIT. Оборачивает `nvidia-smi`, один статический бинарь,
  работает на consumer GeForce. Grafana dashboard ID 14574. Не даёт hashrate
  (это из API майнера). **Самый релевантный.** Maintainer предупреждает об
  ограниченном времени на issues/PR.
- **NVIDIA/dcgm-exporter** — https://github.com/NVIDIA/dcgm-exporter — ~1.8k★,
  очень активен, Go, Apache-2.0, порт 9400. Богатейшие метрики, но
  **K8s/datacenter-ориентирован**, требует DCGM. **Overkill для 3 consumer-ригов.**
- **mindprince/nvidia_gpu_prometheus_exporter** — устарел, вытеснен utkuozdemir.

### Экспортёры телеметрии майнеров

- **platofff/prometheus-mining** — https://github.com/platofff/prometheus-mining
  — pull-модель: центральный экспортёр скрейпит HTTP API ригов. Поддержка
  **T-Rex (4067), lolMiner (4069), TeamRedMiner (4028)**. Хороший референс
  маппинга miner-API → Prometheus.
- **leonardochaia/xmrig-monitoring** — референс docker-compose: риги с
  node-exporter + xmrig-exporter, центральный Prometheus + Grafana + Alertmanager.
  Хороший шаблон для `infra/`.

### Мёртвые «rig manager» (только как уроки)

- **lennykean/MiningMonitor** — https://github.com/lennykean/MiningMonitor — C#/TS,
  MIT, последний релиз июль 2021. Гибрид agent+central, **LiteDB** по умолчанию,
  pull, threshold-алерты с действиями. Концептуально **ближайший к Stoker** — мёртв.
- **getminera/minera** (PHP, ~2021), **cryptoGlance** (архивирован, PHP),
  **tsileo/rigsmonitoring** (Python/CoffeeScript, заброшен).

### SaaS / закрытые (только UX-референс)

- **HiveOS, minerstat, Awesome Miner** — закрыты, облачные.
- **Foreman** (foreman.mn) — облачный control-plane, открыт только агент сбора,
  ASIC-focused.
- **Hashrate.no** — профит/бенчмарки, по сути SaaS.

### T-Rex HTTP API (целевой майнер) — https://github.com/trexminer/t-rex/wiki/api

- Default bind **0.0.0.0:4067** (`--api-bind-http`).
- **`GET /summary`** — полная телеметрия JSON: total `hashrate` +
  `hashrate_minute/hour/day`; per-GPU `temperature`, `fan_speed`, `power`,
  `hashrate`, `intensity`; `active_pool`, `accepted/rejected/solved_count`,
  `uptime`, `gpu_total`, `version`.
- **`GET /control`** — `?command=shutdown`, `?pause=true|false` (можно `:0,2,3`
  по конкретным GPU), `?time-limit=N`, и т.д.
- **`/config`** (GET/POST) — чтение/правка конфига в рантайме (pool, лимиты),
  может писаться в файл.
- **Дыра в безопасности:** T-Rex **не разделяет** read-only `/summary` и
  привилегированные `/config`/`/control` на одном порту — открытый API раскрывает
  wallet/pool config и позволяет shutdown. **Агент Stoker должен биндить API
  майнера на localhost и брокерить доступ сам.**

## Архитектурные выводы

### 1. Присоединяться к существующему проекту?
**Нет — строить, но строить меньше.** Все пересекающиеся по *control+UI* проекты
мертвы или закрыты; ни один не годится как база (язык/эпоха/заброшенность).
Но **слой метрик строить не надо** — это commodity. Защитимый scope = ровно то,
что не закрыто: открытый self-hosted **control-plane** (start/stop/config майнера)
+ современный React UI рядом с готовыми Prometheus/Grafana. Совпадает с планом M0–M4.

### 2. Свой pynvml `/metrics` vs готовый экспортёр
- **(A)** Переиспользовать `utkuozdemir/nvidia_gpu_exporter` для GPU-метрик,
  а агент Stoker отдаёт только miner-метрики (hashrate, shares из `/summary`).
  Плюс: нулевая поддержка GPU-телеметрии. Минус: два процесса и два scrape-таргета
  на риг, корреляция GPU↔miner в Grafana через лейблы.
- **(B)** Свой pynvml-коллектор в агенте + единый `/metrics`. Плюс: один процесс,
  один таргет, единые лейблы (`rig`/`gpu`/`miner`); **pynvml — заявленная цель
  обучения**. Минус: переизобретаем то, что уже решено; pynvml на consumer-картах
  иногда капризен.

**Рекомендация: (B)** — агент всё равно уже опрашивает T-Rex API на риге, так что
один процесс/таргет чище. Имена метрик согласовать со стилем dcgm-exporter для
переносимости дашбордов. dcgm-exporter в зависимости не брать (K8s-shaped).

### 3. Транспорт agent↔server для команд
- Для *метрик* — pull (Prometheus скрейпит `/metrics` агента), индустриальный
  стандарт, уже в плане — верно.
- Для *команд* — **WebSocket agent→server (агент дозванивается наружу)**, как по
  сути делают HiveOS/Foreman. Нет входящих дыр в файрволе ригов, push команд с
  низкой задержкой, живой статус «connected». **Ни один open-проект не сделал
  чистый командный канал** — это и есть вклад Stoker. SSH-control запрещён
  правилами проекта без ADR.

### 4. Как аналоги отдают телеметрию и контроль майнера
- Паттерн: **каждый современный GPU-майнер отдаёт локальный HTTP JSON API**
  (T-Rex 4067, lolMiner ~4069, TeamRedMiner 4028, XMRig 8080). Телеметрия через
  `/summary`, контроль — тот же API.
- **Start** API не умеет (у остановленного майнера нет API) → **агент владеет
  lifecycle процесса** (spawn/kill t-rex через systemd/subprocess), а HTTP API
  использует для pause/resume/reconfig/телеметрии во время работы.

### 5. Типичные грабли аналогов
- **Безопасность API**: открытый T-Rex API без read/write-разделения. → биндить
  API майнеров на localhost; агент — единственный клиент; сервер брокерит контроль
  через аутентифицированный WS.
- **Жёсткая привязка к одной монете/майнеру/эпохе** — причина смерти Minera/
  cryptoGlance/MiningMonitor. → **абстрагировать майнер за интерфейсом** (`miners/`
  с t-rex-враппером уже в плане), добавление lolMiner/gminer — аддитивно.
- **Переизобретение хранилища метрик** (LiteDB/Mongo + кастомные графики) сгнило.
  → Prometheus+Grafana, числовые time-series вне SQLite (граница Stoker верна).
- **Bus-factor экспортёров** — пинить версии; вендорить Grafana dashboard JSON,
  а не зависеть от remote ID.
- **Grafana Agent EOL (ноя 2025)** → plain Prometheus scraping (уже так) или Alloy.

## Рекомендация для Stoker

1. **Строить — ниша реальна и не закрыта.** Открытые аналоги мертвы, живые —
   закрытый SaaS или просто экспортёры. Планируемая архитектура здравая.
2. **Не строить хранилище/дашборды метрик** — Prometheus + Grafana, вендорить JSON.
3. **Агент `/metrics`**: pynvml-коллектор + скрейп T-Rex `/summary` в единый
   `/metrics`. Имена метрик в стиле dcgm-exporter.
4. **Control-plane = дифференциатор**: agent-initiated WebSocket к FastAPI; агент
   владеет lifecycle майнера (start/stop через systemd/subprocess), T-Rex HTTP API
   (localhost) для pause/resume/reconfig/телеметрии.
5. **Безопасность с первого дня**: никогда не выставлять miner API в сеть; весь
   контроль — через аутентифицированный канал server↔agent. Достойно ADR.
6. **Майнер за интерфейсом** (`miners/t-rex` сейчас, lolMiner/gminer позже).

**Референс-репо:** platofff/prometheus-mining (маппинг miner-API→Prometheus),
utkuozdemir/nvidia_gpu_exporter (имена метрик + Grafana dashboard 14574),
leonardochaia/xmrig-monitoring (layout docker-compose), trexminer/t-rex wiki (API).

## Источники

- https://github.com/utkuozdemir/nvidia_gpu_exporter
- https://github.com/NVIDIA/dcgm-exporter
- https://github.com/platofff/prometheus-mining
- https://github.com/leonardochaia/xmrig-monitoring
- https://github.com/lennykean/MiningMonitor
- https://github.com/trexminer/t-rex/wiki/api
- https://github.com/AleksandrParamonov/T-Rex-miner-Readonly-API
- https://foreman.mn
