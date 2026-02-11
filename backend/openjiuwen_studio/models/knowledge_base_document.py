from __future__ import annotations
import enum
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import JSON, BigInteger, Index, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, declarative_mixin, mapped_column, relationship
from openjiuwen_studio.ops.config import settings
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase

if TYPE_CHECKING:
    pass


class DocumentStatus(str, enum.Enum):
    """文档状态枚举"""

    UPLOADING = "uploading"  # 上传中
    UPLOADED = "uploaded"  # 已上传
    PROCESSING = "processing"  # 处理中（解析、分块等）
    INDEXING = "indexing"  # 索引中（写入ES）
    INDEXED = "indexed"  # 已索引
    FAILED = "failed"  # 失败
    DELETED = "deleted"  # 已删除


@declarative_mixin
class KnowledgeBaseDocumentDBMixin:
    """知识库文档数据模型 Mixin"""

    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(
            Integer, primary_key=True, autoincrement=True, name="id"
        )
    else:
        primary_id: Mapped[int] = mapped_column(
            BigInteger, primary_key=True, autoincrement=True, name="id"
        )

    # 关联字段
    space_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="空间ID，用于多租户隔离"
    )
    kb_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="知识库ID")
    doc_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="文档ID，唯一标识"
    )

    # 文档基本信息
    name: Mapped[str] = mapped_column(String(500), nullable=False, comment="文档名称（文件名）")
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="文档在服务器上的存储路径"
    )
    obs_name: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="OBS 存储路径在存储桶中"
    )
    file_size: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="文件大小（字节）"
    )
    file_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="文件类型（如：pdf, docx, txt等）"
    )
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME类型")

    # 文档状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentStatus.UPLOADING.value, comment="文档状态"
    )

    # Indexing details
    index_manager_type: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Whether Chroma or Milvus is used for indexing"
    )
    index_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="ES中的索引ID")
    index_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="ES索引名称")
    chunk_count: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, default=0, comment="文档分块数量"
    )

    # 处理信息
    process_info: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="处理信息（错误信息、处理进度等）"
    )

    # 元数据（注意：metadata 是 SQLAlchemy 保留字段，使用 doc_metadata）
    doc_metadata: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, name="metadata", comment="文档元数据（作者、标签、自定义字段等）"
    )

    # 扩展字段
    _rest_: Mapped[Dict | None] = mapped_column(JSON, nullable=True, comment="扩展字段")

    # 时间戳
    create_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建时间")
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="更新时间")
    indexed_time: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="索引完成时间"
    )


# ==================== 知识库文档表 ====================
class KnowledgeBaseDocumentDB(KnowledgeBaseDocumentDBMixin, Base, DBFunBase):
    """知识库文档数据表

    设计说明：
    - 存储文档的元数据信息
    - 文档的物理文件存储在服务器文件系统（file_path）
    - 文档的索引存储在 ES 中（通过 es_index_id 关联）
    - 通过 kb_id + space_id 关联到知识库
    """

    __tablename__ = "knowledge_base_document"
    __table_args__ = (
        UniqueConstraint("doc_id", name="uix_doc_id"),  # doc_id 唯一约束
        Index("idx_space_id", "space_id"),  # space_id 索引
        Index("idx_kb_id", "kb_id"),  # kb_id 索引
        Index("idx_space_kb", "space_id", "kb_id"),  # 复合索引：按空间+知识库查询
        Index("idx_status", "status"),  # 状态索引：用于查询不同状态的文档
        Index("idx_space_kb_doc", "space_id", "kb_id", "doc_id"),  # 复合索引：完整查询路径
        {"comment": "知识库文档表，存储文档元数据信息"},
    )

    # 关联关系：文档属于某个知识库（使用 viewonly，因为是通过复合键关联，没有外键约束）
    knowledge_base: Mapped["KnowledgeBaseDB"] = relationship(
        "KnowledgeBaseDB",
        primaryjoin="and_(KnowledgeBaseDocumentDB.kb_id==foreign(KnowledgeBaseDB.kb_id), "
        "KnowledgeBaseDocumentDB.space_id==foreign(KnowledgeBaseDB.space_id))",
        viewonly=True,
        back_populates="documents",
    )
