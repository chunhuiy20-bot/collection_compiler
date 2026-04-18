"""
文件名: JwtConfig.py
作者: yangchunhui
创建日期: 2026/2/25
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/25
描述: JWT 配置类，定义签名密钥、算法、过期时间等参数

修改历史:
2026/2/25 - yangchunhui - 初始版本

使用示例:
config = JwtConfig(secret_key="your-secret", access_token_expire_minutes=30)
"""

from dataclasses import dataclass, field


@dataclass
class JwtConfig:
    """JWT 配置"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
