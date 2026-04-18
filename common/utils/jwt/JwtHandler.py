"""
文件名: JwtHandler.py
作者: yangchunhui
创建日期: 2026/2/25
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/25
描述: JWT 核心处理器，提供 Token 签发、解析、刷新、校验等功能。
      设计为通用工具类，可在任意项目中通过传入 JwtConfig 实例化使用。

修改历史:
2026/2/25 - yangchunhui - 初始版本

依赖:
- python-jose: JWT 编解码库（pip install python-jose[cryptography]）
- JwtConfig: JWT 配置
- JwtPayload: Payload 数据模型
- JwtTokenPair: Token 对响应模型

使用示例:
    from common.utils.jwt.JwtConfig import JwtConfig
    from common.utils.jwt.JwtHandler import JwtHandler

    config = JwtConfig(secret_key="your-secret-key")
    jwt_handler = JwtHandler(config)

    # 签发 Token
    token_pair = jwt_handler.create_token_pair(user_id="123", extra={"role": "admin"})

    # 解析 Access Token
    payload = jwt_handler.decode_token(token_pair.access_token)

    # 刷新 Token
    new_pair = jwt_handler.refresh_token(token_pair.refresh_token)
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from jose import jwt, JWTError, ExpiredSignatureError

from common.utils.jwt.JwtConfig import JwtConfig
from common.utils.jwt.JwtPayload import JwtPayload
from common.utils.jwt.JwtTokenPair import JwtTokenPair


class TokenExpiredError(Exception):
    """Token 已过期"""
    pass


class TokenInvalidError(Exception):
    """Token 无效"""
    pass


class JwtHandler:
    """
    JWT 核心处理器

    通用 JWT 工具，支持：
    - Access Token + Refresh Token 双 Token 机制
    - 自定义 extra 字段（role、username 等业务数据）
    - Token 解析与校验
    - Refresh Token 换取新 Token 对
    """

    def __init__(self, config: JwtConfig):
        """
        方法说明: 初始化 JWT 处理器
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            config: JWT 配置实例
        """
        self.config = config

    def _now_timestamp(self) -> int:
        """获取当前 UTC 时间戳（秒）"""
        return int(datetime.now(timezone.utc).timestamp())

    def _create_token(self, user_id: str, token_type: str, expire_seconds: int, extra: Optional[Dict[str, Any]] = None) -> str:
        """
        方法说明: 创建单个 Token
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            user_id: 用户ID
            token_type: Token 类型（access / refresh）
            expire_seconds: 有效期（秒）
            extra: 自定义扩展字段

        Returns:
            JWT 字符串
        """
        now = self._now_timestamp()
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + expire_seconds,
            "token_type": token_type,
            "extra": extra or {},
        }
        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def create_token_pair(self, user_id: str, extra: Optional[Dict[str, Any]] = None) -> JwtTokenPair:
        """
        方法说明: 签发 Access Token + Refresh Token 对
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            user_id: 用户ID
            extra: 自定义扩展字段，如 {"role": "admin", "username": "foo"}

        Returns:
            JwtTokenPair 实例

        Example:
            token_pair = jwt_handler.create_token_pair("123", extra={"role": "admin"})
        """
        access_expire_seconds = self.config.access_token_expire_minutes * 60
        refresh_expire_seconds = self.config.refresh_token_expire_days * 24 * 3600

        access_token = self._create_token(user_id, "access", access_expire_seconds, extra)
        refresh_token = self._create_token(user_id, "refresh", refresh_expire_seconds, extra)

        return JwtTokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_expire_seconds,
        )

    def decode_token(self, token: str, expected_type: str = "access") -> JwtPayload:
        """
        方法说明: 解析并校验 Token，返回 Payload
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            token: JWT 字符串
            expected_type: 期望的 Token 类型，默认 "access"

        Returns:
            JwtPayload 实例

        Raises:
            TokenExpiredError: Token 已过期
            TokenInvalidError: Token 无效（签名错误、格式错误、类型不匹配等）
        """
        try:
            raw = jwt.decode(token, self.config.secret_key, algorithms=[self.config.algorithm])
        except ExpiredSignatureError:
            raise TokenExpiredError("Token 已过期")
        except JWTError:
            raise TokenInvalidError("Token 无效")

        if raw.get("token_type") != expected_type:
            raise TokenInvalidError(f"Token 类型错误，期望 {expected_type}")

        return JwtPayload(**raw)

    def refresh_token(self, refresh_token: str) -> JwtTokenPair:
        """
        方法说明: 使用 Refresh Token 换取新的 Token 对
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            refresh_token: Refresh Token 字符串

        Returns:
            新的 JwtTokenPair 实例

        Raises:
            TokenExpiredError: Refresh Token 已过期
            TokenInvalidError: Refresh Token 无效
        """
        payload = self.decode_token(refresh_token, expected_type="refresh")
        return self.create_token_pair(user_id=payload.sub, extra=payload.extra)

    def get_user_id(self, token: str) -> str:
        """
        方法说明: 从 Access Token 中快捷获取用户ID
        作者: yangchunhui
        创建时间: 2026/2/25
        修改历史:
        2026/2/25 - yangchunhui - 初始版本

        Args:
            token: Access Token 字符串

        Returns:
            用户ID 字符串

        Raises:
            TokenExpiredError: Token 已过期
            TokenInvalidError: Token 无效
        """
        return self.decode_token(token).sub
