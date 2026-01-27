from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict
from openjiuwen_studio.ops.config import settings
from sqlalchemy import JSON, BigInteger, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column, relationship

from openjiuwen_studio.models.db_fun_base import Base, DBFunBase

if TYPE_CHECKING:
    pass


@declarative_mixin
class KnowledgeBaseDBMixin:
    """知识库数据模型 Mixin，包含共享字段"""

    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True, name="id"
        )
    else:
        primary_id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True, name="id"
        )

    space_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="空间ID，用于多租户隔离"
    )
    kb_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="知识库ID，唯一标识"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="知识库描述")

    # Embedding 模型配置ID（关联到 embedding_model_configs 表）
    index_manager_type: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Whether Chroma or Milvus is used for indexing"
    )
    embedding_model_config_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Embedding 模型配置ID，知识库创建时选择，后续不可更改",
    )

    # 知识库配置（如：ES索引配置、向量模型配置等）
    config: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="知识库配置信息"
    )

    # 扩展字段
    _rest_: Mapped[Dict | None] = mapped_column(
        JSON, nullable=True, comment="扩展字段，存储其他未定义的数据"
    )

    # 时间戳
    create_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建时间")
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="更新时间")


# ==================== 知识库表 ====================
class KnowledgeBaseDB(KnowledgeBaseDBMixin, Base, DBFunBase):
    """知识库数据表

    设计说明：
    - 一个 space_id 可以有多个知识库（通过 kb_id 区分）
    - 每个知识库可以有多篇文档（通过 KnowledgeBaseDocumentDB 关联）
    - 文档的物理文件存储在服务器文件系统
    - 文档的索引存储在 ES 中
    """

    __tablename__ = "knowledge_base"
    __table_args__ = (
        UniqueConstraint("kb_id", name="uix_kb_id"),  # kb_id 唯一约束
        Index("idx_space_id", "space_id"),  # space_id 索引，用于快速查询
        Index("idx_space_kb", "space_id", "kb_id"),  # 复合索引，用于空间+知识库查询
        {"comment": "知识库表，存储知识库基本信息"},
    )

    # 关联关系：一个知识库有多篇文档（使用 viewonly，因为是通过复合键关联，没有外键约束）
    documents: Mapped[list["KnowledgeBaseDocumentDB"]] = relationship(
        "KnowledgeBaseDocumentDB",
        primaryjoin="and_(KnowledgeBaseDocumentDB.kb_id==foreign(KnowledgeBaseDB.kb_id), "
        "KnowledgeBaseDocumentDB.space_id==foreign(KnowledgeBaseDB.space_id))",
        viewonly=True,
        back_populates="knowledge_base",
    )
