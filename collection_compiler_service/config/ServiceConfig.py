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

    openai_api_key: str = Field(
        ...,
        alias="OPENAI_API_KEY",
        description="OpenAI API 密钥"
    )

    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL",
        description="OpenAI API 地址"
    )

    openai_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL",
        description="OpenAI 模型名称"
    )


@lru_cache()
def get_service_config() -> ServiceConfig:
    return ServiceConfig()  # type: ignore


stock_service_config = get_service_config()