import io
from types import SimpleNamespace
from unittest.mock import AsyncMock
import zipfile

import pytest

from agent_runtime.supervisor.event.channel import EventChannel, reset_channel, set_channel
from agent_runtime.supervisor.skill_artifact_cache import SkillArtifactCache, SkillArtifactError
from agent_runtime.supervisor.skill_context import (
    attach_agent_context,
    bind_agent_skill_context,
    reset_skill_context,
)
from agent_runtime.supervisor.skill_model import SkillDescriptor
from agent_runtime.supervisor.tool.activate_skill_tool import ActivateSkillTool


def descriptor(skill_id, version_id, name, description):
    return SkillDescriptor(
        skill_id=skill_id,
        version_id=version_id,
        name=name,
        description=description,
        object_key=f"user/skills/{skill_id}/{version_id}/{name}.zip",
    )


@pytest.mark.asyncio
async def test_activate_returns_instructions_and_emits_event():
    cache = AsyncMock()
    cache.load_instructions.return_value = "完整技能指令"
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    skill_token = bind_agent_skill_context(agent)
    channel = EventChannel("exec-1")
    event_token = set_channel(channel)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
        event = await channel.get()
    finally:
        reset_channel(event_token)
        reset_skill_context(skill_token)

    assert result == {
        "skillId": "s1",
        "name": "会议纪要",
        "versionId": "v1",
        "instructions": "完整技能指令",
    }
    assert event["event"] == "skill_activated"
    assert event["data"] == {"skillId": "s1", "name": "会议纪要", "versionId": "v1"}
    assert "objectKey" not in event["data"]


@pytest.mark.asyncio
async def test_activate_rejects_id_outside_current_catalog():
    agent = SimpleNamespace()
    attach_agent_context(agent, [], [], AsyncMock())
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "other"})
    finally:
        reset_skill_context(token)

    assert result["error"]["code"] == "skill_not_available"


@pytest.mark.asyncio
@pytest.mark.parametrize(("error", "code"), [
    (RuntimeError("storage unavailable"), "skill_download_failed"),
    (SkillArtifactError("invalid skill archive"), "skill_artifact_invalid"),
])
async def test_activate_returns_stable_cache_failure_codes_without_storage_details(error, code):
    cache = AsyncMock()
    cache.load_instructions.side_effect = error
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_skill_context(token)

    assert result["error"]["code"] == code
    assert "user/skills/" not in result["error"]["message"]


def skill_archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return output.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    skill_archive({"s1/SKILL.md": b"\xff"}),
    skill_archive({"one/SKILL.md": b"one", "two/SKILL.md": b"two"}),
])
async def test_activate_classifies_real_cache_utf8_or_structure_failures_as_invalid(tmp_path, payload):
    skill = descriptor("s1", "v1", "会议纪要", "整理会议")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))
    agent = SimpleNamespace()
    attach_agent_context(agent, [skill], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_skill_context(token)

    assert result["error"] == {
        "code": "skill_artifact_invalid",
        "message": "Skill s1 activation failed: archive rejected.",
    }


@pytest.mark.asyncio
async def test_activate_classifies_real_cache_missing_root_instructions_by_exception_type(tmp_path):
    skill = descriptor("s1", "v1", "会议纪要", "整理会议")
    cache = SkillArtifactCache(
        tmp_path,
        downloader=AsyncMock(return_value=skill_archive({"s1/README.md": b"no instructions"})),
    )
    agent = SimpleNamespace()
    attach_agent_context(agent, [skill], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_skill_context(token)

    assert result["error"] == {
        "code": "skill_instructions_missing",
        "message": "Skill s1 activation failed: SKILL.md is missing.",
    }


@pytest.mark.asyncio
async def test_activate_classifies_real_cached_skill_markdown_read_failure_as_invalid(tmp_path):
    skill = descriptor("s1", "v1", "会议纪要", "整理会议")
    cache_dir = tmp_path / skill.cache_key
    cache_dir.mkdir()
    (cache_dir / "SKILL.md").write_bytes(b"\xff")
    downloader = AsyncMock()
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    agent = SimpleNamespace()
    attach_agent_context(agent, [skill], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_skill_context(token)

    assert result["error"]["code"] == "skill_artifact_invalid"
    downloader.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_key", ["objectKey", "versionId", "unexpected"])
async def test_activate_rejects_extra_input_keys_without_loading_artifact(extra_key):
    cache = AsyncMock()
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1", extra_key: "untrusted"})
    finally:
        reset_skill_context(token)

    assert result == {
        "error": {
            "code": "invalid_skill_activation_input",
            "message": "activate_skill accepts only skill_id.",
        }
    }
    cache.load_instructions.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_succeeds_without_an_event_channel():
    cache = AsyncMock()
    cache.load_instructions.return_value = "完整技能指令"
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    token = bind_agent_skill_context(agent)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_skill_context(token)

    assert result["instructions"] == "完整技能指令"


@pytest.mark.asyncio
async def test_activate_keeps_success_result_when_event_delivery_fails():
    class FailingChannel:
        execution_id = "exec-1"

        async def emit(self, event):
            raise RuntimeError("event transport secret")

    cache = AsyncMock()
    cache.load_instructions.return_value = "完整技能指令"
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    skill_token = bind_agent_skill_context(agent)
    event_token = set_channel(FailingChannel())
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_channel(event_token)
        reset_skill_context(skill_token)

    assert result["instructions"] == "完整技能指令"


@pytest.mark.asyncio
async def test_activate_failure_does_not_emit_success_event():
    cache = AsyncMock()
    cache.load_instructions.side_effect = SkillArtifactError("invalid skill archive")
    channel = SimpleNamespace(execution_id="exec-1", emit=AsyncMock())
    agent = SimpleNamespace()
    attach_agent_context(agent, [descriptor("s1", "v1", "会议纪要", "整理会议")], [], cache)
    skill_token = bind_agent_skill_context(agent)
    event_token = set_channel(channel)
    try:
        result = await ActivateSkillTool().invoke({"skill_id": "s1"})
    finally:
        reset_channel(event_token)
        reset_skill_context(skill_token)

    assert result["error"]["code"] == "skill_artifact_invalid"
    channel.emit.assert_not_awaited()


def test_activate_tool_card_accepts_only_skill_id():
    card = ActivateSkillTool().card

    assert card.id == "conversation_activate_skill"
    assert card.name == "activate_skill"
    assert card.input_params == {
        "type": "object",
        "properties": {"skill_id": {"type": "string", "description": "目录中的 Skill ID"}},
        "required": ["skill_id"],
        "additionalProperties": False,
    }
