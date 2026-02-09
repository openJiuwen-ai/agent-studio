from __future__ import annotations
from datetime import datetime
from sqlalchemy import (JSON, BigInteger, DateTime, ForeignKey, Index, Integer,
                        String, Text, func)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import (Mapped, mapped_column, relationship)
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.models.workflow import WorkflowBaseDB, WorkflowPublishDB
from openjiuwen_studio.ops.config import settings


# ==================== workflow_execution ====================
class WorkflowExecutionDB(Base, DBFunBase):
    __tablename__ = "workflow_execution"
    __table_args__ = (
        Index("idx_workflow", "space_id", "workflow_id", "workflow_version"),
        Index("workflow_id_version", "workflow_id", "workflow_version"),
        {"comment": "某次workflow执行的总结信息"}      
    )

    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    space_id: Mapped[str | None] = mapped_column(String(100), nullable=False)
    # 与workflow的多态关联字段
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_version: Mapped[str | None] = mapped_column(
        String(100), default=DBFunBase.__version_none__, comment='workflow version. empty if is draft')
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True,
                                          comment='the trace id of this execution')
    status: Mapped[str | None] = mapped_column(
        String(16), default=None, comment='finish/start/error/running/interrupted/unknown')
    mode: Mapped[int] = mapped_column(Integer, default=0, nullable=False,
                                      comment='the execution mode: 0. debug run 1. release run 2. node debug')
    
    call_type: Mapped[str | None] = mapped_column(
        String(100), default=None, nullable=True, comment='The caller type that initiated this execution')
    execution_id: Mapped[str | None] = mapped_column(
        String(100), default=None, nullable=True, comment='the user id that runs this workflow')
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
        JSON, default=None, nullable=True, comment="workflows' components' execute info")
    agent_execution_detail_id: Mapped[int | None] = mapped_column(  # 如果本次workflow的执行由agent发起，则此值指向 agent_execution_details.id
        BigInteger,
        ForeignKey("agent_execution_details.id"),  # 数据库层面也做级联
        nullable=True,
        unique=True,                # 保证 1-to-1
        default=None,
        comment="link to agent_execution_details.id"
    )

    create_time: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), comment="更新时间")

    # 与workflow表关联
    workflow_draft: Mapped[WorkflowBaseDB] = relationship(
        "WorkflowBaseDB",
        primaryjoin=f"and_(WorkflowExecutionDB.workflow_version=='{DBFunBase.__version_none__}', WorkflowExecutionDB.workflow_id==WorkflowBaseDB.workflow_id, \
            WorkflowExecutionDB.workflow_version==WorkflowBaseDB.workflow_version)",
        foreign_keys=[workflow_id, workflow_version],
        back_populates="workflow_executions",
    )
    # 与workflow_publish表关联
    workflow_publish: Mapped[WorkflowPublishDB] = relationship(
        "WorkflowPublishDB",
        primaryjoin=f"and_(WorkflowExecutionDB.workflow_version!='{DBFunBase.__version_none__}', WorkflowExecutionDB.workflow_id==WorkflowPublishDB.workflow_id, \
            WorkflowExecutionDB.workflow_version==WorkflowPublishDB.workflow_version)",
        foreign_keys=[workflow_id, workflow_version],
        back_populates="workflow_executions",
    )
    # 与workflow_execution_details表关联
    workflow_execution_details_list: Mapped[list["WorkflowExecutionDetailsDB"]] = relationship(
        "WorkflowExecutionDetailsDB",
        foreign_keys="WorkflowExecutionDetailsDB.workflow_execution_id",
        back_populates="workflow_execution_summary",
        cascade="all, delete-orphan",        # ← 内存+数据库都会删
    )
    # 与agent_execution_details表的关联
    agent_execution_detail: Mapped["AgentExecutionDetailsDB | None"] = relationship(
        "AgentExecutionDetailsDB",
        foreign_keys=[agent_execution_detail_id],
        back_populates="workflow_execution",
    )

    # 通用父对象访问器
    def get_workflow(self):
        if self.workflow_version == DBFunBase.__version_none__:
            return self.workflow_draft
        else:
            return self.workflow_publish

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"workflow_id={self.workflow_id}, "
            f"workflow_version={self.workflow_version}, "
            f"trace_id='{self.trace_id}, "
            f"status={self.status}, "
            f"duration={self.duration}, "
            f"create_time='{self.create_time})>"
        )

# ==================== workflow_execution_details ====================


class WorkflowExecutionDetailsDB(Base, DBFunBase):
    __tablename__ = "workflow_execution_details"
    __table_args__ = {"comment": "某次workflow执行每个步骤的详细信息"}
    
    # 主键
    if settings.DB_TYPE.lower() == "sqlite":
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    else:
        id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 关联至workflow_execution的主键id
    workflow_execution_id: Mapped[int] = mapped_column(BigInteger, 
                                            ForeignKey("workflow_execution.id"),  # ← 数据库级联
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

    on_invoke_data: Mapped[list[dict]] = mapped_column(JSON, default=list, 
        comment='Intermediate process information used to record the execution time of the current component')

    component_id: Mapped[str] = mapped_column(String(100), default="")
    component_name: Mapped[str] = mapped_column(String(255), default="")
    component_type: Mapped[str] = mapped_column(String(100), default="")
    agent_parent_invoke_id: Mapped[str] = mapped_column(String(100), default="", 
        comment='Reserved field: nested workflows for future adaptation of workflow nodes')

    meta_data: Mapped[str | None] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), default=None)

    # loop 信息
    loop_node_id: Mapped[str | None] = mapped_column(String(100), default=None)
    loop_index: Mapped[int | None] = mapped_column(Integer, default=None)

    # 状态
    status: Mapped[str | None] = mapped_column(
        String(16), default=None, comment='finish/start/error/running/interrupted/unknown')

    # 模型数据，临时存储
    llm_invoke_data: Mapped[dict[str, dict]] = mapped_column(JSON, default=dict)

    # subworkflow
    parent_node_id: Mapped[str] = mapped_column(String(100), default="")
    # 未定义的字段保存于_rest_中
    _rest_: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)

    workflow_execution_summary: Mapped[WorkflowExecutionDB] = relationship(
        "WorkflowExecutionDB",
        foreign_keys=[workflow_execution_id],
        back_populates="workflow_execution_details_list",
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"workflow_execution_id='{self.workflow_execution_id}, "
            f"invoke_id={self.invoke_id}, "
            f"status='{self.status})>"
        )
    
