# Research 0004: Валидация архитектуры на сопоставимых проектах

**Дата:** 2026-06-18
**Этап:** M0 (глубокий архитектурный research)
**Вопрос:** рабочий ли наш скелет (агент↔сервер, Prometheus pull, WS-команды,
веб-дашборд) — на опыте зрелых проектов схожей формы (не майнинг-домен).

## Summary

Форма Stoker (агент на хосте + центральный сервер + веб-UI + Prometheus/Grafana)
**хорошо обоснована**. Ближайший аналог — **Beszel** (henrygd/beszel, ~22.9k★, MIT,
Go): та же топология hub+agent, тот же React 19 UI, то же разделение
«SQLite для state, не для time-series». Сильная валидация.

**НО один пункт плана — реальная проблема для нашей среды: расчёт на то, что
Prometheus будет *скрейпить* (`pull`) `/metrics` агентов.** Риги — домашние,
возможно за NAT/динамическим IP; pull требует, чтобы *сервер* инициировал
входящее соединение к каждому ригу — NAT это заблокирует. Это классическая
проблема, ради которой существуют `PushProx` и `remote_write`, и **именно её
Beszel решил, отказавшись от pull в пользу исходящего соединения от агента.**
Ирония: у Stoker **уже есть** нужный примитив — исходящий WebSocket агента для
команд — но план гоняет метрики мимо него через pull.

Остальные 4 решения (WS-хаб, SQLite-state, React UI, embedded Grafana) — здравые,
с известными управляемыми граблями.

## По проектам

- **Beszel** — изучить пристально. Два транспорта: **(основной)** агент
  устанавливает исходящее WS-соединение к hub и пушит данные; **(fallback)** hub
  ходит к агенту по SSH. Их док прямо говорит: SSH — для случая «hub достаёт
  агентов, но агенты не достают hub». Хранит time-series в **SQLite** с
  даунсэмплингом (1m→10m→…→8h), без Prometheus. UI — React 19 + WS-подписки для
  live. Auth: ED25519 для SSH, токен для WS.
- **Netdata** (~79k★) — agent-per-host, дети **стримят метрики исходящим**
  соединением к parent, с репликацией для добивки истории при реконнекте.
  Снова: соединение инициирует агент. Сильное свидетельство, что **push —
  доминирующий паттерн для флотов**.
- **Glances** (Python, ~32.8k★) — подтверждает, что Python-агент с `/metrics` —
  норма и просто (`--export prometheus`). Но server-mode у него pull → та же
  NAT-проблема.
- **Uptime Kuma** — один процесс, без агентов. Полезен паттерном «весь live-UI
  через один WS (Socket.IO) + SQLite». **Важный tip: вернулись к одному
  DB-соединению по умолчанию, чтобы избежать lock contention.**
- **Prometheus + node_exporter** — канонический pull. Док самого Prometheus
  занижает важность pull-vs-push. Pull требует, чтобы сервер *достал* таргет —
  для NAT не работает. Их ответы: Pushgateway (только для batch, не рекомендуется)
  или `remote_write`.
- **PushProx** (prometheus-community) — **прямое решение нашей NAT-проблемы**:
  клиент на риге опрашивает прокси исходящим, Prometheus скрейпит прокси, все
  соединения инициированы с рига. Сохраняет pull-модель и формат экспозиции.
  Минус: нет встроенной auth (нужен reverse proxy).
- **Grafana Agent — EOL ноя 2025** → не брать; преемник Alloy. Экосистема
  сошлась на **исходящем `remote_write`** как дефолте.
- **Cockpit** — multi-host транспорт = SSH от hub к хостам (как fallback Beszel),
  не наш NAT-кейс.

## Выводы (5 пунктов)

### 1. Форма здравая?
**Форма (agent+server+web+Prometheus+Grafana) — да, валидирована (Beszel почти
1:1).** Но конкретный **сплит** — «агент отдаёт `/metrics` для pull И отдельно
дозванивается по WS для команд» — необычен и частично саморазрушителен. Ни один
зрелый аналог не использует pull для агента, который *и так* держит исходящий
управляющий канал. Beszel и Netdata гонят **метрики по исходящему соединению
агента**. Контрольная половина (агент дозванивается по WS) — верна и совпадает со
всеми. Метрик-половина (сервер скрейпит агента) — белая ворона.

### 2. Pull vs push в нашем масштабе
Для крошечного флота экосистема **не** за pull. Плюсы pull (service discovery,
`up`-liveness) почти не важны на 3 хостах, заданных руками. Флот-инструменты
(Netdata streaming, Alloy `remote_write`, Beszel WS) **пушат исходящим**.
Решающий фактор — не масштаб, а **достижимость** (п.3). Честный трейд-офф: pull
даёт бесплатный `up` для детекта «риг упал»; при push это надо делать самому —
**но мы получаем это бесплатно из WS, который и так держим** (оборвался WS = риг
офлайн).

### 3. NAT / достижимость — главная находка
**Прямо: если риги за NAT/динамическим IP, а Prometheus где-то ещё (VPS) — pull
не работает.** План в текущем виде имеет дыру достижимости. Решения (в порядке
пригодности для Stoker):

1. **Переиспользовать WS, который агент уже открывает (модель Beszel/Netdata).**
   Агент пушит сэмплы метрик вверх по исходящему WS; сервер их принимает и либо
   (a) хранит лёгкие time-series в SQLite à la Beszel, либо (b) ре-экспозит
   локально для Prometheus, либо (c) делает `remote_write` в локальный
   Prometheus/VictoriaMetrics. **Чистейшее решение — один исходящий канал на
   команды и метрики, NAT не проблема, детект «риг упал» бесплатен из обрыва WS.**
2. **PushProx** — сохранить pull + формат экспозиции, но клиент на риге
   опрашивает прокси исходящим. Минимальные изменения; нужен reverse proxy для auth.
3. **`remote_write`** от мини-коллектора (Alloy) на риге исходящим. Тяжелее.
4. **Pushgateway — НЕ рекомендуется** (только batch; SPOF; не забывает stale; нет `up`).

**Если Prometheus co-located с ригами в одной LAN (или достижим через
VPN/Tailscale)** — обычный pull работает как есть, проблема исчезает. Реальное
решение зависит от: **где живёт сервер относительно ригов?** Одна сеть → pull ок.
Сервер удалённый / риги за NAT → вариант 1 (предпочт.) или 2. **Это в ADR.**

### 4. WS-хаб в малом масштабе
При N≈3 нагрузка тривиальна, но примитивы надёжности сделать правильно: auth на
upgrade-хендшейке (токен/mTLS, проверка `Origin`); heartbeat ping/pong 30–45s
(мёртвый WS = сигнал «риг упал», писать `last_seen` в SQLite); реконнект с
экспоненциальным backoff+jitter на стороне агента; ограниченные send-буферы
(иначе медленный потребитель → OOM); SQLite в WAL с сериализованной записью.

### 5. Embedded Grafana через iframe
Здраво и распространено, но auth — самое тонкое. Грабли: `allow_embedding=true`
(иначе `X-Frame-Options: deny` → пустой iframe); для single-user проще всего
`[auth.anonymous] enabled=true, org_role=Viewer`; **reverse proxy может молча
вернуть `X-Frame-Options: DENY`** — аудитить заголовки; разные домены →
`cookie_samesite=lax` или один origin за общим proxy; встраивать панели через
`/d-solo` / `&kiosk`. Best practice: UI + Grafana за одним reverse proxy на одном
origin, anonymous Viewer, embedding включён.

## Рекомендация для Stoker

1. **Форму сохранить** — Beszel валидирует почти точно.
2. **Решить вопрос метрик-транспорта/NAT отдельным ADR до M2.** Сначала ответить:
   *сервер/Prometheus будут в одной сети с ригами?*
   - **Да (LAN/VPN/Tailscale):** оставить pull-scrape `/metrics` как в плане,
     задокументировать допущение достижимости.
   - **Нет (удалённый сервер, риги за домашним NAT):** pull сломан. Сильно
     предпочесть **push метрик по WS, который агент и так держит** (Beszel/Netdata).
     Вторая опция — **PushProx**.
3. **Подумать, нужен ли Prometheus вообще на M2.** Beszel доказывает: 3-риговый
   флот может хранить даунсэмпленные time-series прямо в SQLite и рисовать графики
   (Recharts) — без Prometheus/Grafana/iframe-auth. Это *материально проще*.
   Prometheus/Grafana всё ещё оправданы целью обучения (индустриальный навык) и
   ad-hoc PromQL — но «Prometheus vs своё SQLite-хранилище» это осознанный ADR,
   не дефолт. Учитывая цель обучения, оставить Prometheus/Grafana разумно; просто
   не дать pull-scrape диктовать сломанную топологию сети.
4. **WS-хаб:** token-auth на хендшейке, ping/pong 30–45s, реконнект с backoff,
   ограниченные буферы, SQLite WAL + сериализованная запись.
5. **Embedded Grafana:** один origin за reverse proxy, anonymous Viewer,
   `allow_embedding=true`, аудит `X-Frame-Options`.

**Итог:** форма правильная и обоснованная; единственное, что починить до
стройки — допущение, что Prometheus сможет скрейпить риги за NAT (обычно не
сможет), и инструмент, на который мы больше всего похожи (Beszel), решил это
push'ем по исходящему соединению агента.

## Источники

- https://github.com/henrygd/beszel · https://beszel.dev/guide/agent-installation
- https://github.com/netdata/netdata · https://learn.netdata.cloud/docs/streaming/understanding-how-streaming-works
- https://github.com/nicolargo/glances · https://glances.readthedocs.io/en/latest/gw/prometheus.html
- https://github.com/louislam/uptime-kuma
- https://prometheus.io/docs/practices/pushing/ · https://prometheus.io/docs/introduction/faq/
- https://github.com/prometheus-community/PushProx
- https://grafana.com/blog/grafana-agent-to-grafana-alloy-opentelemetry-collector-faq/
- https://cockpit-project.org/guide/latest/cockpit-ws.8
- https://grafana.com/blog/how-to-embed-grafana-dashboards-into-web-applications/
