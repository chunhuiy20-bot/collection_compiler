"""
文件名: CommonResult.py
作者: yangchunhui
创建日期: 2026/2/5
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/5 18:12
描述: 统一的 API 响应结果封装类。提供标准化的接口返回格式，包括通用返回结果（Result）和分页返回结果（PageResult），支持泛型、状态码管理、成功/失败响应快捷方法等功能。

修改历史:
2026/2/5 18:12 - yangchunhui - 初始版本

依赖:
- typing: 提供泛型支持（Generic, Optional, TypeVar）
- pydantic: 数据验证和序列化框架（BaseModel, Field, ConfigDict）
- datetime: 用于生成时间戳

使用示例:
"""

from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# 定义泛型类型
T = TypeVar('T')


class ResultCode:
    """业务状态码常量"""
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class Result(BaseModel, Generic[T]):
    """通用的统一返回结果"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="返回消息")
    data: Optional[T] = Field(default=None, description="返回数据")
    timestamp: Optional[int] = Field(default=None, description="时间戳（毫秒），可选")

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "success",
                include_timestamp: bool = False) -> "Result[T]":
        """成功响应

        Args:
            data: 返回的数据
            message: 成功消息
            include_timestamp: 是否包含时间戳，默认 False

        Returns:
            Result 对象

        Example:
            return Result.success(data=user_info)
            return Result.success(message="操作成功")
            return Result.success(data=user_info, include_timestamp=True)
        """
        timestamp = int(datetime.now().timestamp() * 1000) if include_timestamp else None
        return cls(code=ResultCode.SUCCESS, message=message, data=data, timestamp=timestamp)

    @classmethod
    def fail(cls, message: str = "操作失败", code: int = ResultCode.INTERNAL_ERROR,
             data: Optional[T] = None, include_timestamp: bool = False) -> "Result[T]":
        """失败响应

        Args:
            message: 错误消息
            code: 错误码
            data: 附加数据
            include_timestamp: 是否包含时间戳，默认 False

        Returns:
            Result 对象

        Example:
            return Result.fail(message="用户不存在", code=ResultCode.NOT_FOUND)
            return Result.fail(message="服务异常", include_timestamp=True)
        """
        timestamp = int(datetime.now().timestamp() * 1000) if include_timestamp else None
        return cls(code=code, message=message, data=data, timestamp=timestamp)

    @classmethod
    def unauthorized(cls, message: str = "未授权") -> "Result[T]":
        """未授权响应"""
        return cls(code=ResultCode.UNAUTHORIZED, message=message, data=None)

    @classmethod
    def forbidden(cls, message: str = "无权限") -> "Result[T]":
        """无权限响应"""
        return cls(code=ResultCode.FORBIDDEN, message=message, data=None)

    @classmethod
    def not_found(cls, message: str = "资源不存在") -> "Result[T]":
        """资源不存在响应"""
        return cls(code=ResultCode.NOT_FOUND, message=message, data=None)

    @classmethod
    def bad_request(cls, message: str = "请求参数错误") -> "Result[T]":
        """请求参数错误响应"""
        return cls(code=ResultCode.BAD_REQUEST, message=message, data=None)


class PageResult(BaseModel, Generic[T]):
    """通用的分页返回结果"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码，从1开始")
    page_size: int = Field(description="每页大小")
    items: list[T] = Field(default_factory=list, description="数据列表")

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    @property
    def total_pages(self) -> int:
        """总页数"""
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1
