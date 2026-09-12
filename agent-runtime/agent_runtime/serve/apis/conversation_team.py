# -*- coding: UTF-8 -*-
"""团队对话 API —— `/v1/conversation/team`（SSE 事件流）

独立 API（不耦合 /v1/orchestration/ir/execute）：
接收子 Agent IDs + 模型部署 ID（+ 多轮历史），引擎侧内置组装「监督者 + handoff 工具」并执行。
监督者系统提示词固定引擎侧（F4/用户决策 2026-08-11）：Java 不再传 systemPrompt。
子 Agent 通过其已有 IR 加载（OBS agent/ir/{agentId}/{agentId}.json）。

SSE 事件化（Phase 3）：产出结构化事件流（user_message/run_start/message/reasoning/tool_call/
tool_result/sub_start/sub_done/run_done/usage/error），暴露执行边界给前端与 Java 三表落库。
无 done 事件（SSE 流关闭即正常结束），error 用于异常。
"""

import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_runtime.supervisor.builder import build_supervisor, normalize_skill_inputs
from agent_runtime.supervisor.common.constants import TeamEventField
from agent_runtime.supervisor.event.adapt import build_error, build_run_start, build_user_message, sse_line
from agent_runtime.supervisor.runner import run_supervisor
from agent_runtime.supervisor.skill_model import SkillDescriptor
from agent_runtime.serve.apis.conversation_team_app import stream_application

team_router = APIRouter(tags=["conversation-team"])

logger = logging.getLogger(__name__)


class SkillCatalogItemReq(BaseModel):
    """Manager 在对话请求中下发的受信任 Skill 描述。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    skill_id: str = Field(alias="skillId")
    version_id: str = Field(alias="versionId")
    name: str
    description: str
    object_key: str = Field(alias="objectKey")

    @field_validator("skill_id", "version_id", "name", "description", "object_key")
    @classmethod
    def reject_blank_descriptor_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("skill descriptor fields must not be blank")
        return value


class ConversationTeamStreamingResponse(StreamingResponse):
    """Close this endpoint's async body in the Task that consumes SSE chunks."""

    async def stream_response(self, send) -> None:
        try:
            await super().stream_response(send)
        finally:
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                await close()


class ConversationTeamReq(BaseModel):
    """/v1/conversation/team 请求体"""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    conversation_id: str = Field(alias="conversationId")
    user_id: str = Field(default="anonymous", alias="userId")
    query: str
    select_type: str = Field(default="SUPERVISOR", alias="selectType")
    app_id: str | None = Field(default=None, alias="appId")
    sub_agent_ids: list[str] = Field(default_factory=list, alias="subAgentIds")
    model_deployment_id: str | None = Field(default=None, alias="modelDeploymentId")
    # 多轮历史（list[{role, content}]）：仅注入监督者上下文（方案 B），子 Agent 不感知（D0-3/用户决策 2026-08-11）
    conversation_history: list | None = Field(None, alias="conversationHistory")
    skill_catalog: list[SkillCatalogItemReq] = Field(default_factory=list, alias="skillCatalog")
    recommended_skill_ids: list[str] = Field(default_factory=list, alias="recommendedSkillIds")
    file_ids: list[dict[str, str]] = Field(default_factory=list, alias="fileIds")

    @model_validator(mode="before")
    @classmethod
    def reject_conflicting_aliases(cls, values):
        if not isinstance(values, dict):
            return values
        aliases = (
            ("conversationId", "conversation_id"),
            ("userId", "user_id"),
            ("subAgentIds", "sub_agent_ids"),
            ("modelDeploymentId", "model_deployment_id"),
            ("conversationHistory", "conversation_history"),
            ("skillCatalog", "skill_catalog"),
            ("recommendedSkillIds", "recommended_skill_ids"),
            ("fileIds", "file_ids"),
            ("selectType", "select_type"),
            ("appId", "app_id"),
        )
        if any(
            alias in values and field_name in values and values[alias] != values[field_name]
            for alias, field_name in aliases
        ):
            raise ValueError("conflicting request field aliases")
        return values

    @model_validator(mode="after")
    def validate_skill_catalog(self):
        catalog = [
            SkillDescriptor(
                skill_id=item.skill_id,
                version_id=item.version_id,
                name=item.name,
                description=item.description,
                object_key=item.object_key,
            )
            for item in self.skill_catalog
        ]
        _, self.recommended_skill_ids = normalize_skill_inputs(catalog, self.recommended_skill_ids)
        return self


async def team_sse_stream(req: ConversationTeamReq, execution_id: str | None = None):
    """SSE 事件生成器：先发 user_message/run_start，再跑监督者事件流。index 统一在此递增。

    execution_id 优先级：X-Execution-Id 头（Java 侧生成并提前落了 user 行，需回显保证
    user 行与 run/sub_run 行 execution_id 一致）> 引擎 uuid4 兜底（全量 uuid4，不用 conversation_id）。
    """
    if not execution_id:
        execution_id = str(uuid.uuid4())
    index = 0
    yield sse_line(build_user_message(execution_id, req.conversation_id, req.query, index=index))
    index += 1
    yield sse_line(build_run_start(execution_id, index=index))
    index += 1

    runner = None
    try:
        if req.select_type.upper() == "APP":
            runner = stream_application(req, execution_id)
        else:
            skill_catalog = [
                SkillDescriptor(
                    skill_id=item.skill_id,
                    version_id=item.version_id,
                    name=item.name,
                    description=item.description,
                    object_key=item.object_key,
                )
                for item in req.skill_catalog
            ]
            skill_catalog, recommended_skill_ids = normalize_skill_inputs(
                skill_catalog, req.recommended_skill_ids
            )
            agent = await build_supervisor(
                sub_agent_ids=req.sub_agent_ids,
                model_deployment_id=req.model_deployment_id,
                conversation_history=req.conversation_history,
                skill_catalog=skill_catalog,
                recommended_skill_ids=recommended_skill_ids,
                file_references=req.file_ids,
            )
            runner = run_supervisor(agent, req.query, req.conversation_id, execution_id)

        async for event in runner:
            event[TeamEventField.INDEX] = index  # 统一占序，覆盖增量事件自带 index
            index += 1
            yield sse_line(event)
    except Exception as e:
        logger.error(f"conversation/team build or app adapter failed: {e}", exc_info=True)
        yield sse_line(build_error(execution_id, code="build_failed", message=str(e), index=index))
    finally:
        if runner is not None:
            try:
                await runner.aclose()
            except Exception:
                pass


@team_router.post("/v1/conversation/team")
async def conversation_team(req: ConversationTeamReq, request: Request):
    """组装监督者 + N 个 handoff 工具，跑一轮团队对话，返回 SSE 事件流。"""
    if not req.query:
        return JSONResponse(status_code=400, content={"error": "query is required"})
    select_type = req.select_type.upper()
    if select_type not in {"SUPERVISOR", "APP"}:
        return JSONResponse(status_code=400, content={"error": "selectType must be SUPERVISOR or APP"})
    if select_type == "SUPERVISOR":
        if not req.sub_agent_ids:
            return JSONResponse(status_code=400, content={"error": "subAgentIds is required"})
        if not req.model_deployment_id:
            return JSONResponse(status_code=400, content={"error": "modelDeploymentId is required"})
        if req.app_id:
            return JSONResponse(status_code=400, content={"error": "appId is not allowed for SUPERVISOR"})
    else:
        if not req.app_id:
            return JSONResponse(status_code=400, content={"error": "appId is required"})
        if req.sub_agent_ids or req.model_deployment_id:
            return JSONResponse(status_code=400, content={"error": "Supervisor fields are not allowed for APP"})

    # Java 侧生成 execution_id 并经 X-Execution-Id 头下发（保证三表 execution_id 一致），缺省时引擎 uuid4 兜底
    execution_id = request.headers.get("x-execution-id")
    return ConversationTeamStreamingResponse(
        content=team_sse_stream(req, execution_id),
        media_type="text/event-stream",
    )
