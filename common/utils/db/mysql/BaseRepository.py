"""
文件名: BaseRepository.py
作者: yangchunhui
创建日期: 2026/2/5
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6
描述: 同步数据访问层基类，提供完整的 CRUD 操作和查询功能。包含 QueryWrapper（链式查询条件构建器）和 BaseRepository（同步仓储基类），支持自动会话管理、事务控制、逻辑删除、分页查询等功能。

修改历史:
2026/2/5 - yangchunhui - 初始版本
2026/2/6 - yangchunhui - 参照 AsyncBaseRepository 优化，添加自动 session 管理功能

依赖:
- typing: 提供泛型和类型注解支持（TypeVar, Generic, List, Optional, Dict, Any, Type, Callable）
- functools: wraps 装饰器，用于保持被装饰函数的元数据
- sqlalchemy.orm: Session（同步数据库会话）
- sqlalchemy: 查询构建工具（and_, desc, asc, func）和异常处理（SQLAlchemyError）
- common.model.BaseDBModel: 数据库模型基类
- common.utils.db.MultiDBManager: 多数据库管理器（运行时导入）

使用示例:
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any, Type, Callable
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc, func
from sqlalchemy.exc import SQLAlchemyError
from common.model.BaseDBModel import BaseDBModel
from common.utils.db.mysql.MultiAsyncDBManager import multi_db

# 定义泛型类型
T = TypeVar('T', bound=BaseDBModel)


def auto_session(method: Callable) -> Callable:
    """自动管理 session 的装饰器"""
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # 如果已经有 session，直接执行
        if self._provided_db is not None or self._owned_session is not None:
            return method(self, *args, **kwargs)

        # 否则创建临时 session 执行
        with multi_db.session(self.db_name) as session:
            self._owned_session = session
            try:
                return method(self, *args, **kwargs)
            finally:
                self._owned_session = None
    return wrapper


class QueryWrapper:
    """
    建造者模式构建条件包装器
    查询条件包装器，类似 MyBatis-Plus 的 QueryWrapper
    """

    def __init__(self, model_class: Type[BaseDBModel]):
        self.model_class = model_class
        self.conditions = []
        self.order_by_clauses = []
        self._limit = None
        self._offset = None

    def eq(self, field: str, value: Any) -> "QueryWrapper":
        """等于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column == value)
        return self

    def ne(self, field: str, value: Any) -> "QueryWrapper":
        """不等于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column != value)
        return self

    def gt(self, field: str, value: Any) -> "QueryWrapper":
        """大于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column > value)
        return self

    def ge(self, field: str, value: Any) -> "QueryWrapper":
        """大于等于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column >= value)
        return self

    def lt(self, field: str, value: Any) -> "QueryWrapper":
        """小于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column < value)
        return self

    def le(self, field: str, value: Any) -> "QueryWrapper":
        """小于等于条件"""
        if value is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column <= value)
        return self

    def like(self, field: str, value: str) -> "QueryWrapper":
        """模糊查询"""
        if value:
            column = getattr(self.model_class, field)
            self.conditions.append(column.like(f"%{value}%"))
        return self

    def like_left(self, field: str, value: str) -> "QueryWrapper":
        """左模糊查询"""
        if value:
            column = getattr(self.model_class, field)
            self.conditions.append(column.like(f"%{value}"))
        return self

    def like_right(self, field: str, value: str) -> "QueryWrapper":
        """右模糊查询"""
        if value:
            column = getattr(self.model_class, field)
            self.conditions.append(column.like(f"{value}%"))
        return self

    def in_(self, field: str, values: List[Any]) -> "QueryWrapper":
        """IN 查询"""
        if values:
            column = getattr(self.model_class, field)
            self.conditions.append(column.in_(values))
        return self

    def not_in(self, field: str, values: List[Any]) -> "QueryWrapper":
        """NOT IN 查询"""
        if values:
            column = getattr(self.model_class, field)
            self.conditions.append(~column.in_(values))
        return self

    def between(self, field: str, start: Any, end: Any) -> "QueryWrapper":
        """BETWEEN 查询"""
        if start is not None and end is not None:
            column = getattr(self.model_class, field)
            self.conditions.append(column.between(start, end))
        return self

    def is_null(self, field: str) -> "QueryWrapper":
        """IS NULL 查询"""
        column = getattr(self.model_class, field)
        self.conditions.append(column.is_(None))
        return self

    def is_not_null(self, field: str) -> "QueryWrapper":
        """IS NOT NULL 查询"""
        column = getattr(self.model_class, field)
        self.conditions.append(column.isnot(None))
        return self

    def order_by_asc(self, *fields: str) -> "QueryWrapper":
        """升序排序"""
        for field in fields:
            column = getattr(self.model_class, field)
            self.order_by_clauses.append(asc(column))
        return self

    def order_by_desc(self, *fields: str) -> "QueryWrapper":
        """降序排序"""
        for field in fields:
            column = getattr(self.model_class, field)
            self.order_by_clauses.append(desc(column))
        return self

    def limit(self, limit: int) -> "QueryWrapper":
        """限制返回数量"""
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryWrapper":
        """偏移量"""
        self._offset = offset
        return self

    def build_query(self, query):
        """构建查询"""
        if self.conditions:
            query = query.filter(and_(*self.conditions))
        if self.order_by_clauses:
            query = query.order_by(*self.order_by_clauses)
        if self._offset is not None:
            query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)
        return query


class BaseRepository(Generic[T]):
    """
    通用 Repository 基类，提供类似 MyBatis-Plus 的 CRUD 操作

    支持两种使用方式：
    1. 传统方式（手动管理 session）:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(db=db, model_class=User)

        # 使用
        with multi_db.session('default') as db:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(1)

    2. 自动管理方式（推荐）:
        class UserRepository(BaseRepository[User]):
            def __init__(self):
                super().__init__(model_class=User, db_name='default')

        # 使用 - 自动管理 session
        user_repo = UserRepository()
        user = user_repo.get_by_id(1)  # 自动创建和关闭 session

        # 或使用上下文管理器
        with UserRepository() as user_repo:
            user = user_repo.get_by_id(1)
    """

    def __init__(self, model_class: Type[T], db: Optional[Session] = None, db_name: str = 'default'):
        """
        初始化 Repository

        Args:
            model_class: 模型类
            db: 数据库会话（可选，如果不提供则使用 db_name 自动管理）
            db_name: 数据库名称（当 db 为 None 时使用）
        """
        self.model_class = model_class
        self._provided_db = db  # 外部提供的 session
        self._owned_session: Optional[Session] = None  # 自己创建的 session
        self.db_name = db_name

    @property
    def db(self) -> Session:
        """获取当前使用的 session"""
        if self._provided_db is not None:
            return self._provided_db
        if self._owned_session is not None:
            return self._owned_session
        raise RuntimeError("No database session available")

    def __enter__(self):
        """进入上下文管理器"""
        if self._provided_db is None and self._owned_session is None:

            self._owned_session = multi_db.get_session(self.db_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if self._owned_session is not None:
            try:
                if exc_type is None:
                    self._owned_session.commit()
                else:
                    self._owned_session.rollback()
            finally:
                self._owned_session.close()
                self._owned_session = None

    def _execute_with_session(self, func: Callable, *args, **kwargs):
        """
        使用 session 执行函数

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        return func(*args, **kwargs)

    # ==================== 基础 CRUD 操作 ====================

    @auto_session
    def save(self, entity: T) -> T:
        """
        保存实体（新增）

        Args:
            entity: 实体对象

        Returns:
            保存后的实体
        """
        try:
            self.db.add(entity)
            self.db.flush()
            self.db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    @auto_session
    def save_batch(self, entities: List[T]) -> List[T]:
        """
        批量保存

        Args:
            entities: 实体列表

        Returns:
            保存后的实体列表
        """
        try:
            self.db.add_all(entities)
            self.db.flush()
            for entity in entities:
                self.db.refresh(entity)
            return entities
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    @auto_session
    def update_by_id(self, entity: T) -> bool:
        """
        根据 ID 更新实体

        Args:
            entity: 实体对象（必须包含 id）

        Returns:
            是否更新成功
        """
        try:
            self.db.merge(entity)
            self.db.flush()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    @auto_session
    def update_by_id_selective(self, id: int, updates: Dict[str, Any]) -> bool:
        """
        根据 ID 选择性更新（只更新非 None 字段）

        Args:
            id: 实体 ID
            updates: 要更新的字段字典

        Returns:
            是否更新成功
        """
        try:
            # 过滤掉 None 值
            updates = {k: v for k, v in updates.items() if v is not None}
            if not updates:
                return False

            result = (
                self.db.query(self.model_class)
                .filter(
                    and_(
                        self.model_class.id == id,
                        self.model_class.del_flag == 0
                    )
                )
                .update(updates)
            )
            self.db.flush()
            return result > 0
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    @auto_session
    def remove_by_id(self, id: int, physical: bool = False) -> bool:
        """
        根据 ID 删除（默认逻辑删除）

        Args:
            id: 实体 ID
            physical: 是否物理删除，默认 False（逻辑删除）

        Returns:
            是否删除成功
        """
        try:
            if physical:
                # 物理删除
                result = (
                    self.db.query(self.model_class)
                    .filter(
                        and_(
                            self.model_class.id == id
                        )
                    )
                    .delete(synchronize_session=False)
                )
            else:
                # 逻辑删除
                result = (
                    self.db.query(self.model_class)
                    .filter(
                        and_(
                            self.model_class.id == id,
                            self.model_class.del_flag == 0
                        )
                    )
                    .update({"del_flag": 1}, synchronize_session=False)
                )

            self.db.flush()
            return result > 0
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    @auto_session
    def remove_by_ids(self, ids: List[int], physical: bool = False) -> int:
        """
        根据 ID 列表批量删除

        Args:
            ids: ID 列表
            physical: 是否物理删除

        Returns:
            删除的记录数
        """
        try:
            if physical:
                result = self.db.query(self.model_class).filter(
                    self.model_class.id.in_(ids)
                ).delete(synchronize_session=False)
            else:
                result = (
                    self.db.query(self.model_class)
                    .filter(
                        and_(
                            self.model_class.id.in_(ids),
                            self.model_class.del_flag == 0
                        )
                    )
                    .update({"del_flag": 1}, synchronize_session=False)
                )

            self.db.flush()
            return result
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e

    # ==================== 查询操作 ====================

    @auto_session
    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据 ID 查询

        Args:
            id: 实体 ID

        Returns:
            实体对象或 None
        """
        return (
            self.db.query(self.model_class)
            .filter(
                and_(
                    self.model_class.id == id,
                    self.model_class.del_flag == 0
                )
            )
            .first()
        )

    @auto_session
    def get_one(self, wrapper: QueryWrapper) -> Optional[T]:
        """
        根据条件查询单个实体

        Args:
            wrapper: 查询条件包装器

        Returns:
            实体对象或 None
        """
        query = (
            self.db.query(self.model_class)
            .filter(
                and_(
                    self.model_class.del_flag == 0
                )
            )
        )
        query = wrapper.build_query(query)
        return query.first()

    @auto_session
    def list(self, wrapper: Optional[QueryWrapper] = None) -> List[T]:
        """
        查询列表

        Args:
            wrapper: 查询条件包装器（可选）

        Returns:
            实体列表
        """
        query = (
            self.db.query(self.model_class)
            .filter(
                and_(
                    self.model_class.del_flag == 0
                )
            )
        )
        if wrapper:
            query = wrapper.build_query(query)
        return query.all()

    @auto_session
    def list_by_ids(self, ids: List[int]) -> List[T]:
        """
        根据 ID 列表查询

        Args:
            ids: ID 列表

        Returns:
            实体列表
        """
        return (
            self.db.query(self.model_class)
            .filter(
                and_(
                    self.model_class.id.in_(ids),
                    self.model_class.del_flag == 0
                )
            )
            .all()
        )

    @auto_session
    def count(self, wrapper: Optional[QueryWrapper] = None) -> int:
        """
        统计数量

        Args:
            wrapper: 查询条件包装器（可选）

        Returns:
            记录数
        """
        query = (
            self.db.query(func.count(self.model_class.id))
            .filter(
                and_(
                    self.model_class.del_flag == 0
                )
            )
        )
        if wrapper:
            if wrapper.conditions:
                query = query.filter(and_(*wrapper.conditions))
        return query.scalar()

    @auto_session
    def exists(self, wrapper: QueryWrapper) -> bool:
        """
        判断是否存在

        Args:
            wrapper: 查询条件包装器

        Returns:
            是否存在
        """
        return self.count(wrapper) > 0

    @auto_session
    def page(self, page: int, page_size: int, wrapper: Optional[QueryWrapper] = None) -> Dict[str, Any]:
        """
        分页查询

        Args:
            page: 页码（从 1 开始）
            page_size: 每页大小
            wrapper: 查询条件包装器（可选）

        Returns:
            分页结果字典，包含 total, page, page_size, items
        """
        # 查询总数
        total = self.count(wrapper)

        # 查询数据
        query = (
            self.db.query(self.model_class)
            .filter(
                and_(
                    self.model_class.del_flag == 0
                )
            )
        )
        if wrapper:
            query = wrapper.build_query(query)

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

    # ==================== 便捷方法 ====================

    def query_wrapper(self) -> QueryWrapper:
        """
        创建查询条件包装器

        Returns:
            QueryWrapper 实例
        """
        return QueryWrapper(self.model_class)

    def save_or_update(self, entity: T) -> T:
        """
        保存或更新（根据 ID 是否存在判断）

        Args:
            entity: 实体对象

        Returns:
            保存或更新后的实体
        """
        if hasattr(entity, 'id') and entity.id and self.get_by_id(entity.id):
            self.update_by_id(entity)
            return entity
        else:
            return self.save(entity)

    def list_all(self) -> List[T]:
        """
        查询所有记录（不包含已删除）

        Returns:
            实体列表
        """
        return self.list()


# """
# BaseRepository 使用示例
#
# 类似 MyBatis-Plus 的 CRUD 操作示例
# """
# from sqlalchemy import Column, String, Integer
#
#
# # ==================== 1. 定义模型 ====================
#
# class User(BaseDBModel):
#     """用户模型"""
#     __tablename__ = "users"
#
#     username = Column(String(50), nullable=False, comment="用户名")
#     email = Column(String(100), comment="邮箱")
#     age = Column(Integer, comment="年龄")
#     status = Column(Integer, default=1, comment="状态：1-正常，0-禁用")
#
#
# # ==================== 2. 定义 Repository ====================
#
# class UserRepository(BaseRepository[User]):
#     """用户 Repository"""
#
#     def __init__(self, db: Session):
#         super().__init__(db, User)
#
#     # 可以添加自定义方法
#     def find_by_username(self, username: str):
#         """根据用户名查询"""
#         wrapper = self.query_wrapper().eq("username", username)
#         return self.get_one(wrapper)
#
#     def find_active_users(self):
#         """查询所有活跃用户"""
#         wrapper = self.query_wrapper().eq("status", 1)
#         return self.list(wrapper)
