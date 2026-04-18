"""
文件名: GlobalExceptionHandlers.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 13:36
描述: 全局异常处理器模块，提供 FastAPI 应用的统一异常处理机制。包括请求参数验证错误处理、
HTTP 异常处理、通用异常处理等功能。支持友好的中文错误提示、完整的日志记录、统一的响应格式。

修改历史:
2026/2/6 13:36 - yangchunhui - 初始版本

依赖:
- fastapi: HTTPException, Request，FastAPI 核心组件
- fastapi.exceptions: RequestValidationError，请求验证异常
- fastapi.responses: JSONResponse，JSON 响应对象
- common.utils.logger.CustomLogger: CustomLogger，自定义日志管理器

使用示例:
    from fastapi import FastAPI
    from common.utils.exception.GlobalExceptionHandlers import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
"""
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from common.utils.logger.CustomLogger import get_logger

# 获取日志实例
logger = get_logger()

# 错误类型映射模板（模块级常量）
ERROR_TYPE_TEMPLATES = {
    'string_too_long': '参数 {field} 长度超出限制',
    'string_too_short': '参数 {field} 长度不足',
    'value_error': '参数 {field} 格式不正确',
    'type_error': '参数 {field} 类型错误',
    'missing': '缺少必需参数 {field}',
    'string_pattern_mismatch': '参数 {field} 格式不符合要求'
}


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求参数验证错误(422)
    """
    errors = exc.errors()
    error_messages = []

    # 处理所有验证错误
    for error_detail in errors:
        field = error_detail.get('loc', ['unknown'])[-1]  # 获取字段名
        msg = error_detail.get('msg', '参数验证失败')
        error_type = error_detail.get('type', '')

        # 使用模板生成友好的错误消息
        template = ERROR_TYPE_TEMPLATES.get(error_type)
        if template:
            error_msg = template.format(field=field)
        else:
            error_msg = f'参数 {field} 验证失败: {msg}'

        error_messages.append(error_msg)

    # 合并所有错误消息
    final_message = '; '.join(error_messages) if error_messages else '参数验证失败'

    # 记录日志
    logger.warning(
        f"参数验证失败 - 路径: {request.url.path}, 方法: {request.method}, "
        f"客户端: {request.client.host if request.client else 'unknown'}, "
        f"错误: {final_message}"
    )

    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": final_message,
            "data": None
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    # 记录日志
    logger.warning(
        f"HTTP异常 - 路径: {request.url.path}, 方法: {request.method}, "
        f"客户端: {request.client.host if request.client else 'unknown'}, "
        f"状态码: {exc.status_code}, 详情: {exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    # 记录详细的错误日志
    logger.error(
        f"未处理的异常 - 路径: {request.url.path}, 方法: {request.method}, "
        f"客户端: {request.client.host if request.client else 'unknown'}, "
        f"异常类型: {type(exc).__name__}, 异常信息: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )


def register_exception_handlers(app):
    """注册所有异常处理器"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
