"""
LoopComponent 核心功能测试

工作流结构统一为: Start → LoopComponent → End

循环体内通过 LoopSetVariable + inputs_schema 引用实现跨迭代状态传递，
遵循 openjiuwen 的变量引用机制。循环体组件通过 inputs_schema 读取上游变量，
通过 output_schema 输出结果，LoopSetVariable 将输出写回变量存储。

覆盖功能点：
1. 次数循环 (number loop) — 跨迭代累加计数器
2. 数组遍历 (array loop) — 处理每个数组元素
3. 中断机制 (LoopBreakComponent) — 第一轮即中断
4. 输出收集 — 验证 output_schema 收集为列表
5. 跨迭代状态传递 (intermediateVar)
6. 全局变量写入 (_request. 前缀) — 使用增强版 LoopSetVariable
7. 条件中断 — LoopBreakComponent 替代 breakCondition
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.loop_set_variable import (
    LoopSetVariable,
    _REQUEST_KEY,
)
from jiuwen.extension.workflow_node.start import Start
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
    WorkflowComponent,
    LoopComponent,
    LoopGroup,
    LoopBreakComponent,
)

pytestmark = pytest.mark.asyncio

# Start/End 节点共用的最小配置
_MINIMAL_CONF = {
    "userFields": {"inputs": [], "outputs": []},
    "systemFields": {"inputs": [], "outputs": []},
}


# ============================================================================
# 辅助组件（替代真实 LLM / Message 等业务组件，仅用于测试）
# ============================================================================


class AccumulatorComponent(WorkflowComponent):
    """累加器组件：从 inputs 读取 total，加 1 后输出新的 total 和描述文本。

    首次调用时 total 为 None，使用 default_total 作为初始值。
    """

    def __init__(self, default_total: int = 0):
        super().__init__()
        self._default = default_total

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        total = (inputs or {}).get("total")
        if total is None:
            total = self._default
        new_total = total + 1
        return {"total": new_total, "text": f"round_{total}"}


class ItemProcessorComponent(WorkflowComponent):
    """数组元素处理组件：从 inputs 读取当前数组元素，输出处理结果。"""

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        item = (inputs or {}).get("item", "")
        return {"text": f"hello_{item}", "length": len(str(item))}


class ThresholdBreakComponent(LoopBreakComponent):
    """条件中断组件：当 inputs.total >= threshold 时中断循环，否则跳过。"""

    def __init__(self, threshold: int):
        super().__init__()
        self._threshold = threshold

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        total = (inputs or {}).get("total", 0) or 0
        if total >= self._threshold:
            return await super().invoke(inputs, session, context)
        return {}


class GlobalStateProbe(WorkflowComponent):
    """读取 global_state["_request"] 中指定 key 的值，用于测试验证 _request. 变量写入。

    读取路径与 WorkflowWrapper 一致：
    旧框架从 REQUEST_VARIABLES 读取 → 新框架从 global_state["_request"] 读取。
    """

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        request_vars = session.get_global_state(_REQUEST_KEY) or {}
        value = request_vars.get(self._key) if isinstance(request_vars, dict) else None
        return {self._key: value}


# ============================================================================
# 测试用例
# ============================================================================


async def test_number_loop():
    """
    测试次数循环：循环 3 次，验证跨迭代累加

    覆盖功能点: #1 次数循环, #5 状态机管理

    验证要点:
    1. 循环执行指定次数
    2. LoopSetVariable 将 body 输出写回 state_store，下一轮 body 通过
       inputs_schema 读取到更新后的值，实现跨迭代状态传递
    3. output_schema 将每轮 body 的输出收集为列表

    循环体: body(读取 state_store.total) → update_var(将 body.total 写回 state_store)
    工作流: Start → Loop(body→update_var × 3) → End

    预期:
    - text: 每轮收到递增的 total (0→1→2)，输出 ["round_0", "round_1", "round_2"]
    - total: 累加值 [1, 2, 3]
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "body",
        AccumulatorComponent(),
        inputs_schema={"total": "${state_store.total}"},
    )
    loop_group.add_workflow_comp(
        "update_var",
        LoopSetVariable({"${state_store.total}": "${body.total}"}),
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["update_var"])
    loop_group.add_connection("body", "update_var")

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}", "total": "${body.total}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node", loop_comp, inputs_schema={"loop_type": "number", "loop_number": 3}
    )
    workflow.set_end_comp(
        "end",
        End(),
        inputs_schema={
            "result": "${loop_node.text}",
            "totals": "${loop_node.total}",
        },
    )
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "end")

    session = create_workflow_session()
    result = await workflow.invoke({"query": "test_number_loop"}, session=session)

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]
    # 验证循环执行了 3 次，每轮 text 正确
    assert output["result"] == ["round_0", "round_1", "round_2"]
    # 验证跨迭代状态传递：每轮 total 递增，LoopSetVariable 写回后下一轮可读
    assert output["totals"] == [1, 2, 3]
    workflow_logger.info(f"test_number_loop: {output}")


async def test_array_loop():
    """
    测试数组遍历：遍历城市数组，处理每个元素

    覆盖功能点: #1 数组遍历, #6 获取当前元素

    验证要点:
    1. LoopComponent 按数组长度执行对应次数
    2. 每轮迭代通过 inputs_schema 的 ${loop_node.item} 引用获取当前数组元素
    3. body 组件确实使用了该元素进行处理（而非空转）
    4. output_schema 将每轮 body 输出收集为列表

    循环体: body(通过 inputs_schema 读取当前数组元素)
    工作流: Start → Loop(body × 数组) → End

    预期:
    - text: ["hello_Beijing", "hello_Shanghai", "hello_Guangzhou"]
    - length: [7, 8, 9]（每个城市名的字符长度）
    """
    loop_group = LoopGroup()
    # 通过 inputs_schema 引用 ${loop_node.item} 直接获取当前迭代的数组元素
    loop_group.add_workflow_comp(
        "body",
        ItemProcessorComponent(),
        inputs_schema={"item": "${loop_node.item}"},
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["body"])

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}", "length": "${body.length}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node",
        loop_comp,
        inputs_schema={
            "loop_type": "array",
            "loop_array": {"item": ["Beijing", "Shanghai", "Guangzhou"]},
        },
    )
    workflow.set_end_comp(
        "end",
        End(),
        inputs_schema={
            "result": "${loop_node.text}",
            "lengths": "${loop_node.length}",
        },
    )
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "end")

    session = create_workflow_session()
    result = await workflow.invoke({"query": "test_array_loop"}, session=session)

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]
    # 验证每个数组元素被正确传递给 body 并处理
    assert output["result"] == ["hello_Beijing", "hello_Shanghai", "hello_Guangzhou"]
    # 验证 body 确实使用了传入的数组元素（字符长度与城市名一一对应）
    assert output["lengths"] == [7, 8, 9]
    workflow_logger.info(f"test_array_loop: {output}")


async def test_loop_break():
    """
    测试条件中断：累加到阈值时中断循环

    覆盖功能点: #9 中断机制 (LoopBreakComponent)

    验证要点:
    1. ThresholdBreakComponent 在 total >= threshold 时触发 break
    2. break 触发后，当前轮正常结束（update_var 作为 end_node 仍执行），
       但后续轮次不再执行
    3. break 发生在正确时机（total 累加到 3 时，即第 3 轮后 break）
    4. output_schema 收集到 break 之前的所有轮次输出

    循环体: body(累加) → break(total >= 3 时中断) / update_var(写回 state_store)
    工作流: Start → Loop(body→break/update_var, 最多 10 次) → End

    预期:
    - 输出 ["round_0", "round_1", "round_2"]（3 轮后 break，而非跑满 10 次）
    - break 后工作流正常完成（非异常状态）
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "body",
        AccumulatorComponent(),
        inputs_schema={"total": "${state_store.total}"},
    )
    loop_group.add_workflow_comp(
        "break",
        ThresholdBreakComponent(threshold=3),
        inputs_schema={"total": "${body.total}"},
    )
    loop_group.add_workflow_comp(
        "update_var",
        LoopSetVariable({"${state_store.total}": "${body.total}"}),
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["break", "update_var"])
    loop_group.add_connection("body", "break")
    loop_group.add_connection("body", "update_var")

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node", loop_comp, inputs_schema={"loop_type": "number", "loop_number": 10}
    )
    workflow.set_end_comp("end", End(), inputs_schema={"result": "${loop_node.text}"})
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "end")

    session = create_workflow_session()
    result = await workflow.invoke({"query": "test_loop_break"}, session=session)

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]["result"]
    # 验证 break 在正确时机触发：第 3 轮 body.total=3 >= threshold=3 时 break
    # 输出 3 条而非 10 条，证明后续轮次被跳过
    assert output == ["round_0", "round_1", "round_2"]
    assert len(output) == 3  # break 阻止了后续 7 轮的执行
    workflow_logger.info(f"test_loop_break: {output}")


async def test_loop_output_collection():
    """
    测试输出收集：验证 output_schema 对同一字段的列表收集

    覆盖功能点: #10/#12 输出收集 + 单值/列表区分

    循环体: body(累加) → update_var
    工作流: Start → Loop × 3 → End

    预期: text 收集为列表 ["round_0","round_1","round_2"]，total 收集为列表 [1,2,3]
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "body",
        AccumulatorComponent(),
        inputs_schema={"total": "${state_store.total}"},
    )
    loop_group.add_workflow_comp(
        "update_var",
        LoopSetVariable({"${state_store.total}": "${body.total}"}),
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["update_var"])
    loop_group.add_connection("body", "update_var")

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}", "total": "${body.total}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node", loop_comp, inputs_schema={"loop_type": "number", "loop_number": 3}
    )
    workflow.set_end_comp(
        "end",
        End(),
        inputs_schema={
            "result": "${loop_node.text}",
            "totals": "${loop_node.total}",
        },
    )
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "end")

    session = create_workflow_session()
    result = await workflow.invoke(
        {"query": "test_loop_output_collection"}, session=session
    )

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]
    assert output["result"] == ["round_0", "round_1", "round_2"]
    assert output["totals"] == [1, 2, 3]
    workflow_logger.info(f"test_loop_output_collection: {output}")


async def test_intermediate_var():
    """
    测试 intermediate_var 机制：通过中间变量初始化跨迭代状态的起始值

    覆盖功能点: #13 跨迭代状态传递

    背景: 旧框架 Loop 组件通过 intermediateLoopVar 在循环开始前注入初始值到变量池，
    循环体通过变量引用读取该初始值。新框架 LoopComponent 的 intermediate_var 参数
    通过 IntermediateLoopVarCallback 实现相同功能。

    机制分析:
    - IntermediateLoopVarCallback.first_in_loop() 返回 {"total": 10}
    - LoopCallback._atomic_invoke() 将返回值通过 set_outputs 写入 session 的 io_state
    - session 是 NodeSession(loop_session, "loop_node")，node_id="loop_node",
      parent_id=loop_node_executable_id
    - set_outputs 写入路径: io_state["loop_node"]["loop_node"]["total"] = 10
    - body 组件的 parent_id="loop_node"，get_inputs 在 io_state["loop_node"] 下查找
    - 因此 body 应通过 ${loop_node.total} 引用 intermediate_var 写入的值

    验证要点:
    1. intermediate_var 中的初始值能被循环体通过 ${loop_node.total} 读取
    2. 后续迭代通过 LoopSetVariable 写回 ${loop_node.total}，实现跨迭代状态传递

    循环体: body(读取 loop_node.total) → update_var(写回 loop_node.total)
    工作流: Start → Loop × 3(intermediate_var={total: 10}) → End

    预期:
    - 第 1 轮: intermediate_var 注入 total=10，body 输出 round_10, total=11
    - 第 2 轮: update_var 写回的 total=11 生效，body 输出 round_11, total=12
    - 第 3 轮: total=12，body 输出 round_12, total=13
    - 输出 ["round_10", "round_11", "round_12"]
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "body",
        AccumulatorComponent(default_total=0),
        inputs_schema={"total": "${loop_node.total}"},
    )
    # LoopSetVariable 写回 loop_node 命名空间，与 intermediate_var 写入路径一致
    loop_group.add_workflow_comp(
        "update_var",
        LoopSetVariable({"${loop_node.total}": "${body.total}"}),
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["update_var"])
    loop_group.add_connection("body", "update_var")

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}", "total": "${body.total}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node",
        loop_comp,
        inputs_schema={
            "loop_type": "number",
            "loop_number": 3,
            "intermediate_var": {"total": 10},
        },
    )
    workflow.set_end_comp(
        "end",
        End(),
        inputs_schema={
            "result": "${loop_node.text}",
            "totals": "${loop_node.total}",
        },
    )
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "end")

    session = create_workflow_session()
    result = await workflow.invoke({"query": "test_intermediate_var"}, session=session)

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]
    # 验证 intermediate_var 注入了初始值 total=10
    assert output["result"] == ["round_10", "round_11", "round_12"]
    # 验证跨迭代状态传递：total 从 10 开始，每轮 +1
    assert output["totals"] == [11, 12, 13]
    workflow_logger.info(f"test_intermediate_var: {output}")


async def test_set_variable_with_request_prefix():
    """
    测试 _request. 前缀全局变量写入

    覆盖功能点: #15/#16 全局变量写入

    背景: 旧框架 SetVariable 支持 _request. 前缀变量写入 REQUEST_VARIABLES（全局状态）
    和 CONSTANT_NODE_VARIABLE（节点变量池），使循环内变量可被循环外组件读取。
    新框架原生 LoopSetVariableComponent 不支持此能力，LoopSetVariable 通过
    set_outputs（写 io_state）+ update_global（写 global_state）补齐。

    验证要点:
    1. 循环正常完成，说明 LoopSetVariable 的 _request. 写入不影响循环执行
    2. _request. 变量写入 global_state["_REQUEST"]（与 WorkflowWrapper 初始化路径一致）
       可被循环外的下游组件通过 get_global_state("_REQUEST") 读取
       （等价于旧框架写入 REQUEST_VARIABLES 后其他节点从 REQUEST_VARIABLES 读取）

    循环体: body(累加) → update_var(写回 state_store) → set_var(写 _request.global_counter)
    工作流: Start → Loop × 2 → Probe(读取 global_state) → End

    预期:
    - 循环正常完成，输出 ["round_0", "round_1"]
    - Probe 从 global_state["_REQUEST"] 读到 global_counter = 2（最后一轮覆盖写入的值）
    """
    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "body",
        AccumulatorComponent(),
        inputs_schema={"total": "${state_store.total}"},
    )
    loop_group.add_workflow_comp(
        "update_var",
        LoopSetVariable({"${state_store.total}": "${body.total}"}),
    )
    # 使用增强版 LoopSetVariable 写入 _request. 全局变量
    loop_group.add_workflow_comp(
        "set_var",
        LoopSetVariable({"${_request.global_counter}": "${body.total}"}),
    )
    loop_group.start_nodes(["body"])
    loop_group.end_nodes(["set_var"])
    loop_group.add_connection("body", "update_var")
    loop_group.add_connection("update_var", "set_var")

    loop_comp = LoopComponent(
        loop_group,
        output_schema={"text": "${body.text}", "total": "${body.total}"},
    )

    workflow = Workflow()
    workflow.set_start_comp("start", Start(_MINIMAL_CONF), inputs_schema={})
    workflow.add_workflow_comp(
        "loop_node", loop_comp, inputs_schema={"loop_type": "number", "loop_number": 2}
    )
    # Probe 放在 loop 之后，读取 global_state 中 loop 写入的 _request.global_counter
    workflow.add_workflow_comp(
        "probe", GlobalStateProbe("global_counter"), inputs_schema={}
    )
    workflow.set_end_comp(
        "end",
        End(),
        inputs_schema={
            "result": "${loop_node.text}",
            "global_counter": "${probe.global_counter}",
        },
    )
    workflow.add_connection("start", "loop_node")
    workflow.add_connection("loop_node", "probe")
    workflow.add_connection("probe", "end")

    session = create_workflow_session()
    result = await workflow.invoke(
        {"query": "test_set_variable_with_request_prefix"}, session=session
    )

    assert result.state == WorkflowExecutionState.COMPLETED
    output = result.result["answer"]["output"]
    # 验证循环正常完成
    assert output["result"] == ["round_0", "round_1"]
    # 验证 _request. 前缀变量通过 update_global 写入 global_state 后，
    # 可被循环外的下游组件通过 session.get_global_state() 读取
    # 等价于旧框架写入 REQUEST_VARIABLES 后其他节点读取
    assert output["global_counter"] == 2
    workflow_logger.info(f"test_set_variable_with_request_prefix: {output}")
