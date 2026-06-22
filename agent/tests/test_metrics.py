from prometheus_client import REGISTRY

from stoker_agent.metrics import update_fake_metrics


def test_update_fake_metrics_sets_values() -> None:
    update_fake_metrics("rig-x", gpu_count=2, tick=0)

    # gpu0, tick0 → phase 0 → 55 + 0
    temp = REGISTRY.get_sample_value("stoker_gpu_temperature_celsius", {"rig": "rig-x", "gpu": "0"})
    assert temp == 55.0

    # gpu1, tick0 → phase 1 → 60_000_000 + 100_000
    hashrate = REGISTRY.get_sample_value("stoker_miner_hashrate_hps", {"rig": "rig-x", "gpu": "1"})
    assert hashrate == 60_100_000.0
