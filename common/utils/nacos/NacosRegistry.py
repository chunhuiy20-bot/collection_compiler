"""
文件名: NacosRegistry.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 11:34
描述: Nacos 服务注册与发现工具类，提供 FastAPI 应用的服务注册、心跳保活、优雅下线功能。
支持自动获取本机 IP、服务注册重试、心跳失败自动重连、健康检查端点等特性。
包含 NacosConfig（配置模型）、NacosRegistry（注册管理器）和 create_nacos_lifespan（生命周期工厂函数）。

修改历史:
2026/2/6 11:34 - yangchunhui - 初始版本

依赖:
- asyncio: 异步任务管理，用于心跳任务和异步注册/注销
- socket: 网络操作，用于自动获取本机 IP 地址
- contextlib: asynccontextmanager 装饰器，用于创建异步上下文管理器
- typing: 类型注解支持（Optional, Dict）
- fastapi: FastAPI 框架，用于集成服务注册和健康检查端点
- nacos: nacos-sdk-python，Nacos 客户端 SDK，用于服务注册、注销和心跳
- pydantic: BaseModel 和 Field，用于配置模型的数据验证和序列化
"""

import asyncio
import socket
from contextlib import asynccontextmanager
from typing import Optional, Dict
from fastapi import FastAPI
import nacos
from pydantic import BaseModel, Field


def get_local_ip() -> str:
    """获取本机 IP（更可靠的方式）"""
    try:
        # 通过连接外部地址获取本机 IP（不会真正发送数据）
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        # 降级方案
        return socket.gethostbyname(socket.gethostname())



class NacosConfig(BaseModel):
    """Nacos 配置"""
    server_addresses: str = Field(default="127.0.0.1:8848", description="Nacos 服务器地址")
    namespace: str = Field(default="", description="命名空间 ID")
    service_name: str = Field(..., description="服务名称")
    service_ip: Optional[str] = Field(default=None, description="服务 IP，默认自动获取")
    service_port: int = Field(..., description="服务端口")
    group_name: str = Field(default="DEFAULT_GROUP", description="服务分组")
    weight: float = Field(default=1.0, description="权重")
    metadata: Dict[str, str] = Field(default_factory=dict, description="元数据")
    username: Optional[str] = Field(default=None, description="Nacos 用户名")
    password: Optional[str] = Field(default=None, description="Nacos 密码")
    heartbeat_interval: int = Field(default=5, description="心跳间隔（秒）")
    enabled: bool = Field(default=True, description="是否启用 Nacos 注册")
    ephemeral: bool = Field(default=True, description="是否为临时实例")
    max_retries: int = Field(default=3, description="注册失败最大重试次数")
    retry_delay: int = Field(default=5, description="重试延迟（秒）")

    def __init__(self, **data):
        super().__init__(**data)
        # 自动获取本机 IP
        if not self.service_ip:
            self.service_ip = get_local_ip()




class NacosRegistry:
    """Nacos 服务注册管理器"""

    def __init__(self, config: NacosConfig):
        self.config = config
        self.client: Optional[nacos.NacosClient] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._registered = False

    def _create_client(self) -> nacos.NacosClient:
        """创建 Nacos 客户端"""
        client_kwargs = {
            "server_addresses": self.config.server_addresses,
            "namespace": self.config.namespace,
        }
        
        # 只有在提供了用户名和密码时才添加认证信息
        if self.config.username and self.config.password:
            client_kwargs["username"] = self.config.username
            client_kwargs["password"] = self.config.password
        
        return nacos.NacosClient(**client_kwargs)

    async def register(self) -> bool:
        """注册服务到 Nacos（带重试）"""
        if not self.config.enabled:
            print(f"[Nacos] 注册已禁用，服务 {self.config.service_name} 正常启动")
            return False

        for attempt in range(self.config.max_retries):
            try:
                print(f"[Nacos] 正在注册服务: {self.config.service_name} (尝试 {attempt + 1}/{self.config.max_retries})")

                if not self.client:
                    self.client = self._create_client()

                self.client.add_naming_instance(
                    service_name=self.config.service_name,
                    ip=self.config.service_ip,
                    port=self.config.service_port,
                    group_name=self.config.group_name,
                    weight=self.config.weight,
                    metadata=self.config.metadata,
                    enable=True,
                    healthy=True,
                    ephemeral=self.config.ephemeral
                )

                self._registered = True
                print(f"[Nacos] 服务注册成功: {self.config.service_ip}:{self.config.service_port}")

                # 启动心跳任务
                if not self._heartbeat_task or self._heartbeat_task.done():
                    self._heartbeat_task = asyncio.create_task(self._send_heartbeat())

                return True

            except Exception as e:
                print(f"[Nacos] 注册失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")

                if attempt < self.config.max_retries - 1:
                    print(f"[Nacos] {self.config.retry_delay}秒后重试...")
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    print(f"[Nacos] 服务 {self.config.service_name} 将在没有 Nacos 注册的情况下继续运行")
                    self.client = None

        return False

    async def deregister(self) -> bool:
        """从 Nacos 注销服务"""
        # 停止心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 注销服务
        if self.client and self._registered:
            try:
                print(f"[Nacos] 正在注销服务: {self.config.service_name}")
                self.client.remove_naming_instance(
                    service_name=self.config.service_name,
                    ip=self.config.service_ip,
                    port=self.config.service_port,
                    group_name=self.config.group_name
                )
                self._registered = False
                print(f"[Nacos] 服务注销成功")
                return True
            except Exception as e:
                print(f"[Nacos] 注销失败: {e}")
                return False
        return False

    async def _send_heartbeat(self):
        """发送心跳到 Nacos"""
        consecutive_failures = 0
        max_failures = 3

        while True:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)

                if self.client and self._registered:
                    self.client.send_heartbeat(
                        service_name=self.config.service_name,
                        ip=self.config.service_ip,
                        port=self.config.service_port,
                        group_name=self.config.group_name
                    )
                    consecutive_failures = 0  # 重置失败计数

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_failures += 1
                print(f"[Nacos] 心跳发送失败 ({consecutive_failures}/{max_failures}): {e}")

                # 连续失败多次后尝试重新注册
                if consecutive_failures >= max_failures:
                    print(f"[Nacos] 心跳连续失败，尝试重新注册...")
                    self._registered = False
                    if await self.register():
                        consecutive_failures = 0

    def is_registered(self) -> bool:
        """检查服务是否已注册"""
        return self._registered and self.client is not None

    def get_health_status(self) -> Dict[str, any]:
        """获取健康状态"""
        return {
            "registered": self._registered,
            "client_connected": self.client is not None,
            "service_name": self.config.service_name,
            "service_address": f"{self.config.service_ip}:{self.config.service_port}",
            "nacos_server": self.config.server_addresses
        }

    def create_health_endpoint(self):
        """
        创建健康检查端点的路由函数

        使用示例:
            registry = NacosRegistry(config)
            app.get("/health")(registry.create_health_endpoint())
        """
        async def health_check():
            """健康检查接口"""
            return {
                "status": "UP",
                "nacos": self.get_health_status() if self.config.enabled else None
            }
        return health_check

    @asynccontextmanager
    async def lifespan_context(self, app: FastAPI):
        """FastAPI 生命周期上下文管理器"""
        # 启动时注册
        await self.register()
        print(type(app))
        yield
        
        # 关闭时注销
        await self.deregister()


def create_nacos_lifespan(config: NacosConfig, auto_health_check: bool = True, health_path: str = "/health"):
    """
    创建 Nacos 生命周期管理器的工厂函数

    Args:
        config: Nacos 配置
        auto_health_check: 是否自动注册健康检查端点，默认 True
        health_path: 健康检查端点路径，默认 "/health"

    使用示例:
        config = NacosConfig(
            service_name="my-service",
            service_port=8000
        )
        app = FastAPI(lifespan=create_nacos_lifespan(config))
        # 健康检查端点会自动注册到 /health

        # 如果不需要自动注册健康检查
        app = FastAPI(lifespan=create_nacos_lifespan(config, auto_health_check=False))

        # 自定义健康检查路径
        app = FastAPI(lifespan=create_nacos_lifespan(config, health_path="/router/health"))
    """
    registry = NacosRegistry(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 自动注册健康检查端点
        if auto_health_check:
            app.get(health_path)(registry.create_health_endpoint())

        async with registry.lifespan_context(app):
            # 将 registry 实例附加到 app.state，方便后续访问
            app.state.nacos_registry = registry
            yield

    return lifespan
