"""
Trace Summary Pydantic 模型

基于设计文档: TRACE_SUMMARY_SCHEMA.md
用于workflow和agent执行摘要的数据验证
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TraceSummary(BaseModel):
    """Trace Summary 模型"""
    space_id: str = Field(..., max_length=100)
    business_id: str = Field(..., max_length=100)
    business_type: str = Field(..., max_length=20)
    business_version: Optional[str] = Field(None, max_length=100)
    trace_id: str = Field(..., max_length=100)
    mode: int = Field(..., description="执行模式：0-调试运行，1-发布运行，2-节点调试")
    call_type: Optional[str] = Field(None, max_length=100)
    duration: Optional[int] = Field(None, description="执行时长（毫秒）")
    inputs: Optional[Dict[str, Any]] = Field(None)
    outputs: Optional[Dict[str, Any]] = Field(None)
    error_code: Optional[int] = Field(None)
    fail_reason: Optional[str] = Field(None)
    input_tokens: Optional[int] = Field(None)
    output_tokens: Optional[int] = Field(None)
    execute_info_list: Optional[List[Dict[str, Any]]] = Field(None)
    create_time: Optional[datetime] = Field(None)
    update_time: Optional[datetime] = Field(None)
    status: Optional[str] = Field(None, max_length=16)

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class TraceSummaryListRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: Optional[str] = Field(default=None, alias="spaceId", validation_alias=AliasChoices("spaceId", "space_id"))
    business_id: str = Field(alias="businessId", validation_alias=AliasChoices("businessId", "business_id"))
    business_type: str = Field(alias="businessType", validation_alias=AliasChoices("businessType", "business_type"))


class TraceSummaryByTraceIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: Optional[str] = Field(default=None, alias="spaceId", validation_alias=AliasChoices("spaceId", "space_id"))
    trace_id: str = Field(alias="traceId", validation_alias=AliasChoices("traceId", "trace_id"))


class TraceSummaryLatestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: Optional[str] = Field(default=None, alias="spaceId", validation_alias=AliasChoices("spaceId", "space_id"))
    business_id: str = Field(alias="businessId", validation_alias=AliasChoices("businessId", "business_id"))
    business_type: str = Field(alias="businessType", validation_alias=AliasChoices("businessType", "business_type"))


class TraceSummaryBrief(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId", validation_alias=AliasChoices("traceId", "trace_id"))
    create_time: Optional[datetime] = Field(default=None, alias="createTime",
                                            validation_alias=AliasChoices("createTime", "create_time"))


class TraceSummaryListBySpaceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    space_id: str = Field(alias="spaceId", validation_alias=AliasChoices("spaceId", "space_id"))
    business_type: Optional[str] = Field(default=None, alias="businessType",
                                         validation_alias=AliasChoices("businessType", "business_type"))
    limit: int = Field(default=50, ge=1, le=200)


class TraceSummaryBriefWithStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    trace_id: str = Field(alias="traceId", validation_alias=AliasChoices("traceId", "trace_id"))
    business_id: str = Field(alias="businessId", validation_alias=AliasChoices("businessId", "business_id"))
    business_name: Optional[str] = Field(default=None, alias="businessName",
                                         validation_alias=AliasChoices("businessName", "business_name"))
    business_version: Optional[str] = Field(default=None, alias="businessVersion",
                                            validation_alias=AliasChoices("businessVersion", "business_version"))
    business_type: str = Field(alias="businessType", validation_alias=AliasChoices("businessType", "business_type"))
    create_time: Optional[datetime] = Field(default=None, alias="createTime",
                                            validation_alias=AliasChoices("createTime", "create_time"))
    duration: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)


class ActiveExecutionInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conversation_id: str = Field(alias="conversationId",
                                 validation_alias=AliasChoices("conversationId", "conversation_id"))
    workflow_id: str = Field(alias="workflowId", validation_alias=AliasChoices("workflowId", "workflow_id"))
    workflow_name: Optional[str] = Field(default=None, alias="workflowName",
                                         validation_alias=AliasChoices("workflowName", "workflow_name"))
    workflow_version: str = Field(alias="workflowVersion",
                                  validation_alias=AliasChoices("workflowVersion", "workflow_version"))
    space_id: str = Field(alias="spaceId", validation_alias=AliasChoices("spaceId", "space_id"))
    start_time: Optional[float] = Field(default=None, alias="startTime",
                                        validation_alias=AliasChoices("startTime", "start_time"))
