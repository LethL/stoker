# Research 0003: API майнера WildRig Multi (~v0.48.4)

**Дата:** 2026-06-17
**Этап:** Pre-M0 (pre-flight, добивающая разведка)
**Контекст:** Первый реальный `MinerDriver` в Stoker — под wildrig-multi v0.48.4
(Nvidia-риг). Нужно знать формат телеметрии и управления.
**Метод:** веб-поиск; авторитетный источник — парсер HiveOS `h-stats.sh`
(показывает, что API реально отдаёт), README WildRig, модель XMRig API.

> Степень достоверности помечена: ✅ подтверждено (HiveOS реально читает),
> ⚠️ выведено из модели XMRig и не верифицировано для WildRig.

## Summary

WildRig Multi **НЕ использует** cgminer/sgminer TCP-сокет API (порт 4028,
newline-JSON). Несмотря на происхождение ядер от sgminer/avermore, его
**мониторинг-API — это HTTP JSON в стиле XMRig**: обычный `GET http://host:port/`
возвращает один JSON-документ. Подтверждается тем, что HiveOS опрашивает его
через `curl`, а не `nc`. Дефолтный порт у HiveOS — **60050** (порт произвольный,
задаётся `--api-port`). Форма JSON повторяет XMRig `/api/1/summary`.

**Это перечёркивает допущение из research 0002**, где (под T-Rex) предполагался
другой формат. Для WildRig — другой транспорт и другая схема.

## API: транспорт и порт

- **Транспорт: HTTP/1.1, JSON по GET.** ✅ HiveOS: `curl ... http://127.0.0.1:${PORT}`.
- **НЕ cgminer TCP API.** Сокета на 4028 нет.
- **Дефолтного порта у самого майнера нет** — без `--api-port N` API не поднимается.
  HiveOS хардкодит `--api-port 60050`.
- **Документированные флаги (README):** `--api-port N`, `--api-worker-id ID`.
- **Bind-адрес / read-only режим — НЕ документированы.** Есть ли `--api-bind` и
  по умолчанию слушает ли `0.0.0.0` или `127.0.0.1` — неизвестно. Проверить
  `wildrig --help` на реальном риге и биндить явно.

## Маппинг полей телеметрии

✅ — HiveOS реально читает; ⚠️ — выведено из XMRig, не верифицировано.

| Метрика Stoker | JSON path | Статус |
|---|---|---|
| Версия майнера | `.version` | ✅ |
| Алгоритм | `.algo` | ✅ |
| Uptime (сек) | `.uptime` | ✅ |
| Общий хэшрейт | `.hashrate.total[0]` (массив средних, `[0]`=текущее) | ✅ |
| Хэшрейт по GPU | `.hashrate.threads[][0]` (массив массивов) | ✅ |
| Принятые шары | `.results.shares_good` | ✅ |
| Всего отправлено | `.results.shares_total` (rejected ≈ total − good) | ✅ |
| Температура по GPU | `.temp` (массив, порядок = перечисление майнера) | ✅ |
| Fan по GPU | `.fan` (массив) | ✅ |
| Кол-во GPU | `len(.temp)` / `len(.hashrate.threads)` | ✅ derived |
| Активный пул | `.connection.pool` (URL) | ⚠️ HiveOS не читает |
| Power по GPU | в API HiveOS не читается | ⚠️ скорее всего отсутствует |
| Clock по GPU | не читается HiveOS | ⚠️ неизвестно/вероятно нет |
| PCI bus id | **в JSON нет** | ✅ отсутствует (HiveOS берёт из лога) |

**Грабли:**
- `hashrate.total` / `threads` — **массивы оконных средних**, брать `[0]`. Единицы
  — сырые H/s (HiveOS делит на 1000 для kH/s).
- **Power и clocks в API ненадёжны/отсутствуют** → брать из **pynvml** (Nvidia).
  Это ровно ложится на архитектуру Stoker: GPU-телеметрия — отдельный слой
  `GpuCollector`, а не майнер.
- **Нет привязки к bus-id**: массивы `temp`/`fan`/`threads` упорядочены по
  перечислению майнера, может не совпадать с PCI-порядком. Согласование
  WildRig-индексов с идентичностью GPU в Stoker — через лог майнера (как HiveOS)
  или принять index-order.

Примерная форма ответа (реконструкция, НЕ дамп v0.48.4):
```json
{
  "version": "0.48.4",
  "algo": "ghostrider",
  "uptime": 3600,
  "hashrate": { "total": [12345.6, 12300.0, 12280.0],
                "threads": [[6170.0], [6175.6]] },
  "results": { "shares_good": 412, "shares_total": 415 },
  "temp": [61, 63],
  "fan": [55, 58],
  "connection": { "pool": "stratum+tcp://pool.example:3333", "uptime": 3600 }
}
```

## Команды управления

- **Подтверждено (community): API поддерживает `pause` и `resume`** + read-команды
  `hashrate`/`statistics`. Точный HTTP-метод/путь/payload **не документирован** —
  проверять на живом бинаре.
- **Reload config / shutdown через API — НЕ подтверждены.** Документации нет.
- **cgminer-команды (`quit`, `restart`, `gpuenable`...) не применимы.**
- **Read-only режим API не документирован** — считать API read-write без
  разделения привилегий.

→ Для Stoker: API только для телеметрии и (best-effort) pause/resume.
**Start/stop/restart владеет Stoker через процесс/systemd** — совпадает с дизайном.

## Безопасность

- **Аутентификации нет** (в README флага токена нет; XMRig-style Bearer для
  WildRig не подтверждён). Считать API **без auth**.
- Wallet/pass в телеметрийном GET, похоже, не отдаются; `connection.pool` (только
  URL) может присутствовать. Всё равно считать endpoint чувствительным.
- **Bind по умолчанию неизвестен** → биндить на `127.0.0.1` явно либо
  файрволить порт. Весь контроль — через аутентифицированный канал agent↔server.
  Порт наружу не выставлять.

## Версии / quirks

- Схема API не документирована официально ни в одной версии — published API
  changelog отсутствует.
- Известный quirk HiveOS: **неверные temp/fan** в части связок WildRig+HiveOS —
  issue #111. Проверить порядок/корректность массивов на реальном риге.
- Ветка v0.48.x — **Nvidia-focused «Pearl»** релизы (GTX 1000 – RTX 5000).
  Упоминаний об изменениях API в 0.48.x нет → API предположительно стабилен, но
  не верифицировано для 0.48.4.
- **Жёсткая рекомендация:** снять реальный `curl http://127.0.0.1:<port>/` с
  установленного 0.48.4 и запинить парсер на него + добавить как test fixture.

## Конфиг и запуск

- Конфигурация — через CLI-флаги и/или JSON-конфиг (`--config <file>`). HiveOS
  использует CLI-форму с подстановкой `%EWAL%`, `%WORKER_NAME%` и т.д.
- Ключевые флаги: `-a/--algo`, `-o/--url` (`stratum+tcp://host:port`),
  `-u/--user <wallet[.worker]>`, `-p/--pass`, `--api-port N`, `--api-worker-id`,
  `--opencl-devices=`, `--gpu-temp-limit=`, `--log-file=`.
- Схема config.json официально не опубликована (по сути CLI-опции как JSON-ключи).
  → Для Stoker чище **генерировать командную строку** из per-rig TOML (как в
  CLAUDE.md), а не поддерживать JSON-конфиг с негарантированной схемой.

## Рекомендация для WildRigDriver

1. **Телеметрия по HTTP, не сокет.** `httpx.AsyncClient` GET на
   `http://127.0.0.1:<api_port>/`. Cgminer-сокет НЕ делать. Порт фиксированный
   (напр. 60050) через `--api-port`.
2. **Defensive parsing.** Пинить на подтверждённые поля; `connection.pool`/power/
   clocks — optional/absent. `rejected = shares_total − shares_good`,
   `gpu_count = len(temp)`. Pydantic с optional non-core полями → дрейф схемы
   не роняет коллектор.
3. **Power/clocks — из pynvml, не из WildRig** (в API ненадёжно). Уже ложится
   на `GpuCollector`.
4. **Lifecycle — не через API.** Start/stop/restart через systemd/процесс.
   Pause/resume — опционально, проверив endpoint на реальном бинаре.
5. **Security: localhost + zero-trust.** API на loopback, наружу не выставлять,
   весь доступ через аутентифицированный канал.
6. **Перед релизом:** снять живой JSON-дамп с реального v0.48.4 как fixture;
   проверить порядок `temp`/`fan` против физических GPU (quirk #111).

## Источники

- README WildRig: https://github.com/andru-kun/wildrig-multi/blob/master/README.md
- HiveOS парсер (авторитетно по реальному выводу API):
  https://github.com/minershive/hiveos-linux/blob/master/hive/miners/wildrig-multi/h-stats.sh
- HiveOS launcher (`--api-port 60050`):
  https://github.com/andru-kun/wildrig/blob/master/hiveos/h-config.sh
- Quirk temp/fan: https://github.com/andru-kun/wildrig-multi/issues/111
- Релизы 0.48.x: https://github.com/andru-kun/wildrig-multi/releases
- Модель XMRig API (база для инференса):
  https://github.com/xmrig/xmrig/wiki/API
- bitcointalk анонс: https://bitcointalk.org/index.php?topic=5023676.0
