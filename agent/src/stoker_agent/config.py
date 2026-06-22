import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Конфиг агента. База — TOML-файл на риге, env (STOKER_) переопределяет.

    learn: pydantic-settings валидирует и типизирует конфиг как Zod-схема. TOML
    читаем stdlib-модулем tomllib (3.11+) и передаём в модель.
    """

    model_config = SettingsConfigDict(env_prefix="STOKER_")

    rig_id: str = "dev-rig"
    metrics_host: str = "0.0.0.0"  # /metrics скрейпит Prometheus (по overlay-сети, ADR 0006)
    metrics_port: int = 9101
    poll_interval_s: float = 5.0
    server_url: str = "ws://localhost:8000/ws/agent"  # пока не используется (M2d)
    fake_gpu_count: int = 2  # для заглушки M1; в M2a заменится реальным перечислением GPU


def load_settings(path: Path) -> AgentSettings:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return AgentSettings(**data)
