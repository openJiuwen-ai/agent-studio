from __future__ import annotations
from datetime import datetime
from sqlalchemy import (BigInteger, DateTime, Index, Integer, String, Boolean, func)
from sqlalchemy.orm import (Mapped, mapped_column)
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings


# ==================== runtime_info ====================
class RuntimeInfoDB(Base, DBFunBase):
    __tablename__ = "runtime_info"
    __table_args__ = (
        Index("idx_space_source", "space_id", "source_id"),
        Index("idx_type_status", "type", "status"),
        {"comment": "运行时信息表，记录 agent/插件/workflow 的部署运行状态"}
    )

    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    deployment_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, unique=True,
        comment='部署 ID，唯一标识一个运行时实例')
    space_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment='空间 ID')
    source_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment='原 agent/插件/workflow 的 ID')
    version: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment='version')
    type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment='类型：agent/plugin/workflow')
    name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='运行时名称')
    status: Mapped[str | None] = mapped_column(
        String(50), default=None, nullable=True,
        comment='运行状态：PENDING/RUNNING/STOPED/FAILED')
    url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment='访问 URL')
    port: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment='端口号')
    is_delete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment='是否被删除')
    create_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="创建时间")
    update_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"deployment_id='{self.deployment_id}', "
            f"space_id={self.space_id}, "
            f"source_id={self.source_id}, "
            f"type={self.type}, "
            f"name={self.name}, "
            f"status={self.status}, "
            f"url={self.url}, "
            f"port={self.port})>"
            f"is_delete={self.is_delete})>"
        )
