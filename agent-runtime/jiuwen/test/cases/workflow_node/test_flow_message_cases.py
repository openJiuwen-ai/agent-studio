# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
Message 组件单元测试。

覆盖：批量 invoke 渲染、userFields / 扁平入参、流式帧协议、结构化结束帧、
enable_history、task_completion、非法配置、显式关键字构造，
message_outputs 中的 scope 字段（根图 vs 子工作流）、
以及 Start → Message → End 工作流（invoke / stream，写法参考 test_end.py）。
"""

import pytest
from jiuwen.extension.workflow_node.flow_message import (
    Message,
    MESSAGE_OUTPUTS_KEY,
    MESSAGE_NODE_STREAM,
    MESSAGE_NODE_END,
    _workflow_message_scope,
)
from openjiuwen.core.common.constants.constant import (
    END_NODE_STREAM,
)
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.session.internal.workflow import NodeSession, WorkflowSession
from openjiuwen.core.session.stream import BaseStreamMode, OutputSchema
from openjiuwen.core.workflow import (
    ComponentAbility,
    End,
    Start,
    SubWorkflowComponent,
    Workflow,
    WorkflowCard,
    WorkflowExecutionState,
    create_workflow_session,
)
from openjiuwen.core.workflow.components import Session


def _make_message_session(comp_id: str = "msg1") -> Session:
    wf = WorkflowSession(workflow_id="message_unit_wf", session_id="message_unit_sess")
    node = NodeSession(wf, comp_id, "Message")
    return Session(node, False)


@pytest.mark.asyncio
async def test_invoke_from_user_fields_appends_message_outputs():
    """
    功能点：invoke 从 userFields 取模板变量；返回 {"result": 字符串}；
    同一批次写入工作流级 message_outputs（含 node_type、output、time_stamp）。
    """
    session = _make_message_session()
    comp = Message({"template": "您好，{{name}}！"})
    inputs = {"userFields": {"name": "李四"}}
    out = await comp.invoke(inputs, session, None)
    assert out == {"result": "您好，李四！"}
    stored = session._inner.state().get_workflow_state(MESSAGE_OUTPUTS_KEY)
    assert isinstance(stored, list) and len(stored) == 1
    assert stored[0]["node_type"] == "message"
    assert stored[0]["output"] == "您好，李四！"
    assert "time_stamp" in stored[0]
    assert stored[0]["host_workflow_id"] == "message_unit_wf"
    assert stored[0]["message_component_id"] == "msg1"
    assert stored[0]["executable_id"] == "msg1"
    assert stored[0]["workflow_nesting_depth"] == 0
    assert stored[0]["root_workflow_id"] == "message_unit_wf"


def test_workflow_message_scope_reads_inner_session_facets():
    """
    功能点：_workflow_message_scope 汇总 host/root/depth/executable 等，
    供 message_outputs 区分嵌套执行层（不依赖真实图调度）。
    """

    class _Inner:
        def main_workflow_id(self):
            return "root_wf_1"

        def workflow_nesting_depth(self):
            return 2

        def parent_id(self):
            return "sub_comp"

    class _Sess:
        _inner = _Inner()

        def get_workflow_id(self):
            return "child_wf_card"

        def get_component_id(self):
            return "inner_msg"

        def get_executable_id(self):
            return "sub_comp.inner_msg"

    scope = _workflow_message_scope(_Sess())  # type: ignore[arg-type]
    assert scope["host_workflow_id"] == "child_wf_card"
    assert scope["message_component_id"] == "inner_msg"
    assert scope["executable_id"] == "sub_comp.inner_msg"
    assert scope["root_workflow_id"] == "root_wf_1"
    assert scope["workflow_nesting_depth"] == 2
    assert scope["parent_executable_prefix"] == "sub_comp"


@pytest.mark.asyncio
async def test_invoke_flat_dict_when_no_user_fields():
    """
    功能点：入参顶层无 userFields 时，把整个 dict 当作模板变量表。
    """
    session = _make_message_session()
    comp = Message({"template": "计数={{count}}"})
    out = await comp.invoke({"count": "1"}, session, None)
    assert out == {"result": "计数=1"}


@pytest.mark.asyncio
async def test_stream_stream_frames_and_end_frame():
    """
    功能点：stream 先 yield MESSAGE_NODE_STREAM（可多段），最后 MESSAGE_NODE_END；
    结束帧 payload.result 为全文；默认 enable_history 为 True。
    """
    session = _make_message_session()
    comp = Message({"template": "前缀{{mid}}后缀"})
    chunks = []
    async for frame in comp.stream({"userFields": {"mid": "内容"}}, session, None):
        chunks.append(frame)
    assert len(chunks) >= 2
    assert all(c.type == MESSAGE_NODE_STREAM for c in chunks[:-1])
    assert chunks[-1].type == MESSAGE_NODE_END
    assert chunks[-1].payload["result"] == "前缀内容后缀"
    assert chunks[-1].payload["enable_history"] is True


@pytest.mark.asyncio
async def test_stream_enable_history_false_string_on_end_frame():
    """
    功能点：配置 enable_history 为字符串 \"false\" 时，流结束帧中 enable_history 为 False。
    """
    session = _make_message_session()
    comp = Message({"template": "固定句", "enable_history": "false"})
    chunks = []
    async for frame in comp.stream({"userFields": {}}, session, None):
        chunks.append(frame)
    assert chunks[-1].payload["enable_history"] is False


@pytest.mark.asyncio
async def test_stream_struct_template_struct_answer_on_end_frame():
    """
    功能点：isStructMessage + struct_output_template 时，结束帧携带 struct_answer，
    且可用占位符 _NODE_OUTPUT 引用主模板拼接结果。
    """
    session = _make_message_session()
    comp = Message(
        {
            "template": "正文块",
            "isStructMessage": True,
            "struct_output_template": "包装开始：{{_NODE_OUTPUT}}：包装结束",
        }
    )
    chunks = []
    async for frame in comp.stream({"userFields": {}}, session, None):
        chunks.append(frame)
    assert chunks[-1].payload["struct_answer"] == "包装开始：正文块：包装结束"
    assert chunks[-1].payload["is_struct_message"] is True


def test_event_task_completion_sets_end_interrupt():
    """
    功能点：event.type 为 task_completion 时，组件 end_interrupt 为 True，
    供编排侧识别提前结束等语义。
    """
    comp = Message({"template": "占位", "event": {"type": "task_completion"}})
    assert comp.end_interrupt is True


def test_missing_template_raises():
    """功能点：配置必须包含非空 template，否则构造期抛出 BaseError。"""
    with pytest.raises(BaseError):
        Message({})


def test_empty_template_raises():
    """功能点：template 为空字符串时校验失败，抛出 BaseError。"""
    with pytest.raises(BaseError):
        Message({"template": ""})


@pytest.mark.asyncio
async def test_from_fields_matches_dict_config_invoke():
    """
    功能点：Message.from_fields(...) 与等价 dict / IR 键（outputMode）配置的 invoke 结果一致。
    """
    comp_fields = Message.from_fields(template="答：{{q}}", output_mode="text")
    comp_dict = Message({"template": "答：{{q}}", "outputMode": "text"})
    inputs = {"userFields": {"q": "杭州天气？"}}
    out_fields = await comp_fields.invoke(inputs, _make_message_session(), None)
    out_dict = await comp_dict.invoke(inputs, _make_message_session(), None)
    assert out_fields == out_dict == {"result": "答：杭州天气？"}


def test_message_conf_none_raises():
    """功能点：与 End 不同，Message 必须提供 conf，缺省时报错。"""
    with pytest.raises(BaseError):
        Message(None)


@pytest.mark.asyncio
async def test_workflow_invoke_start_message_end_renders_echo():
    """
    功能点：工作流 Start → Message → End；Message 产出 result，End 用 responseTemplate 引用 ${msg.result}。
    """
    flow = Workflow()
    flow.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    flow.add_workflow_comp(
        "msg",
        Message({"template": "Hello {{name}}", "outputMode": None}),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    flow.set_end_comp(
        "e",
        End({"responseTemplate": "echo={{echo}}"}),
        inputs_schema={"echo": "${msg.result}"},
    )
    flow.add_connection("s", "msg")
    flow.add_connection("msg", "e")

    res = await flow.invoke({"userFields": {"name": "Sam"}}, create_workflow_session())
    assert res.state == WorkflowExecutionState.COMPLETED
    assert res.result == {"response": "echo=Hello Sam"}


@pytest.mark.asyncio
async def test_workflow_invoke_parent_subworkflow_child_message_end():
    """
    功能点：父子工作流——父图 Start → SubWorkflowComponent(子图 Start → Message → End) → End；
    子图 Message 渲染 result，子 End 用 responseTemplate 产出子级 response；
    父 End 通过 ${sub.response} 引用子工作流最终响应（与 test_workflow 中嵌套模板用例一致）。
    """
    child = Workflow()
    child.set_start_comp("cs", Start(), inputs_schema={"userFields": "${userFields}"})
    child.add_workflow_comp(
        "msg",
        Message({"template": "子问候-{{name}}"}),
        inputs_schema={"userFields": "${cs.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    child.set_end_comp(
        "ce",
        End({"responseTemplate": "[子]{{out}}"}),
        inputs_schema={"out": "${msg.result}"},
    )
    child.add_connection("cs", "msg")
    child.add_connection("msg", "ce")

    parent = Workflow()
    parent.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    parent.add_workflow_comp(
        "sub",
        SubWorkflowComponent(child),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    parent.set_end_comp(
        "e",
        End({"responseTemplate": "父收到={{child_line}}"}),
        inputs_schema={"child_line": "${sub.response}"},
    )
    parent.add_connection("s", "sub")
    parent.add_connection("sub", "e")

    res = await parent.invoke(
        {"userFields": {"name": "Nested"}}, create_workflow_session()
    )
    assert res.state == WorkflowExecutionState.COMPLETED
    assert res.result == {"response": "父收到=[子]子问候-Nested"}


@pytest.mark.asyncio
async def test_message_outputs_scope_root_vs_child_in_one_invoke(monkeypatch):
    """
    功能点：同一根 session 的 message_outputs 中，根图 Message 与子工作流 Message
    通过 host_workflow_id / root_workflow_id / workflow_nesting_depth（及 executable_id）区分作用域。
    """
    from jiuwen.extension.workflow_node import flow_message as flow_message_mod

    captured: list[dict] = []
    _orig_append = flow_message_mod._append_workflow_message_output

    def _capture_append(session, record):
        captured.append(dict(record))
        return _orig_append(session, record)

    monkeypatch.setattr(
        flow_message_mod, "_append_workflow_message_output", _capture_append
    )

    parent_card = WorkflowCard(id="wf_parent_msg_scope", name="parent")
    child_card = WorkflowCard(id="wf_child_msg_scope", name="child")

    child = Workflow(card=child_card)
    child.set_start_comp("cs", Start(), inputs_schema={"userFields": "${userFields}"})
    child.add_workflow_comp(
        "cmsg",
        Message({"template": "子-{{name}}"}),
        inputs_schema={"userFields": "${cs.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    child.set_end_comp(
        "ce",
        End({"responseTemplate": "[子]{{out}}"}),
        inputs_schema={"out": "${cmsg.result}"},
    )
    child.add_connection("cs", "cmsg")
    child.add_connection("cmsg", "ce")

    parent = Workflow(card=parent_card)
    parent.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    parent.add_workflow_comp(
        "pmsg",
        Message({"template": "父-{{name}}"}),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    parent.add_workflow_comp(
        "sub",
        SubWorkflowComponent(child),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    parent.set_end_comp(
        "e",
        End({"responseTemplate": "done={{child_line}}"}),
        inputs_schema={"child_line": "${sub.response}"},
    )
    parent.add_connection("s", "pmsg")
    parent.add_connection("pmsg", "sub")
    parent.add_connection("sub", "e")

    res = await parent.invoke(
        {"userFields": {"name": "Scope"}}, create_workflow_session()
    )
    assert res.state == WorkflowExecutionState.COMPLETED
    assert len(captured) == 2

    root_rec = next(r for r in captured if r["message_component_id"] == "pmsg")
    nested_rec = next(r for r in captured if r["message_component_id"] == "cmsg")

    assert root_rec["output"] == "父-Scope"
    assert root_rec["host_workflow_id"] == parent_card.id
    assert root_rec["root_workflow_id"] == parent_card.id
    assert root_rec["workflow_nesting_depth"] == 0
    assert root_rec["executable_id"] == "pmsg"

    assert nested_rec["output"] == "子-Scope"
    assert nested_rec["host_workflow_id"] == child_card.id
    assert nested_rec["root_workflow_id"] == parent_card.id
    assert nested_rec["workflow_nesting_depth"] == 1
    assert (
        "sub" in nested_rec["executable_id"] and "cmsg" in nested_rec["executable_id"]
    )


@pytest.mark.asyncio
async def test_workflow_invoke_start_message_end_struct_config_plain_line_to_end():
    """
    功能点：Message 开启结构化等配置时，invoke 路径仍以主模板正文作为 result；End 只消费 msg.result。
    """
    flow = Workflow()
    flow.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    flow.add_workflow_comp(
        "msg",
        Message(
            {
                "template": "body-{{id}}",
                "isStructMessage": True,
                "struct_output_template": "wrap:{{_NODE_OUTPUT}}",
                "enable_history": "false",
                "outputMode": "text",
            }
        ),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    flow.set_end_comp(
        "e",
        End({"responseTemplate": "final={{t}}"}),
        inputs_schema={"t": "${msg.result}"},
    )
    flow.add_connection("s", "msg")
    flow.add_connection("msg", "e")

    res = await flow.invoke({"userFields": {"id": "99"}}, create_workflow_session())
    assert res.state == WorkflowExecutionState.COMPLETED
    assert res.result == {"response": "final=body-99"}


@pytest.mark.asyncio
async def test_workflow_stream_start_message_end_end_stream_chunks_like_test_end_stream_template():
    """
    功能点：对齐 test_end.test_end_stream_template——End 使用 response_mode=\"streaming\" 时，
    workflow.stream 产出多帧 ``end node stream``；此处上游由 Message invoke 写入 msg.result，
    End 模板按静态片段与变量分段输出。
    """
    flow = Workflow()
    flow.set_start_comp("s", Start(), inputs_schema={"userFields": "${userFields}"})
    flow.add_workflow_comp(
        "msg",
        Message({"template": "result:{{a}},{{b}}"}),
        inputs_schema={"userFields": "${s.userFields}"},
        comp_ability=[ComponentAbility.INVOKE],
    )
    flow.set_end_comp(
        "e",
        End({"responseTemplate": "final:{{line}}"}),
        inputs_schema={"line": "${msg.result}"},
        response_mode="streaming",
    )
    flow.add_connection("s", "msg")
    flow.add_connection("msg", "e")

    streams: list[OutputSchema] = []
    async for chunk in flow.stream(
        {"userFields": {"a": "hello", "b": "hz"}},
        create_workflow_session(),
        stream_modes=[BaseStreamMode.OUTPUT],
    ):
        streams.append(chunk)

    expected = [
        OutputSchema(type=END_NODE_STREAM, index=0, payload={"response": "final:"}),
        OutputSchema(
            type=END_NODE_STREAM, index=1, payload={"response": "result:hello,hz"}
        ),
    ]
    assert streams == expected


@pytest.mark.asyncio
async def test_stream_standalone_message_yields_stream_then_end_frame():
    """功能点：仅 Message + Session 流式调用时，存在 MESSAGE_NODE_STREAM 与末帧 MESSAGE_NODE_END。"""
    wf = WorkflowSession(workflow_id="wf_msg_stream", session_id="sess_stream")
    node = NodeSession(wf, "msg_only", "Message")
    session = Session(node, False)
    comp = Message({"template": "p{{q}}r"})
    out: list[OutputSchema] = []
    async for frame in comp.stream({"userFields": {"q": "1"}}, session, None):
        if isinstance(frame, OutputSchema):
            out.append(frame)
    assert any(f.type == MESSAGE_NODE_STREAM for f in out)
    assert out[-1].type == MESSAGE_NODE_END
    assert out[-1].payload.get("result") == "p1r"
