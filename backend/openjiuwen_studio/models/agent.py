from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy import (JSON, BigInteger, ForeignKey, String, UniqueConstraint,
                        and_, func, select, Integer)
from sqlalchemy.orm import (Mapped, declarative_mixin, foreign, mapped_column,
                            relationship)

from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from openjiuwen_studio.ops.config import settings

if TYPE_CHECKING:
    pass


class AgentModelConfig(BaseModel):
    """Agent模型配置参数封装"""
    timeout: int = Field(default=300)
    temperature: float = Field(default=0.7)
    top_p: float = Field(default=0.9)
    # 配置类必加，禁止传入未定义的字段，防传参错误
    model_config = {"extra": "forbid"}


@declarative_mixin
class AgentDBMixin:
    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        primary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    space_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    edit_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_template_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    auto_generated_prompt: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    opening_remarks: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    default_response: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    configs: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    plugins: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    workflows: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_model_config: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    prompt_template: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    constraint: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    prompt_tuning: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    triggers: Mapped[List[str] | None] = mapped_column(JSON, nullable=True)
    knowledge: Mapped[List[str] | None] = mapped_column(JSON, nullable=True)
    memory: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    _rest_: Mapped[Dict | None] = mapped_column(JSON, nullable=True)
    create_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


# -------------------- 具体表 --------------------
class AgentBaseDB(AgentDBMixin, Base, DBFunBase):
    __tablename__ = "agent"
    __table_args__ = (
        UniqueConstraint("agent_id", "agent_version", name="uix_agent_id_version"),
    )
    agent_id: Mapped[str] = mapped_column(String(100), index=True, unique=True, nullable=False)
    agent_version: Mapped[str | None] = mapped_column(String(100), default=DBFunBase.__version_none__, nullable=True)
    latest_publish_time: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True)
    latest_publish_version: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True)

    agent_executions: Mapped[list["AgentExecutionDB"]] = relationship(
        "AgentExecutionDB",
        primaryjoin=f"and_(AgentExecutionDB.agent_version=='{DBFunBase.__version_none__}', AgentExecutionDB.agent_id==AgentBaseDB.agent_id, \
            AgentExecutionDB.agent_version==AgentBaseDB.agent_version)",
        foreign_keys="[AgentExecutionDB.agent_id, AgentExecutionDB.agent_version]",
        cascade="all, delete-orphan",
        back_populates="agent_draft"
    )

    prompts: Mapped[list["PromptRelationDB"]] = relationship(
        "PromptRelationDB",
        primaryjoin=f"and_(PromptRelationDB.version=='{DBFunBase.__version_none__}', PromptRelationDB.type=='AGENT',\
            PromptRelationDB.id==AgentBaseDB.agent_id, PromptRelationDB.version==AgentBaseDB.agent_version)",
        foreign_keys="[PromptRelationDB.id, PromptRelationDB.version]",
        cascade="all, delete-orphan",
        back_populates="agent_draft"
    )

    # 所有发布版本的agent
    agent_publish_list: Mapped[list[AgentPublishDB]] = relationship(
        "AgentPublishDB",
        foreign_keys="AgentPublishDB.agent_id",
        back_populates="agent_draft",
        cascade="all, delete-orphan",        # ← 内存+数据库都会删
    )

    # 延迟加载最新的发布版本agent
    latest_publish_agent: Mapped[AgentPublishDB | None] = relationship(
        "AgentPublishDB",
        primaryjoin=lambda: and_(
            AgentBaseDB.agent_id == foreign(AgentPublishDB.agent_id),
            AgentPublishDB.primary_id == (
                select(func.max(AgentPublishDB.primary_id))
                .where(AgentPublishDB.agent_id == AgentBaseDB.agent_id)
                .correlate(AgentBaseDB)
                .scalar_subquery()
            )
        ),
        uselist=False,          # 只返回一条或 None
        viewonly=True,          # 只读，不会持久化
        lazy="select",          # 默认延迟加载，想预加载改成 joined / selectin
    )

    agent_workflow_relations: Mapped[list["AgentWorkflowRelationDB"]] = relationship(
        "AgentWorkflowRelationDB",
        primaryjoin=f"and_(AgentWorkflowRelationDB.agent_version=='{DBFunBase.__version_none__}', AgentWorkflowRelationDB.agent_id==AgentBaseDB.agent_id, \
            AgentWorkflowRelationDB.agent_version==AgentBaseDB.agent_version)",
        foreign_keys="[AgentWorkflowRelationDB.agent_id, AgentWorkflowRelationDB.agent_version]",
        cascade="all, delete-orphan",
        back_populates="agent_draft"
    )

    def update_agent_latest_publish_version(self):
        latest_publish = self.latest_publish_agent
        if latest_publish:
            self.latest_publish_time = latest_publish.create_time
            self.latest_publish_version = latest_publish.agent_version
        else:
            self.latest_publish_time = None
            self.latest_publish_version = None
        self.update_time = milliseconds()

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"agent_id={self.agent_id}, "
            f"agent_version={self.agent_version}, "
            f"agent_name='{self.agent_name}', "
            f"agent_type={self.agent_type})>"
        )


class AgentPublishDB(AgentDBMixin, Base, DBFunBase):
    __tablename__ = "agent_publish"
    __table_args__ = (
        UniqueConstraint("agent_id", "agent_version", name="uix_agent_id_version"),
    )
    agent_id: Mapped[str] = mapped_column(String(100),
                                    ForeignKey("agent.agent_id"),  
                                    nullable=False,
                                    index=True,
                                    )
    agent_version: Mapped[str] = mapped_column(String(100), nullable=False)
    version_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    agent_draft: Mapped[AgentBaseDB] = relationship(
        "AgentBaseDB",
        foreign_keys=agent_id,
        back_populates="agent_publish_list",
    )

    agent_executions: Mapped[list["AgentExecutionDB"]] = relationship(
        "AgentExecutionDB",
        primaryjoin=f"and_(AgentExecutionDB.agent_version!='{DBFunBase.__version_none__}', AgentExecutionDB.agent_id==AgentPublishDB.agent_id, \
            AgentExecutionDB.agent_version==AgentPublishDB.agent_version)",
        foreign_keys="[AgentExecutionDB.agent_id, AgentExecutionDB.agent_version]",
        cascade="all, delete-orphan",
        back_populates="agent_publish"
    )

    prompts: Mapped[list["PromptRelationDB"]] = relationship(
        "PromptRelationDB",
        primaryjoin=f"and_(PromptRelationDB.version!='{DBFunBase.__version_none__}', PromptRelationDB.type=='AGENT',\
            PromptRelationDB.id==AgentPublishDB.agent_id, PromptRelationDB.version==AgentPublishDB.agent_version)",
        foreign_keys="[PromptRelationDB.id, PromptRelationDB.version]",
        cascade="all, delete-orphan",
        back_populates="agent_publish"
    )

    agent_workflow_relations: Mapped[list["AgentWorkflowRelationDB"]] = relationship(
        "AgentWorkflowRelationDB",
        primaryjoin=f"and_(AgentWorkflowRelationDB.agent_version!='{DBFunBase.__version_none__}', AgentWorkflowRelationDB.agent_id==AgentPublishDB.agent_id, \
            AgentWorkflowRelationDB.agent_version==AgentPublishDB.agent_version)",
        foreign_keys="[AgentWorkflowRelationDB.agent_id, AgentWorkflowRelationDB.agent_version]",
        cascade="all, delete-orphan",
        back_populates="agent_publish"
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"agent_id={self.agent_id}, "
            f"agent_version={self.agent_version}, "
            f"agent_name='{self.agent_name}', "
            f"agent_type={self.agent_type})>"
        )


AgentBaseDBPd = AgentBaseDB.sqlalchemy_to_pydantic(exclude={"primary_id", })
AgentPublishDBPd = AgentPublishDB.sqlalchemy_to_pydantic(exclude={"primary_id", })


class AgentQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    agent_id: str = Field(..., alias="id", min_length=1, max_length=100)
    agent_version: Optional[str] = Field(None, alias="version", max_length=100)

