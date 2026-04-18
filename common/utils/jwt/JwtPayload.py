"""
文件名: JwtPayload.py
作者: yangchunhui
创建日期: 2026/2/25
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/25
描述: JWT Payload 数据模型，定义 Token 中携带的标准字段和自定义扩展字段

修改历史:
2026/2/25 - yangchunhui - 初始版本

字段说明:
    - sub: Subject，通常为用户ID（字符串）
    - exp: 过期时间（Unix 时间戳）
    - iat: 签发时间（Unix 时间戳）
    - token_type: Token 类型，access 或 refresh
    - extra: 自定义扩展字段，可存放 role、username 等业务数据
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JwtPayload(BaseModel):
    """JWT Payload 模型"""
    sub: str = Field(..., description="用户ID")
    exp: int = Field(..., description="过期时间（Unix 时间戳）")
    iat: int = Field(..., description="签发时间（Unix 时间戳）")
    token_type: str = Field(default="access", description="Token 类型: access / refresh")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="自定义扩展字段")
