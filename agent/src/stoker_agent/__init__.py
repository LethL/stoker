"""Stoker agent — демон на риге: сбор метрик, /metrics, команды от сервера."""

__version__ = "0.1.0"


def main() -> None:
    # learn: настоящая точка входа появится в M1.3 (python -m stoker_agent).
    # Пока заглушка, чтобы console-script из pyproject был валиден.
    print(f"stoker-agent {__version__}")
