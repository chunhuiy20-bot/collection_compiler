"""
文件名: BaseDBModel.py
作者: yangchunhui
创建日期: 2026/2/5
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/5 17:35
描述: 数据库模型基类，提供所有数据表的公共字段和功能。包含雪花算法ID生成、逻辑删除、审计字段（创建时间、更新时间、创建人、更新人）、乐观锁等通用功能。

修改历史:
2026/2/5 17:35 - yangchunhui - 初始版本

依赖:
- sqlalchemy: ORM框架，用于数据库模型定义和操作
- common.model.SnowFlake.SnowflakeIDGenerator: 雪花算法ID生成器
- os: 用于读取环境变量配置

使用示例:
"""


from sqlalchemy import Column, Integer, DateTime, func, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from common.model.SnowFlake import SnowflakeIDGenerator
import os

# 初始化雪花ID生成器（工作节点ID=1，数据中心ID=1）, 理论上应该从配置文件中获取，但是小项目不需要
generator = SnowflakeIDGenerator(int(os.getenv("DATACENTER_ID", 1)), int(os.getenv("DATACENTER_ID", 1)))


def generate_snowflake_id():
    """生成雪花算法ID"""
    return generator.generate()


# 创建SQLAlchemy基类
Base = declarative_base()


class BaseDBModel(Base):
    """所有模型的基类，包含公共字段"""
    __abstract__ = True  # 抽象类，不会创建表

    # default是在数据库层面执行的, id 本应该也是，但是__init__的时候，我们做了处理，给他赋予了值
    id = Column(BigInteger, primary_key=True, default=generate_snowflake_id)
    remark = Column(String(255), comment="备注", nullable=True)
    del_flag = Column(Integer, default=0, comment="逻辑删除标记")  # 0:未删除 1:已删除
    create_time = Column(DateTime, default=func.now(), comment="创建时间")
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    create_by = Column(String(50), nullable=True, default="1", comment="创建人,1表示系统默认")
    update_by = Column(String(50), nullable=True, comment="更新人")
    version = Column(Integer, default=0, comment="乐观锁")

    # 希望可以提前看到id
    def __init__(self, **kwargs):
        # 如果 id不在构造参数里面，提前调用generate_snowflake_id方法，为其赋值
        if "id" not in kwargs:
            kwargs["id"] = generate_snowflake_id()
        super().__init__(**kwargs)
