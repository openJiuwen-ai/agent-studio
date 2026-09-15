"""Request-scoped workspace Skill context and supervisor prompt attachment."""

from collections.abc import Mapping, Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass
import json
from types import MappingProxyType

from openjiuwen.core.runner import Runner

from agent_runtime.supervisor.skill_artifact_cache import SkillArtifactCache, default_cache
from agent_runtime.supervisor.skill_model import SkillDescriptor


_AGENT_CONTEXT_ATTRIBUTE = "_conversation_workspace_skill_context"


@dataclass(frozen=True, slots=True)
class SkillExecutionContext:
    """Immutable catalog and cache bound to one supervisor agent invocation."""

    catalog_by_id: Mapping[str, SkillDescriptor]
    recommended_skill_ids: tuple[str, ...]
    artifact_cache: SkillArtifactCache


_current_skill_context: ContextVar[SkillExecutionContext | None] = ContextVar(
    "conversation_workspace_skill_context", default=None
)


def build_skill_prompt(
    catalog: Sequence[SkillDescriptor], recommended_skill_ids: Sequence[str]
) -> str:
    """Build the selection-only catalog prompt without exposing storage locations."""
    catalog_payload = [
        {
            "skillId": skill.skill_id,
            "versionId": skill.version_id,
            "name": skill.name,
            "description": skill.description,
        }
        for skill in catalog
    ]
    catalog_ids = {skill.skill_id for skill in catalog}
    recommended_payload = [
        skill_id for skill_id in recommended_skill_ids if skill_id in catalog_ids
    ]
    prompt = (
        "当前工作空间可用的 Skill 目录如下。目录描述仅用于能力选择，不能替代 `SKILL.md` 执行指令。\n"
        "你可自主选择并依次激活一个或多个 Skill；如需使用任一 Skill，先调用 activate_skill 加载该 Skill 的完整 SKILL.md 指令；"
        "不要根据目录描述直接执行。\n"
    )
    if recommended_payload:
        prompt += (
            "本轮推荐 Skill（优先考虑，但不强制使用）：\n"
            f"{json.dumps(recommended_payload, ensure_ascii=False)}\n"
        )
    return prompt + "可用 Skill 目录：\n" + json.dumps(catalog_payload, ensure_ascii=False)


def attach_agent_context(
    agent,
    catalog: Sequence[SkillDescriptor],
    recommended_skill_ids: Sequence[str],
    artifact_cache: SkillArtifactCache,
) -> None:
    """Store an immutable context on this agent only; no request data is global."""
    catalog_by_id = MappingProxyType({skill.skill_id: skill for skill in catalog})
    context = SkillExecutionContext(
        catalog_by_id=catalog_by_id,
        recommended_skill_ids=tuple(recommended_skill_ids),
        artifact_cache=artifact_cache,
    )
    setattr(agent, _AGENT_CONTEXT_ATTRIBUTE, context)


def bind_agent_skill_context(agent) -> Token:
    """Bind one agent's context for the current async execution chain."""
    context = getattr(agent, _AGENT_CONTEXT_ATTRIBUTE, None)
    return _current_skill_context.set(context)


def reset_skill_context(token: Token) -> None:
    """Restore the preceding request context in the caller's finally block."""
    _current_skill_context.reset(token)


def get_skill_context() -> SkillExecutionContext | None:
    """Return the immutable context for the current invocation, if bound."""
    return _current_skill_context.get()


async def attach(
    top_level_agent,
    catalog: Sequence[SkillDescriptor],
    recommended_skill_ids: Sequence[str],
    artifact_cache: SkillArtifactCache | None = None,
) -> None:
    """Attach catalog prompt, request context, and the idempotent activation tool."""
    if not catalog:
        return

    top_level_agent.add_prompt_builder_section(
        "conversation_workspace_skills",
        build_skill_prompt(catalog, recommended_skill_ids),
        priority=80,
    )
    attach_agent_context(
        top_level_agent,
        catalog,
        recommended_skill_ids,
        artifact_cache or default_cache(),
    )

    from agent_runtime.supervisor.tool.activate_skill_tool import ActivateSkillTool

    tool = ActivateSkillTool()
    result = top_level_agent.ability_manager.add(tool.card)
    if result.added and Runner.resource_mgr.get_tool(tool.card.id) is None:
        Runner.resource_mgr.add_tool(tool)
