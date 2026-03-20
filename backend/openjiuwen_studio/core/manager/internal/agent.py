from typing import Optional, Any

from pydantic import Field, BaseModel, ConfigDict

from openjiuwen_studio.models.agent import AgentBaseDBPd
from openjiuwen_studio.schemas.agent import AGENT_NAME_MAX_SIZE


class AgentWorkflowInputNode(BaseModel):
    type: str
    description: str
    required: bool


class AgentWorkflowInputs(BaseModel):
    type: Optional[str] = Field("")
    properties: dict[str, AgentWorkflowInputNode] = Field(default_factory=dict)


class AgentWorkflowListNodeBase(BaseModel):
    workflow_id: str = Field(..., min_length=1, max_length=100, alias="id")
    workflow_version: str = Field(..., min_length=1, max_length=100, alias="version")
    workflow_name: str = Field(..., min_length=1, max_length=255, alias="name")
    description: str = Field(..., min_length=1, max_length=500, alias="desc")

    class Config:
        populate_by_name = True


class AgentWorkflowListNode(AgentWorkflowListNodeBase):
    pass


class AgentModelListNode(BaseModel):
    api_key: str = Field("")
    api_base: str = Field("")
    model_provider: str = Field("", min_length=1, max_length=100)
    model_id: int = Field(..., ge=0, le=999999, alias="id")
    model_name: str = Field(..., min_length=1, max_length=100, alias="name")
    model_type: str = Field(..., min_length=1, max_length=100, alias="type")
    temperature: float = Field(..., ge=0.0, le=2.0)
    top_p: float = Field(..., ge=0.0, le=1.0)
    streaming: bool = Field(False)
    max_tokens: int = Field(..., ge=1)
    timeout: int = Field(..., ge=1)

    class Config:
        populate_by_name = True


class AgentOptionInfo(BaseModel):
    workflow_list: list[AgentWorkflowListNode] = Field(default_factory=list)
    model_list: list[AgentModelListNode] = Field(default_factory=list)


class SingleAgentData(BaseModel):
    agent_info: AgentBaseDBPd = Field(description="agent基础信息")
    agent_option_info: AgentOptionInfo = Field(description="agent可选项信息")


class AgentItem(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100, alias="id")
    agent_name: str = Field(..., min_length=1, max_length=AGENT_NAME_MAX_SIZE, alias="name")
    agent_version: str = Field(..., min_length=1, max_length=100, alias="version")
    agent_type: str = Field(..., min_length=1, max_length=30, alias="type")
    description: str = Field(..., min_length=1, max_length=500, alias="desc")
    icon: str = Field(..., min_length=1, max_length=100)
    status: str = Field(..., min_length=1, max_length=100)
    model_name: str = Field(..., min_length=1, max_length=100)
    last_activate: str = Field(..., min_length=1, max_length=100)
    usage_count: int = Field(..., description="用户使用的次数")
    tags: list[str] = Field(default_factory=list)
    create_time: int
    update_time: int
    api_endpoint: str = Field(..., min_length=1, max_length=100)
    published_flag: str = Field(..., min_length=1, max_length=100, description="agent发布状态")

    class Config:
        populate_by_name = True


class AgentListPagination(BaseModel):
    page: int = Field(..., ge=0, le=1000)
    page_size: int = Field(..., ge=0, le=1000)
    total: int = Field(..., ge=0, le=1000)
    total_pages: int = Field(..., ge=0, le=1000)


class AgentListInfo(BaseModel):
    agent_items: list[AgentItem] = Field(default_factory=list, description="agent列表信息")
    pagination: AgentListPagination
