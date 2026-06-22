from pathlib import Path

from stoker_agent.config import load_settings


def test_load_settings_from_toml(tmp_path: Path) -> None:
    cfg = tmp_path / "agent.toml"
    cfg.write_text('rig_id = "rig-42"\nmetrics_port = 9999\nfake_gpu_count = 3\n')

    settings = load_settings(cfg)

    assert settings.rig_id == "rig-42"
    assert settings.metrics_port == 9999
    assert settings.fake_gpu_count == 3
    assert settings.poll_interval_s == 5.0  # не задано в файле → дефолт
