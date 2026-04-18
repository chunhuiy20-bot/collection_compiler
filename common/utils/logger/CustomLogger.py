"""
文件名: CustomLogger.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 11:44
描述: 自定义日志管理器，提供按日期轮转的日志文件管理、单例模式的日志管理器、分离 INFO 和 ERROR 日志、
API 调用日志装饰器等功能。支持多种日志格式、自动清理过期日志、敏感信息过滤、同步和异步函数装饰。

修改历史:
2026/2/6 11:44 - yangchunhui - 初始版本

依赖:
- logging: Python 标准日志库，提供日志记录功能
- logging.handlers: TimedRotatingFileHandler，按时间轮转的日志处理器
- re: 正则表达式，用于敏感信息过滤
- time: time，用于记录函数执行耗时
- json: JSON 序列化，用于格式化日志输出
- functools: wraps，用于保持被装饰函数的元数据
- typing: 类型注解支持（Any, Optional, Callable, Dict）
- datetime: datetime，用于日期时间处理和日志文件命名
- inspect: iscoroutinefunction，用于判断函数是否为异步函数
- asyncio: 异步支持，用于异步函数装饰
- pathlib: Path，用于跨平台的文件路径操作
- threading: Lock，用于单例模式的线程安全
- traceback: format_exc，用于获取完整的异常堆栈信息
"""

import logging
import logging.handlers
import re
import time
import json
from functools import wraps
from typing import Any, Optional, Callable, Dict
from datetime import datetime
import inspect
import asyncio
from pathlib import Path
import threading


class DailyRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """自定义的按日期轮转处理器 - 文件名包含日期"""

    def __init__(self, base_filename: str, log_dir: str, **kwargs):
        """
        Args:
            base_filename: 基础文件名（如 "app"）
            log_dir: 日志目录
        """
        self.base_filename = base_filename
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 生成今天的文件名
        today = datetime.now().strftime('%Y%m%d')
        filename = self.log_dir / f"{base_filename}_{today}.log"

        super().__init__(
            filename=str(filename),
            when='midnight',
            interval=1,
            backupCount=kwargs.get('backupCount', 30),
            encoding='utf-8'
        )

        # 禁用默认的后缀添加
        self.suffix = ""
        # self.extMatch = None
        self.extMatch = re.compile(r"")  # 或使用空模式 re.compile(r"")

    def doRollover(self):
        """轮转时生成新的文件名"""
        # 关闭当前文件
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]

        # 生成新的文件名
        today = datetime.now().strftime('%Y%m%d')
        new_filename = self.log_dir / f"{self.base_filename}_{today}.log"
        self.baseFilename = str(new_filename)

        # 打开新文件
        self.stream = self._open()

        # 清理旧文件
        self.cleanup_old_files()

    def cleanup_old_files(self):
        """清理超过保留天数的日志文件"""
        if self.backupCount > 0:
            log_files = sorted(
                self.log_dir.glob(f"{self.base_filename}_*.log"),
                reverse=True
            )
            # 保留最新的 backupCount 个文件
            for old_file in log_files[self.backupCount:]:
                try:
                    old_file.unlink()
                    # 使用 logging 记录而不是 print
                    logging.info(f"已删除旧日志: {old_file}")
                except Exception as e:
                    logging.warning(f"删除旧日志失败: {old_file}, 错误: {e}")


class LoggerManager:
    """日志管理器 - 单例模式"""
    _instance = None
    _lock = threading.Lock()
    _loggers: Dict[str, logging.Logger] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_logger(
            cls,
            logger_name: str = "app",
            level: int = logging.INFO,
            log_to_file: bool = True,
            log_to_console: bool = True,
            log_dir: str = "logs",
            backup_count: int = 30,
            format_style: str = "detailed",
            separate_error_file: bool = True
    ) -> logging.Logger:
        """
        获取或创建logger

        文件结构：
            logs/
            ├── {logger_name}_info/
            │   ├── {logger_name}_20251119.log
            │   └── {logger_name}_20251118.log
            └── {logger_name}_error/
                ├── {logger_name}_20251119.log
                └── {logger_name}_20251118.log
        """
        if logger_name in cls._loggers:
            return cls._loggers[logger_name]

        with cls._lock:
            if logger_name in cls._loggers:
                return cls._loggers[logger_name]

            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            logger.propagate = False
            logger.handlers.clear()

            # 日志格式
            format_templates = {
                "simple": '%(asctime)s [%(levelname)s] %(message)s',
                "detailed": (
                    '%(asctime)s [%(levelname)-8s] '
                    '[%(filename)s:%(lineno)d] '
                    '%(name)s - %(message)s'
                ),
                "full": (
                    '%(asctime)s [%(levelname)-8s] '
                    '[%(pathname)s:%(lineno)d:%(funcName)s] '
                    '%(name)s - %(message)s'
                ),
                "colored": (
                    '%(asctime)s [%(levelname)-8s] '
                    '\033[36m[%(filename)s:%(lineno)d]\033[0m '
                    '%(message)s'
                )
            }

            format_str = format_templates.get(format_style, format_templates["detailed"])
            formatter = logging.Formatter(format_str, datefmt='%Y-%m-%d %H:%M:%S')

            # 控制台处理器
            if log_to_console:
                console_handler = logging.StreamHandler()
                console_format = format_templates.get("colored", format_str)
                console_formatter = logging.Formatter(
                    console_format,
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(console_formatter)
                console_handler.setLevel(level)
                logger.addHandler(console_handler)

            # 文件处理器
            if log_to_file:
                base_log_path = Path(log_dir)
                base_log_path.mkdir(parents=True, exist_ok=True)

                if separate_error_file:
                    # ✅ INFO 日志目录
                    info_log_dir = base_log_path / f"{logger_name}_info"
                    info_log_dir.mkdir(parents=True, exist_ok=True)

                    # ✅ ERROR 日志目录
                    error_log_dir = base_log_path / f"{logger_name}_error"
                    error_log_dir.mkdir(parents=True, exist_ok=True)

                    # INFO 级别日志处理器
                    all_handler = DailyRotatingFileHandler(
                        base_filename=logger_name,
                        log_dir=str(info_log_dir),
                        backupCount=backup_count
                    )
                    all_handler.setFormatter(formatter)
                    all_handler.setLevel(logging.INFO)
                    logger.addHandler(all_handler)

                    # ERROR 级别日志处理器
                    error_handler = DailyRotatingFileHandler(
                        base_filename=logger_name,
                        log_dir=str(error_log_dir),
                        backupCount=backup_count * 2  # 错误日志保留更久
                    )
                    error_handler.setFormatter(formatter)
                    error_handler.setLevel(logging.ERROR)
                    logger.addHandler(error_handler)

                    # 记录日志路径到 logger
                    today = datetime.now().strftime('%Y%m%d')
                    logger.info(f"INFO日志路径: {info_log_dir / f'{logger_name}_{today}.log'}")
                    logger.info(f"ERROR日志路径: {error_log_dir / f'{logger_name}_{today}.log'}")

                else:
                    # 不分离错误日志
                    log_dir_path = base_log_path / logger_name
                    log_dir_path.mkdir(parents=True, exist_ok=True)

                    file_handler = DailyRotatingFileHandler(
                        base_filename=logger_name,
                        log_dir=str(log_dir_path),
                        backupCount=backup_count
                    )
                    file_handler.setFormatter(formatter)
                    file_handler.setLevel(level)
                    logger.addHandler(file_handler)

                    today = datetime.now().strftime('%Y%m%d')
                    logger.info(f"日志文件路径: {log_dir_path / f'{logger_name}_{today}.log'}")

            cls._loggers[logger_name] = logger
            return logger


def serialize_object(obj: Any, max_length: int = 1000) -> str:
    """序列化对象为JSON字符串"""
    try:
        if hasattr(obj, 'dict'):
            result = json.dumps(obj.dict(), ensure_ascii=False, indent=2, default=str)
        elif hasattr(obj, '__dict__'):
            result = json.dumps(obj.__dict__, ensure_ascii=False, indent=2, default=str)
        else:
            result = json.dumps(obj, ensure_ascii=False, indent=2, default=str)

        if len(result) > max_length:
            result = result[:max_length] + "...[已截断]"

        return result
    except Exception as e:
        return f"<序列化失败: {str(e)}>"


def log_api_call(
        logger_name: str = "app",
        log_args: bool = True,
        log_result: bool = True,
        log_time: bool = True,
        exclude_args: Optional[list] = None,
        max_content_length: int = 1000,
        log_level: int = logging.INFO,
        log_stack_trace: bool = True
):
    """API调用日志装饰器"""
    logger = LoggerManager.get_logger(logger_name)
    exclude_args = exclude_args or ['password', 'token', 'secret', 'api_key']

    def _log_function_args(func: Callable, args: tuple, kwargs: dict) -> Optional[str]:
        """记录函数入参的公共逻辑"""
        if not log_args:
            return None

        try:
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            def mask_sensitive_data(obj: Any, depth: int = 0) -> Any:
                """递归屏蔽敏感数据"""
                if depth > 5:  # 防止无限递归
                    return obj

                # 处理 Pydantic 模型
                if hasattr(obj, 'model_dump'):  # Pydantic v2
                    data = obj.model_dump()
                    return {
                        k: '***' if k in exclude_args else mask_sensitive_data(v, depth + 1)
                        for k, v in data.items()
                    }
                elif hasattr(obj, 'dict'):  # Pydantic v1
                    data = obj.dict()
                    return {
                        k: '***' if k in exclude_args else mask_sensitive_data(v, depth + 1)
                        for k, v in data.items()
                    }
                # 处理字典
                elif isinstance(obj, dict):
                    return {
                        k: '***' if k in exclude_args else mask_sensitive_data(v, depth + 1)
                        for k, v in obj.items()
                    }
                # 处理列表
                elif isinstance(obj, (list, tuple)):
                    return [mask_sensitive_data(item, depth + 1) for item in obj]
                # 其他类型直接返回
                else:
                    return obj

            filtered_args = {
                k: '***' if k in exclude_args else mask_sensitive_data(v)
                for k, v in bound_args.arguments.items()
            }

            args_str = serialize_object(filtered_args, max_content_length)
            func_name = f"{func.__module__}.{func.__qualname__}"  # type: ignore[attr-defined]
            logger.log(log_level, f"[调用] {func_name}")
            logger.log(log_level, f"[入参] {args_str}")
            return args_str
        except Exception as e:
            logger.warning(f"记录入参失败: {e}")
            return None

    def _log_function_result(result: Any, execution_time: float):
        """记录函数返回值的公共逻辑"""
        if log_time:
            logger.log(log_level, f"[耗时] {execution_time:.3f}秒")

        if log_result:
            try:
                result_str = serialize_object(result, max_content_length)
                logger.log(log_level, f"[返回] {result_str}")
            except Exception as e:
                logger.warning(f"记录返回值失败: {e}")

    def _log_function_error(func: Callable, e: Exception, args_str: Optional[str], execution_time: float):
        """记录函数错误的公共逻辑"""
        func_name = f"{func.__module__}.{func.__qualname__}"  # type: ignore[attr-defined]

        logger.error(f"{'=' * 60}")
        logger.error(f"[失败] {func_name}")

        # 重新记录入参到 ERROR 级别
        if args_str:
            logger.error(f"[入参] {args_str}")

        logger.error(f"[异常类型] {type(e).__name__}")
        logger.error(f"[异常信息] {str(e)}")
        logger.error(f"[执行耗时] {execution_time:.3f}秒")

        if log_stack_trace:
            logger.error(f"[错误堆栈]")
            logger.exception("完整堆栈跟踪:")

        logger.error(f"{'=' * 60}")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"  # type: ignore[attr-defined]
            start_time = time.time()

            # 记录入参
            args_str = _log_function_args(func, args, kwargs)

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 记录返回值
                _log_function_result(result, execution_time)

                logger.log(log_level, f"[成功] {func_name}")
                return result

            except Exception as e:
                execution_time = time.time() - start_time
                _log_function_error(func, e, args_str, execution_time)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"  # type: ignore[attr-defined]
            start_time = time.time()

            # 记录入参
            args_str = _log_function_args(func, args, kwargs)

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 记录返回值
                _log_function_result(result, execution_time)

                logger.log(log_level, f"[成功] {func_name}")
                return result

            except Exception as e:
                execution_time = time.time() - start_time
                _log_function_error(func, e, args_str, execution_time)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def api_log(
        logger_name: str = "app",
        exclude_args: Optional[list] = None,
        log_result: bool = True,
        log_stack_trace: bool = True
):
    """简化的API日志装饰器"""
    return log_api_call(
        logger_name=logger_name,
        exclude_args=exclude_args,
        log_result=log_result,
        log_stack_trace=log_stack_trace
    )


def get_logger(
        name: str = "app",
        format_style: str = "detailed",
        separate_error_file: bool = True,
        backup_count: int = 30
) -> logging.Logger:
    """获取logger实例"""
    return LoggerManager.get_logger(
        name,
        format_style=format_style,
        separate_error_file=separate_error_file,
        backup_count=backup_count)
