"""
文件名: JwtTokenPair.py
作者: yangchunhui
创建日期: 2026/2/25
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/25
描述: JWT Token 对模型，封装 Access Token 和 Refresh Token 的响应结构

修改历史:
2026/2/25 - yangchunhui - 初始版本
"""

from pydantic import BaseModel, Field


class JwtTokenPair(BaseModel):
    """JWT Token 对"""
    access_token: str = Field(..., description="访问 Token（短期）")
    refresh_token: str = Field(..., description="刷新 Token（长期）")
    token_type: str = Field(default="Bearer", description="Token 类型")
    expires_in: int = Field(..., description="Access Token 有效期（秒）")
