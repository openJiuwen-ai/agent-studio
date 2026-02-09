from __future__ import annotations
from datetime import datetime

from sqlalchemy import (JSON, BigInteger, DateTime, ForeignKey, Index, Integer,
                        String, Text, func)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import (Mapped, mapped_column, relationship)

from openjiuwen_studio.models.agent import AgentBaseDB, AgentPublishDB
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings
# ==================== agent_execution ====================


class AgentExecutionDB(Base, DBFunBase):
    __tablename__ = "agent_execution"
    __table_args__ = (
        Index("idx_agent", "space_id", "agent_id", "agent_version"),
        Index("agent_id_version", "agent_id", "agent_version"),
        {"comment": "某次agent执行的总结信息"}
    )

    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    space_id: Mapped[str | None] = mapped_column(String(100), nullable=False)
    # 与agent的多态关联字段
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_version: Mapped[str | None] = mapped_column(
        String(100), default=DBFunBase.__version_none__, comment='agent version. empty if is draft')
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True,
                                          unique=True, comment='the trace id of this execution')
    status: Mapped[str | None] = mapped_column(
        String(16), default=None, comment='finish/start/error/running/interrupted/unknown')
    mode: Mapped[int | None] = mapped_column(
        Integer, default=None, comment='the execution mode: 0. debug run 1. release run')

    call_type: Mapped[str | None] = mapped_column(
        String(100), default=None, nullable=True, comment='The caller type that initiated this execution')
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment='execution duration in millisecond')
    inputs: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True, comment='inputs of this execution')
    outputs: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True, comment='outputs of this execution')
    error_code: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True, comment='error code')
    fail_reason: Mapped[str | None] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"),
        default=None,
        nullable=True,
        comment='the reason for failure'
    )
    input_tokens: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True, comment='number of input tokens')
    output_tokens: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True, comment='number of output tokens')
    execute_info_list: Mapped[list[dict] | None] = mapped_column(
        JSON, default=None, nullable=True, comment="agent's components' execute info")

    create_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), comment="更新时间")

    agent_execution_details_list: Mapped[list[AgentExecutionDetailsDB]] = relationship(
        "AgentExecutionDetailsDB",
        foreign_keys="AgentExecutionDetailsDB.trace_id",
        back_populates="agent_execution_summary",
        cascade="all, delete-orphan",        # ← 内存+数据库都会删
    )

    # 与agent表关联
    agent_draft: Mapped[AgentBaseDB] = relationship(
        "AgentBaseDB",
        primaryjoin=f"and_(" \
                   f"AgentExecutionDB.agent_version=='{DBFunBase.__version_none__}', " \
                   f"AgentExecutionDB.agent_id==AgentBaseDB.agent_id, " \
                   f"AgentExecutionDB.agent_version==AgentBaseDB.agent_version" \
                   f")",
        foreign_keys=[agent_id, agent_version],
        back_populates="agent_executions",
    )
    # 与agent_publish表关联
    agent_publish: Mapped[AgentPublishDB] = relationship(
        "AgentPublishDB",
        primaryjoin=f"and_(" \
                   f"AgentExecutionDB.agent_version!='{DBFunBase.__version_none__}', " \
                   f"AgentExecutionDB.agent_id==AgentPublishDB.agent_id, " \
                   f"AgentExecutionDB.agent_version==AgentPublishDB.agent_version" \
                   f")",
        foreign_keys=[agent_id, agent_version],
        back_populates="agent_executions",
    )

    # 通用父对象访问器
    def get_agent(self):
        if self.agent_version == DBFunBase.__version_none__:
            return self.agent_draft
        else:
            return self.agent_publish

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"agent_id={self.agent_id}, "
            f"agent_version={self.agent_version}, "
            f"trace_id='{self.trace_id}, "
            f"status={self.status}, "
            f"duration={self.duration}, "
            f"create_time='{self.create_time})>"
        )

# ==================== agent_execution_details ====================


class AgentExecutionDetailsDB(Base, DBFunBase):
    __tablename__ = "agent_execution_details"
    __table_args__ = {"comment": "某次agent执行每个步骤的详细信息"}

    # 主键
    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 业务主键：trace_id + invoke_id 联合唯一（如需要可改成联合主键）
    trace_id: Mapped[str] = mapped_column(String(100),
                                            ForeignKey("agent_execution.trace_id"),  # ← 数据库级联
                                            nullable=False,
                                            index=True,
                                            )
    invoke_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # 时间
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # 数据
    inputs: Mapped[dict | None] = mapped_column(JSON, default=None)
    outputs: Mapped[dict | None] = mapped_column(JSON, default=None)
    input_tokens: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True, comment='number of input tokens')
    output_tokens: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True, comment='number of output tokens')
    error: Mapped[dict] = mapped_column(JSON, default=None)

    # invoke的父子关系
    parent_invoke_id: Mapped[str | None] = mapped_column(String(100), default=None)
    child_invokes_id: Mapped[list[str] | None] = mapped_column(JSON, default=None)

    # TraceAgentSpan 特有字段
    invoke_type: Mapped[str | None] = mapped_column(
        String(100), default=None, comment='the invoke type of this agent execution')
    name: Mapped[str | None] = mapped_column(String(255), default=None, comment='the name of this agent execution')
    elapsed_time: Mapped[str | None] = mapped_column(
        String(100), default=None, comment='the elapsed time of this execution')
    meta_data: Mapped[dict | None] = mapped_column(
        JSON, default=None, comment='include llm function tools and token infos')

    # 预留字段：用于嵌套agent调用
    agent_parent_invoke_id: Mapped[str | None] = mapped_column(
        String(100), default=None, comment='Reserved field: nested agents for future adaptation of agent nodes')

    # 未定义的字段保存于_rest_中
    _rest_: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)

    agent_execution_summary: Mapped[AgentExecutionDB] = relationship(
        "AgentExecutionDB",
        foreign_keys=trace_id,
        back_populates="agent_execution_details_list"
    )

    workflow_execution: Mapped["WorkflowExecutionDB | None"] = relationship(
        "WorkflowExecutionDB",
        foreign_keys="WorkflowExecutionDB.agent_execution_detail_id",
        back_populates="agent_execution_detail",
        cascade="all, delete-orphan",   # 删除 agent_execution_detail 时自动删除 workflow_execution
        single_parent=True,             # 确保 workflow_execution 最多只能属于一个 agent_execution_detail
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"trace_id='{self.trace_id}, "
            f"invoke_id={self.invoke_id}, "
            f"invoke_type='{self.invoke_type})>"
        )