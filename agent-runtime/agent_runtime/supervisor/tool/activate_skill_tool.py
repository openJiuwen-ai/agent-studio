"""Stateless tool that activates a cataloged workspace Skill on demand."""

from openjiuwen.core.foundation.tool import Tool, ToolCard

from agent_runtime.supervisor.event.adapt import build_skill_activated
from agent_runtime.supervisor.event.channel import get_channel
from agent_runtime.supervisor.skill_artifact_cache import (
    SkillArtifactError,
    SkillInstructionsMissingError,
)
from agent_runtime.supervisor.skill_context import get_skill_context


class ActivateSkillTool(Tool):
    """Load only the selected Skill's instructions from the bound request catalog."""

    def __init__(self) -> None:
        super().__init__(
            card=ToolCard(
                id="conversation_activate_skill",
                name="activate_skill",
                description="按 Skill ID 加载当前工作空间 Skill 的完整 SKILL.md 指令",
                input_params={
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "目录中的 Skill ID"}
                    },
                    "required": ["skill_id"],
                    "additionalProperties": False,
                },
            )
        )

    async def invoke(self, inputs, **kwargs):
        if not isinstance(inputs, dict) or set(inputs) != {"skill_id"}:
            return self._error(
                "invalid_skill_activation_input", "activate_skill accepts only skill_id."
            )
        skill_id = inputs["skill_id"]
        context = get_skill_context()
        if context is None:
            return self._error("skill_context_unavailable", "Skill activation is unavailable in this execution.")
        if not isinstance(skill_id, str) or skill_id not in context.catalog_by_id:
            return self._error("skill_not_available", "The requested Skill is not available in this catalog.")

        skill = context.catalog_by_id[skill_id]
        try:
            instructions = await context.artifact_cache.load_instructions(skill)
        except SkillInstructionsMissingError:
            return self._error(
                "skill_instructions_missing",
                f"Skill {skill.skill_id} activation failed: SKILL.md is missing.",
            )
        except SkillArtifactError:
            return self._error(
                "skill_artifact_invalid",
                f"Skill {skill.skill_id} activation failed: archive rejected.",
            )
        except Exception:
            return self._error(
                "skill_download_failed",
                f"Skill {skill.skill_id} activation failed: artifact download failed.",
            )

        channel = get_channel()
        if channel is not None:
            try:
                await channel.emit(
                    build_skill_activated(
                        channel.execution_id, skill.skill_id, skill.name, skill.version_id
                    )
                )
            except Exception:
                # SSE 通道仅作实时透传；投递失败不能撤销已成功加载给 Agent 的指令。
                pass
        return {
            "skillId": skill.skill_id,
            "name": skill.name,
            "versionId": skill.version_id,
            "instructions": instructions,
        }

    async def stream(self, inputs, **kwargs):
        yield await self.invoke(inputs, **kwargs)

    @staticmethod
    def _error(code: str, message: str) -> dict:
        return {"error": {"code": code, "message": message}}
