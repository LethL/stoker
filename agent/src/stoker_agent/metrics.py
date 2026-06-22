from prometheus_client import Gauge

# learn: Gauge — метрика, которая может расти и падать (температура, hashrate).
# Лейблы (rig, gpu) позволяют различать риги и карты в одном scrape — корреляция
# GPU↔майнер в Grafana. Имена в стиле dcgm-exporter с unit-суффиксами (ADR 0002).
GPU_TEMPERATURE = Gauge("stoker_gpu_temperature_celsius", "Температура GPU, °C", ["rig", "gpu"])
GPU_FAN = Gauge("stoker_gpu_fan_percent", "Скорость вентилятора GPU, %", ["rig", "gpu"])
GPU_POWER = Gauge("stoker_gpu_power_watts", "Потребление GPU, Вт", ["rig", "gpu"])
MINER_HASHRATE = Gauge("stoker_miner_hashrate_hps", "Хэшрейт майнера, H/s", ["rig", "gpu"])


def update_fake_metrics(rig_id: str, gpu_count: int, tick: int) -> None:
    """Выставляет детерминированно осциллирующие фейковые значения (заглушка M1).

    В M2a заменится реальным сбором через GpuCollector (pynvml) и MinerDriver.
    """
    for gpu in range(gpu_count):
        gpu_label = str(gpu)
        phase = (tick + gpu) % 10
        GPU_TEMPERATURE.labels(rig=rig_id, gpu=gpu_label).set(55 + phase)
        GPU_FAN.labels(rig=rig_id, gpu=gpu_label).set(40 + phase * 2)
        GPU_POWER.labels(rig=rig_id, gpu=gpu_label).set(120 + phase)
        MINER_HASHRATE.labels(rig=rig_id, gpu=gpu_label).set(60_000_000 + phase * 100_000)
