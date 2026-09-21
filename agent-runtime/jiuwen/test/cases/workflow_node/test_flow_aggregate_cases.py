# coding: utf-8
import pytest
from jiuwen.extension.workflow_node.flow_aggregate import Aggregate
from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.session.internal.workflow import NodeSession, WorkflowSession
from openjiuwen.core.workflow import (
    ComponentAbility,
    End,
    Start,
    Workflow,
    WorkflowExecutionState,
    create_workflow_session,
)
from openjiuwen.core.workflow.components import Session


def _session(comp_id: str = "agg1") -> Session:
    wf = WorkflowSession(workflow_id="wf_agg", session_id="s1")
    return Session(NodeSession(wf, comp_id, "Aggregate"), False)


@pytest.mark.asyncio
async def test_first_non_null_strings_picks_first_non_empty():
    comp = Aggregate({"mode": "first-non-null", "groups": {"merged": ["x", "y"]}})
    out = await comp.invoke({"userFields": {"x": "", "y": "second"}}, _session(), None)
    assert out == {USER_FIELDS: {"merged": "second"}}


@pytest.mark.asyncio
async def test_first_non_null_non_string_picks_first_not_none():
    """Non-string branch: first list element that is not None (types must match jiuwen rules)."""
    comp = Aggregate({"groups": {"n": ["a", "b"]}})
    out = await comp.invoke({"userFields": {"a": None, "b": None}}, _session(), None)
    assert out == {USER_FIELDS: {"n": None}}
    out2 = await comp.invoke({"userFields": {"a": 2, "b": 7}}, _session(), None)
    assert out2 == {USER_FIELDS: {"n": 2}}


@pytest.mark.asyncio
async def test_groups_as_list_of_dicts():
    comp = Aggregate(
        {
            "groups": [
                {"id": "o1", "value_list": ["p", "q"]},
            ]
        }
    )
    out = await comp.invoke({"userFields": {"p": "", "q": "v"}}, _session(), None)
    assert out == {USER_FIELDS: {"o1": "v"}}


@pytest.mark.asyncio
async def test_dict_values_same_shape_ok():
    comp = Aggregate({"groups": {"d": ["a", "b"]}})
    out = await comp.invoke(
        {
            "userFields": {
                "a": {"k": 0},
                "b": {"k": 1},
            }
        },
        _session(),
        None,
    )
    assert out == {USER_FIELDS: {"d": {"k": 0}}}


@pytest.mark.asyncio
async def test_dict_values_type_mismatch_raises():
    comp = Aggregate({"groups": {"d": ["a", "b"]}})
    with pytest.raises(BaseError):
        await comp.invoke(
            {"userFields": {"a": {"k": 1}, "b": {"k": "s"}}},
            _session(),
            None,
        )


@pytest.mark.asyncio
async def test_scalar_type_mismatch_raises():
    comp = Aggregate({"groups": {"m": ["a", "b"]}})
    with pytest.raises(BaseError):
        await comp.invoke({"userFields": {"a": 1, "b": "x"}}, _session(), None)


@pytest.mark.asyncio
async def test_unsupported_mode_raises():
    comp = Aggregate({"mode": "merge-all", "groups": {"x": ["a"]}})
    with pytest.raises(BaseError):
        await comp.invoke({"userFields": {"a": 1}}, _session(), None)


@pytest.mark.asyncio
async def test_flat_inputs_when_no_user_fields_key():
    comp = Aggregate({"groups": {"o": ["a", "b"]}})
    out = await comp.invoke({"a": "", "b": "z"}, _session(), None)
    assert out == {USER_FIELDS: {"o": "z"}}


@pytest.mark.asyncio
async def test_workflow_invoke_start_aggregate_end_first_non_null():
    """
    端到端：Start → Aggregate → End。
    验证图调度、inputs_schema 变量绑定与 Aggregate 合并结果可被 End 模板消费。
    """
    flow = Workflow()
    flow.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    flow.add_workflow_comp(
        "agg",
        Aggregate({"mode": "first-non-null", "groups": {"merged": ["x", "y"]}}),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    flow.set_end_comp(
        "e",
        End({"responseTemplate": "out={{val}}"}),
        inputs_schema={"val": "${agg.userFields.merged}"},
    )
    flow.add_connection("s", "agg")
    flow.add_connection("agg", "e")

    res = await flow.invoke(
        {"userFields": {"x": "", "y": "second"}}, create_workflow_session()
    )
    assert res.state == WorkflowExecutionState.COMPLETED
    assert res.result == {"response": "out=second"}


def test_invalid_conf_raises():
    with pytest.raises(BaseError):
        Aggregate(None)
