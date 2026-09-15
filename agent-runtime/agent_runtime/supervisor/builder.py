# -*- coding: UTF-8 -*-
"""监督者组装器 —— 给定子 Agent IDs，为每个构建 handoff 工具，组装监督者 ReActAgent。

监督者 = openjiuwen ReActAgent（system_prompt 固定引擎侧，F4：Java 不传）+ N 个 HandoffTool。
子 Agent 由 HandoffTool.invoke 按需加载其已有 IR 执行（见 tool/handoff_tool.py）。

工具注册采用公开 API + 幂等（swarm 模板，D0-4）：ability_manager.add(card) 成功后才检查
resource_mgr 是否已有同 id 实例，不存在才注册。工具无状态、跨会话共享安全，数量有界。

运行（事件生成器 run_supervisor）在 runner.py —— build（组装）与 run（运行）职责分离。
"""

from pathlib import PureWindowsPath
import re

from openjiuwen.core.runner import Runner
from openjiuwen.core.single_agent.agents.react_agent import ReActAgent
from openjiuwen.core.single_agent.schema.agent_card import AgentCard

from agent_runtime.supervisor.config import build_react_config, format_conversation_history
from agent_runtime.supervisor.skill_context import attach as attach_skill_context
from agent_runtime.supervisor.skill_model import SkillDescriptor
from agent_runtime.supervisor.tool.handoff_tool import HandoffTool
from agent_runtime.runner.react_file_reader_adapter import ReactFileReaderAdapter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load

# 监督者系统提示词固定引擎侧（F4/用户决策 2026-08-11）：请求不再含 systemPrompt，Java 不传。
# 核心约束（方案 B）：监督者是任务分派者，必须把完成任务所需信息写足在 handoff query 里；
# 子 Agent 纯无状态单任务执行、不感知对话历史。
SUPERVISOR_SYSTEM_PROMPT = (
    "你是团队监督者，负责把用户请求分派给最合适的子 Agent 处理。"
    "移交任务时，你必须把完成任务所需的全部上下文信息完整写入 query 参数，"
    "确保子 Agent 无需任何外部信息即可直接执行。"
    "若无法匹配任何子 Agent，直接告知用户并提供建议。"
)


def _ir_path(agent_id: str) -> str:
    return f"agent/ir/{agent_id}/{agent_id}.json"


def normalize_skill_inputs(
    skill_catalog: list[SkillDescriptor] | None,
    recommended_skill_ids: list[str] | None,
) -> tuple[list[SkillDescriptor], list[str]]:
    """Validate the Manager catalog and normalize recommendations for all call paths.

    This repeats task 3's object-key acceptance semantics at the request boundary without
    importing its private cache validator: object keys are relative POSIX paths and must
    contain the descriptor's ``skills/{skill_id}/{version_id}`` identity path.
    """
    catalog = list(skill_catalog or [])
    seen_ids: set[str] = set()
    for skill in catalog:
        if not isinstance(skill, SkillDescriptor):
            raise ValueError("skill catalog entries must be SkillDescriptor instances")
        values = (skill.skill_id, skill.version_id, skill.name, skill.description, skill.object_key)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("skill catalog descriptor fields must not be blank")
        if skill.skill_id in seen_ids:
            raise ValueError(f"duplicate skill ID in catalog: {skill.skill_id}")
        seen_ids.add(skill.skill_id)
        _validate_skill_object_key(skill)

    recommended: list[str] = []
    for skill_id in recommended_skill_ids or []:
        if not isinstance(skill_id, str) or not skill_id.strip():
            raise ValueError("recommended skill IDs must not be blank")
        if skill_id not in seen_ids:
            raise ValueError(f"recommended skill IDs are not present in the catalog: {skill_id}")
        if skill_id not in recommended:
            recommended.append(skill_id)
    return catalog, recommended


def _validate_skill_object_key(skill: SkillDescriptor) -> None:
    """Mirror task 3's object-key boundary checks before a Skill reaches a prompt."""
    key = skill.object_key
    if "\\" in key or key.startswith("/") or PureWindowsPath(key).is_absolute() or re.match(r"^[A-Za-z]:", key):
        raise ValueError("unsafe skill object key")
    parts = key.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        raise ValueError("unsafe skill object key")
    if any(any(ord(character) < 32 or ord(character) == 127 for character in part) for part in parts):
        raise ValueError("unsafe skill object key")
    identity = (skill.skill_id, skill.version_id)
    if any("/" in value or "\\" in value for value in identity):
        raise ValueError("unsafe skill object key")
    expected = ("skills", *identity)
    if not any(tuple(parts[index : index + 3]) == expected for index in range(len(parts) - 2)):
        raise ValueError("unsafe skill object key")


async def _load_sub_agent_description(agent_id: str) -> str:
    """从子 Agent 已有 IR 读取描述，用于 handoff 工具的卡片描述。"""
    try:
        ir_data = await async_ir_load(_ir_path(agent_id))
        return (
            ir_data.get("description")
            or ir_data.get("agentName")
            or f"将任务移交给子 Agent {agent_id} 处理"
        )
    except Exception:
        return f"将任务移交给子 Agent {agent_id} 处理"


def format_file_references(file_references: list[dict] | None) -> str:
    """Format this turn's uploaded files for the supervisor without inlining content."""
    if not file_references:
        return ""
    lines = [
        "\n\n## 本轮上传文件",
        "以下文件由用户在本轮上传。文件名用于识别文件主题；只有在任务需要时才调用 read_file_from_url，且必须使用清单中的完整 URL。",
    ]
    for item in file_references:
        file_name = str(item.get("fileName") or item.get("file_name") or "未命名文件")
        url = str(item.get("url") or "")
        if url:
            lines.append(f"- **{file_name}**: {url}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _register_file_reader(agent: ReActAgent) -> None:
    """Register the existing URL file reader for this request only."""
    reader = ReactFileReaderAdapter()
    result = agent.ability_manager.add(reader.card)
    if result.added:
        existing = Runner.resource_mgr.get_tool(reader.card.id)
        if existing is None:
            Runner.resource_mgr.add_tool(reader)


async def build_supervisor(
    sub_agent_ids: list,
    model_deployment_id: str,
    conversation_history: list | None = None,
    skill_catalog: list[SkillDescriptor] | None = None,
    recommended_skill_ids: list[str] | None = None,
    file_references: list[dict] | None = None,
) -> ReActAgent:
    """按 sub_agent_ids 动态构建 N 个 handoff 工具，组装监督者 ReActAgent。

    Args:
        sub_agent_ids: 子 Agent IDs（已注册 Agent）
        model_deployment_id: 监督者模型部署 id（非模型名；路由解析成真实模型名，D0-8）
        conversation_history: 多轮历史 list[{role, content}]，仅注入监督者上下文（方案 B），子 Agent 不感知
        skill_catalog: Manager 下发的本轮工作空间 Skill 目录
        recommended_skill_ids: 目录内的推荐 Skill ID

    Returns:
        已配置并注册工具的监督者 ReActAgent
    """
    skill_catalog, recommended_skill_ids = normalize_skill_inputs(
        skill_catalog, recommended_skill_ids
    )

    tools = []
    for agent_id in sub_agent_ids:
        description = await _load_sub_agent_description(agent_id)
        # 工具名 = transfer_to_{agentId[:8]}（HandoffTool 内生成，ASCII 短唯一；路由靠 description）
        tool = HandoffTool(
            agent_id=agent_id,
            description=description,
        )
        tools.append(tool)

    # 监督者提示词 = 引擎侧固定角色/指令 + 历史段 + 本轮附件元信息
    system_prompt = (
        SUPERVISOR_SYSTEM_PROMPT
        + format_conversation_history(conversation_history)
        + format_file_references(file_references)
    )

    agent = ReActAgent(
        card=AgentCard(
            id="conversation_team_supervisor",
            name="Team Supervisor",
            description="团队监督者，负责把任务分派给最合适的子 Agent",
        )
    )
    agent.configure(build_react_config(system_prompt, model_deployment_id))
    await attach_skill_context(agent, skill_catalog, recommended_skill_ids)
    if file_references:
        _register_file_reader(agent)

    # 注册工具：公开 API + 幂等（swarm 模板），不再直插私有 _tools 字段
    for tool in tools:
        result = agent.ability_manager.add(tool.card)
        if result.added:
            existing = Runner.resource_mgr.get_tool(tool.card.id)
            if existing is None:
                Runner.resource_mgr.add_tool(tool)

    return agent
