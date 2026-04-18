"""
文件名: PasswordHasher.py
作者: yangchunhui
创建日期: 2026/2/10
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/10
描述: 密码哈希加密工具类，提供安全的密码哈希和验证功能

修改历史:
2026/2/10 - yangchunhui - 初始版本

依赖:
- passlib: 密码哈希库
- argon2-cffi: Argon2 算法实现

使用示例:
from common.utils.security.PasswordHasher import password_hasher
p1 = password_hasher.hash_password("123456")
p2 = password_hasher.hash_password("123456")
print(p1)
print(p2)
print(password_hasher.verify_password("123456", p1))
print(password_hasher.verify_password("123456", p2))
"""
from passlib.context import CryptContext
from typing import Optional


class PasswordHasher:
    """
    密码哈希工具类
    使用 Argon2 算法进行密码哈希，提供高安全性的密码存储方案
    """

    def __init__(self, schemes: Optional[list] = None):
        """
        方法说明: 初始化密码哈希器
        作者: yangchunhui
        创建时间: 2026/2/10
        修改历史: 2026/2/10 - yangchunhui - 初始版本

        Args:
            schemes: 哈希算法列表，默认使用 argon2
        """
        if schemes is None:
            schemes = ["argon2", "bcrypt"]

        self.pwd_context = CryptContext(
            schemes=schemes,
            deprecated="auto",
            argon2__memory_cost=65536,  # 64 MB
            argon2__time_cost=3,  # 迭代次数
            argon2__parallelism=4  # 并行度
        )

    def hash_password(self, password: str) -> str:
        """
        方法说明: 对密码进行哈希加密
        作者: yangchunhui
        创建时间: 2026/2/10
        修改历史: 2026/2/10 - yangchunhui - 初始版本

        Args:
            password: 明文密码

        Returns:
            str: 哈希后的密码字符串

        Raises:
            ValueError: 当密码为空时抛出
        """
        if not password:
            raise ValueError("密码不能为空")

        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        方法说明: 验证密码是否正确
        作者: yangchunhui
        创建时间: 2026/2/10
        修改历史: 2026/2/10 - yangchunhui - 初始版本

        Args:
            plain_password: 明文密码
            hashed_password: 哈希后的密码

        Returns:
            bool: 密码是否匹配
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except (ValueError, TypeError):
            return False

    def needs_update(self, hashed_password: str) -> bool:
        """
        方法说明: 检查哈希密码是否需要更新（算法升级或参数调整）
        作者: yangchunhui
        创建时间: 2026/2/10
        修改历史: 2026/2/10 - yangchunhui - 初始版本

        Args:
            hashed_password: 哈希后的密码

        Returns:
            bool: 是否需要重新哈希
        """
        return self.pwd_context.needs_update(hashed_password)


# 全局单例实例
password_hasher = PasswordHasher()
