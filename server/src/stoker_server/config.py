from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфиг сервера. Значения читаются из env с префиксом STOKER_.

    learn: BaseSettings из pydantic-settings — как провалидированный, типизированный
    process.env: поля с дефолтами, типы проверяются, env переопределяет.
    """

    model_config = SettingsConfigDict(env_prefix="STOKER_")

    service_name: str = "stoker-server"
    host: str = "127.0.0.1"
    port: int = 8000
