
from typing import Optional, Dict, Any
from sqlalchemy import String, BigInteger, Text, JSON, Integer
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings


class TraceDetailDB(Base, DBFunBase):
    """统一的 Trace Detail 数据库模型"""
    __tablename__ = "trace_detail"

    # 主键字段
    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")

    # 业务字段
    space_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="空间ID")
    business_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="业务ID（workflow_id/agent_id）")
    business_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="业务类型（WORKFLOW/AGENT）")
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="追踪ID，单次执行唯一标识")

    # Span字段
    span_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="Span ID，执行单元唯一标识")
    span_type: Mapped[str] = mapped_column(String(512), nullable=False, comment="Span类型 (如: prompt_executor)")
    span_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Span名称 (如: llm_completion)")
    parent_span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="父Span ID，支持嵌套调用")

    # 请求信息
    method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="HTTP方法 (如: POST)")
    psm: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="服务实例信息 (如: IP地址)")
    logid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="日志ID")
    platform_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="平台类型 (如: prompt)")

    # 执行信息
    start_time_micros: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="开始时间微秒戳")
    end_time_micros: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="结束时间微秒戳")
    status_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="状态码 (如: '0'表示成功)")

    # 数据字段
    input: Mapped[Optional[str]] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"),
        nullable=True,
        comment="输入数据"
    )
    output: Mapped[Optional[str]] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"),
        nullable=True,
        comment="输出数据"
    )
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="扩展属性对象")

    # 索引
    __table_args__ = (
        {"comment": "统一执行追踪表"},
    )

    def __repr__(self) -> str:
        return f"<TraceDetailDB(id={self.id}, business_type={self.business_type}, \
            business_id={self.business_id}, trace_id={self.trace_id})>"