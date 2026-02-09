"""
Trace Summary 数据库模型

基于设计文档: TRACE_SUMMARY_SCHEMA.md
用于存储workflow和agent执行摘要信息
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (JSON, BigInteger, DateTime, Integer, String,
                        Text)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings


class TraceSummaryDB(Base, DBFunBase):
    """Trace Summary 数据库模型"""
    __tablename__ = "trace_summary"

    # 主键字段
    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")

    # 业务字段
    space_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="空间ID")
    business_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="业务ID（workflow_id/agent_id）")
    business_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="业务类型（WORKFLOW/AGENT）")
    business_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="业务版本号，草稿版本为空")
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, comment="执行追踪ID")

    # 执行信息
    mode: Mapped[int] = mapped_column(Integer, nullable=False, comment="执行模式：0-调试运行，1-发布运行，2-节点调试")
    call_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="调用方类型")
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="执行时长（毫秒）")
    status: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, comment="执行状态：finish/start/error/running/interrupted/unknown")

    # Token统计
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="输入Token数量")
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="输出Token数量")

    # 数据字段
    inputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="执行输入参数")
    outputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, comment="执行输出结果")
    execute_info_list: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True, comment="工作流组件执行信息列表")

    # 错误信息
    error_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="错误代码")
    fail_reason: Mapped[Optional[str]] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"),
        nullable=True,
        comment="失败原因"
    )

    # 时间字段
    create_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="创建时间")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="更新时间")

    __table_args__ = (
        {"comment": "执行摘要表"},
    )

    def __repr__(self) -> str:
        return f"<TraceSummaryDB(id={self.id}, business_type={self.business_type}, \
            business_id={self.business_id}, trace_id={self.trace_id})>"