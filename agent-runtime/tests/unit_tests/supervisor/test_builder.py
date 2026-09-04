from unittest.mock import AsyncMock

import pytest

from agent_runtime.supervisor.builder import build_supervisor, format_file_references
from agent_runtime.supervisor.skill_model import SkillDescriptor


def test_format_file_references_includes_file_name_and_url_without_content():
    prompt = format_file_references([{
        "fileName": "report.pdf",
        "url": "https://files.test/report.pdf",
    }])

    assert "report.pdf" in prompt
    assert "https://files.test/report.pdf" in prompt
    assert "文件全文" not in prompt


def descriptor_dict(skill_id):
    return {
        "skill_id": skill_id,
        "version_id": "v1",
        "name": f"name-{skill_id}",
        "description": f"description-{skill_id}",
        "object_key": f"user/skills/{skill_id}/v1/{skill_id}.zip",
    }


@pytest.mark.asyncio
async def test_build_supervisor_attaches_skills_only_to_returned_top_level(monkeypatch):
    class FakeAgent:
        def __init__(self, card):
            self.card = card

        def configure(self, _config):
            pass

    attach = AsyncMock()
    monkeypatch.setattr("agent_runtime.supervisor.builder.attach_skill_context", attach)
    monkeypatch.setattr("agent_runtime.supervisor.builder.build_react_config", lambda *_args: object())
    monkeypatch.setattr("agent_runtime.supervisor.builder.ReActAgent", FakeAgent)

    agent = await build_supervisor(
        [],
        "m1",
        skill_catalog=[SkillDescriptor(**descriptor_dict("s1"))],
        recommended_skill_ids=["s1"],
    )

    assert agent.card.id == "conversation_team_supervisor"
    attach.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_supervisor_rejects_recommended_skill_outside_catalog():
    with pytest.raises(ValueError):
        await build_supervisor([], "m1", recommended_skill_ids=["missing"])


@pytest.mark.parametrize("field_name", ["skill_id", "version_id", "name", "description", "object_key"])
@pytest.mark.asyncio
async def test_build_supervisor_rejects_blank_descriptor_fields(field_name):
    values = descriptor_dict("s1")
    values[field_name] = " "
    with pytest.raises(ValueError):
        await build_supervisor([], "m1", skill_catalog=[SkillDescriptor(**values)])


@pytest.mark.asyncio
async def test_build_supervisor_rejects_duplicate_catalog_and_invalid_object_key():
    with pytest.raises(ValueError):
        await build_supervisor([], "m1", skill_catalog=[
            SkillDescriptor(**descriptor_dict("s1")),
            SkillDescriptor(**descriptor_dict("s1")),
        ])

    with pytest.raises(ValueError):
        await build_supervisor([], "m1", skill_catalog=[SkillDescriptor(**{
            **descriptor_dict("s1"), "object_key": "../outside.zip"
        })])


@pytest.mark.asyncio
async def test_build_supervisor_deduplicates_recommendations_in_stable_order(monkeypatch):
    class FakeAgent:
        def __init__(self, card):
            self.card = card

        def configure(self, _config):
            pass

    attach = AsyncMock()
    monkeypatch.setattr("agent_runtime.supervisor.builder.attach_skill_context", attach)
    monkeypatch.setattr("agent_runtime.supervisor.builder.build_react_config", lambda *_args: object())
    monkeypatch.setattr("agent_runtime.supervisor.builder.ReActAgent", FakeAgent)

    await build_supervisor(
        [],
        "m1",
        skill_catalog=[SkillDescriptor(**descriptor_dict("s1")), SkillDescriptor(**descriptor_dict("s2"))],
        recommended_skill_ids=["s2", "s1", "s2"],
    )

    assert attach.await_args.args[2] == ["s2", "s1"]


@pytest.mark.asyncio
async def test_build_supervisor_rejects_blank_recommended_skill_id():
    with pytest.raises(ValueError):
        await build_supervisor([], "m1", recommended_skill_ids=[" "])
