from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from common.utils.env.EnvLoader import load_service_env

load_service_env(caller_file=__file__)


class ServiceConfig(BaseSettings):
    mysql_config_async: str = Field(
        ...,
        alias="MYSQL_CONFIG_ASYNC",
        description="MySQL 异步连接字符串"
    )


@lru_cache()
def get_service_config() -> ServiceConfig:
    return ServiceConfig()  # type: ignore


stock_service_config = get_service_config()