from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict
from openjiuwen_studio.ops.config import settings
from sqlalchemy import (BigInteger, Index, Integer, String, UniqueConstraint, JSON)
from sqlalchemy.orm import (Mapped, declarative_mixin, mapped_column)

from openjiuwen_studio.models.db_fun_base import Base, DBFunBase

if TYPE_CHECKING:
    pass


@declarative_mixin
class MemoryBaseDBMixin:
    """记忆库数据模型 Mixin，包含共享字段"""
    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        primary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    space_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="空间ID，用于多租户隔离")
    mdb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="记忆库ID，唯一标识")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="记忆库名称")
    description: Mapped[str] = mapped_column(String(100), nullable=False, comment="记忆库名描述")

    # Embedding 模型配置ID（关联到 embedding_model_configs 表）
    embedding_model_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="Embedding 模型配置ID")

    # llm 模型配置
    llm_model_config_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="Embedding 模型配置ID")

    # 时间戳
    create_time: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建时间")
    update_time: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="更新时间")


# ==================== 记忆库表 ====================
class MemoryBaseDB(MemoryBaseDBMixin, Base, DBFunBase):
    """记忆库数据表

    设计说明：
    - 一个 space_id 可以有多个记忆库（通过 mdb_id 区分）
    - 每个记忆库使用指定的 Embedding 模型配置
    """
    __tablename__ = "memory_base"
    __table_args__ = (
        UniqueConstraint("mdb_id", name="uix_mdb_id"),  # mdb_id 唯一约束
        Index("idx_space_id", "space_id"),  # space_id 索引，用于快速查询
        Index("idx_space_mdb", "space_id", "mdb_id"),  # 复合索引，用于空间+记忆库查询
        {"comment": "记忆库表，存储记忆库基本信息"}
    )
