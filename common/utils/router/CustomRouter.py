"""
文件名: CustomRouter.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 12:03
描述:
 自定义 FastAPI 路由器，扩展 APIRouter 功能，提供自动日志记录、统一错误响应、敏感参数过滤等功能。
 支持路由级别的日志开关控制，可以为所有路由自动添加日志装饰器，记录请求和响应信息。

修改历史:
2026/2/6 12:03 - yangchunhui - 初始版本

依赖:
- typing: 类型注解支持（Any, Callable, Optional, List）
- fastapi: APIRouter，FastAPI 路由器基类
- common.utils.logger.CustomLogger: log_api_call，API 调用日志装饰器
"""

from typing import Any, Callable, Optional, List
from fastapi import APIRouter
from common.utils.logger.CustomLogger import log_api_call

# 标准错误响应模板
STANDARD_RESPONSES = {
    400: {
        "description": "请求参数错误",
        "content": {
            "application/json": {
                "example": {
                    "code": 400,
                    "message": "参数验证失败",
                    "data": None
                }
            }
        }
    },
    422: {
        "description": "参数验证错误",
        "content": {
            "application/json": {
                "example": {
                    "code": 400,
                    "message": "参数验证失败",
                    "data": None
                }
            }
        }
    },
    500: {
        "description": "服务器内部错误",
        "content": {
            "application/json": {
                "example": {
                    "code": 500,
                    "message": "服务器内部错误",
                    "data": None
                }
            }
        }
    }
}


class CustomAPIRouter(APIRouter):
    """
    自定义APIRouter，自动添加标准响应和日志装饰器
    """

    def __init__(
        self,
        *args,
        logger_name: Optional[str] = None,
        auto_log: bool = False,
        log_exclude_args: Optional[List[str]] = None,
        **kwargs
    ):
        """
        初始化自定义路由

        Args:
            logger_name: logger名称，如果不指定则不启用自动日志
            auto_log: 是否自动为所有路由添加日志装饰器
            log_exclude_args: 日志中要排除的敏感参数
        """
        super().__init__(*args, **kwargs)

        self.logger_name = logger_name
        self.auto_log = auto_log and (logger_name is not None)
        self.log_exclude_args = log_exclude_args or ['password', 'token', 'secret', 'api_key']

    def api_route(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,  # 自定义参数
        **kwargs
    ) -> Callable:
        """
        重写api_route方法，自动合并标准响应并添加日志装饰器
        """
        # 合并标准响应和自定义响应
        merged_responses = {**STANDARD_RESPONSES}
        if responses:
            merged_responses.update(responses)

        # 获取原始装饰器
        original_decorator = super().api_route(
            path,
            response_model=response_model,
            summary=summary,
            description=description,
            responses=merged_responses,
            **kwargs
        )

        # 判断是否需要自动添加日志
        should_log = False
        if self.logger_name:
            should_log = auto_log if auto_log is not None else self.auto_log

        def decorator(func: Callable) -> Callable:
            # 先应用日志装饰器（如果启用）
            if should_log:
                func = log_api_call(
                    logger_name=self.logger_name,
                    exclude_args=self.log_exclude_args,
                    log_args=True,
                    log_result=True,
                    log_time=True,
                    log_stack_trace=True
                )(func)

            # 再应用路由装饰器
            route_func = original_decorator(func)

            return route_func

        return decorator

    # 重写 get 方法
    def get(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,  # 添加 auto_log 参数
        **kwargs
    ) -> Callable:
        """GET 请求"""
        return self.api_route(
            path,
            methods=["GET"],
            response_model=response_model,
            summary=summary,
            description=description,
            responses=responses,
            auto_log=auto_log,  # 传递 auto_log
            **kwargs
        )

    # 重写 post 方法
    def post(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,  # 添加 auto_log 参数
        **kwargs
    ) -> Callable:
        """POST 请求"""
        return self.api_route(
            path,
            methods=["POST"],
            response_model=response_model,
            summary=summary,
            description=description,
            responses=responses,
            auto_log=auto_log,  # 传递 auto_log
            **kwargs
        )

    # 重写 put 方法
    def put(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,
        **kwargs
    ) -> Callable:
        """PUT 请求"""
        return self.api_route(
            path,
            methods=["PUT"],
            response_model=response_model,
            summary=summary,
            description=description,
            responses=responses,
            auto_log=auto_log,
            **kwargs
        )

    # 重写 delete 方法
    def delete(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,
        **kwargs
    ) -> Callable:
        """DELETE 请求"""
        return self.api_route(
            path,
            methods=["DELETE"],
            response_model=response_model,
            summary=summary,
            description=description,
            responses=responses,
            auto_log=auto_log,
            **kwargs
        )

    # 重写 patch 方法
    def patch(
        self,
        path: str,
        *,
        response_model: Any = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        responses: Optional[dict] = None,
        auto_log: Optional[bool] = None,
        **kwargs
    ) -> Callable:
        """PATCH 请求"""
        return self.api_route(
            path,
            methods=["PATCH"],
            response_model=response_model,
            summary=summary,
            description=description,
            responses=responses,
            auto_log=auto_log,
            **kwargs
        )
