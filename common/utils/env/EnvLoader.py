"""
文件名: EnvLoader.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6
描述: 环境变量加载工具，提供自动定位服务根目录并加载对应 .env 文件的功能。
支持多环境配置（.env.dev, .env.prod 等）、自动检测服务根目录、错误处理和日志记录。

修改历史:
2026/2/6 - yangchunhui - 初始版本

依赖:
- pathlib: Path，用于跨平台的文件路径操作
- dotenv: load_dotenv，用于加载 .env 文件
- typing: Optional，类型注解支持
- os: 环境变量操作

使用示例:
# 方式1：在服务的启动文件中（如 account_service/main.py）
from common.utils.env.EnvLoader import load_service_env
load_service_env(__file__)  # 自动加载 account_service/.env

# 方式2：指定环境
load_service_env(__file__, env_file=".env.prod")

# 方式3：在子目录中调用（如 account_service/config/settings.py）
load_service_env(__file__, levels_up=2)  # 向上2层找到 account_service/.env
"""
from pathlib import Path
from dotenv import load_dotenv


def load_service_env(
    caller_file: str,
    env_file: str = ".env",
    levels_up: int = 1,
    override: bool = True,
    verbose: bool = True
) -> bool:
    """
    加载服务的环境变量文件

    Args:
        caller_file: 调用文件的 __file__ 变量
        env_file: 环境变量文件名，默认为 .env，支持 .env.dev, .env.prod 等
        levels_up: 向上查找的层级数，默认为 1（适用于服务根目录下的文件）
        override: 是否覆盖已存在的环境变量，默认为 True
        verbose: 是否打印加载信息，默认为 True

    Returns:
        bool: 是否成功加载

    Example:
        # 在 account_service/main.py 中调用
        load_service_env(__file__)  # 加载 account_service/.env

        # 在 account_service/config/settings.py 中调用
        load_service_env(__file__, levels_up=2)  # 向上2层加载 account_service/.env

        # 加载生产环境配置
        load_service_env(__file__, env_file=".env.prod")
    """
    try:
        # 获取调用文件的绝对路径
        caller_path = Path(caller_file).resolve()

        # 向上查找指定层级，得到服务根目录
        service_root = caller_path.parent
        for _ in range(levels_up):
            service_root = service_root.parent

        # 构建 .env 文件的完整路径
        env_path = service_root / env_file

        # 检查文件是否存在
        if not env_path.exists():
            if verbose:
                print(f"⚠️  环境变量文件不存在: {env_path}")
            return False

        # 加载环境变量
        load_dotenv(dotenv_path=str(env_path), override=override)

        if verbose:
            print(f"✓ 成功加载环境变量: {env_path}")
            print(f"  服务根目录: {service_root}")

        return True

    except Exception as e:
        if verbose:
            print(f"✗ 加载环境变量失败: {e}")
        return False


def get_service_root(caller_file: str, levels_up: int = 1) -> Path:
    """
    获取服务根目录

    Args:
        caller_file: 调用文件的 __file__ 变量
        levels_up: 向上查找的层级数，默认为 1

    Returns:
        Path: 服务根目录的 Path 对象

    Example:
        service_root = get_service_root(__file__)
        config_path = service_root / "config" / "app.yaml"
    """
    caller_path = Path(caller_file).resolve()
    service_root = caller_path.parent
    for _ in range(levels_up):
        service_root = service_root.parent
    return service_root


def load_env_with_fallback(
    caller_file: str,
    env_files: list[str] = None,
    levels_up: int = 1,
    verbose: bool = True
) -> bool:
    """
    按优先级加载环境变量文件（支持回退机制）

    Args:
        caller_file: 调用文件的 __file__ 变量
        env_files: 环境变量文件列表，按优先级排序，默认为 [".env.local", ".env"]
        levels_up: 向上查找的层级数，默认为 1
        verbose: 是否打印加载信息，默认为 True

    Returns:
        bool: 是否成功加载至少一个文件

    Example:
        # 优先加载 .env.local，如果不存在则加载 .env
        load_env_with_fallback(__file__, env_files=[".env.local", ".env"])
    """
    if env_files is None:
        env_files = [".env.local", ".env"]

    for env_file in env_files:
        if load_service_env(caller_file, env_file, levels_up, verbose=False):
            if verbose:
                print(f"✓ 成功加载环境变量: {env_file}")
            return True

    if verbose:
        print(f"✗ 未找到任何环境变量文件: {env_files}")
    return False
