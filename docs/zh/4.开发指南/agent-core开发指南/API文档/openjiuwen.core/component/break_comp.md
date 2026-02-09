# openjiuwen.core.component.break_comp

## class openjiuwen.core.component.break_comp.BreakComponent

中断组件类，用于控制循环的中断，为工作流提供了强大的循环中断能力，可以在特定条件下主动终止循环执行。当执行到该组件时，循环将立即停止。

> **说明**
>
> * `BreakComponent`可与[LoopComponent](./loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent)和`loop_type="always_true"`（无限循环）配合使用。通过设置无限循环条件，使循环持续执行，直到遇到中断组件时才会退出循环。
> * 可以结合条件判断组件，实现更复杂的条件中断逻辑，例如在满足特定条件时才执行中断操作。
> * 在循环体中，`BreakComponent`的执行顺序会影响循环中断的时机，需要合理安排其在循环体中的位置。

**样例**：

```python
>>> import asyncio
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> from openjiuwen.core.component.break_comp import BreakComponent
>>> from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>>
>>> # 自定义组件AddTenNode， 每次调用，对于inputs中的source累加10
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>>
>>> # 空节点，用于标记循环结束节点
>>> class EmptyNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return inputs
>>>
>>>
>>> # 执行测试
>>> # input_number=2, loop_number=2: 循环执行2次
>>> async def run_workflow():
...     flow = Workflow()
...     flow.set_start_comp("s", Start({"inputs": []}))
...     flow.set_end_comp("e", End({}),
...                       inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})
...
...     # 创建循环体
...     loop_group = LoopGroup()
...     # AddTenNode("1"): 接收当前循环索引l.index作为输入，每次循环索引会自动递增
...     # 注意：这里的"1"是组件的标识ID，用于在output_schema中引用其结果
...     loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.index}"})
...     # AddTenNode("2"): 接收中间变量l.user_var作为输入
...     loop_group.add_workflow_comp("2", AddTenNode("2"),
...                                  inputs_schema={"source": "${l.user_var}"})
...     # SetVariableComponent: 更新中间变量l.user_var为AddTenNode("2")的处理结果
...     # 这使得每次循环的中间变量值都可以基于前一次循环结果进行更新
...     set_variable_component = SetVariableComponent({"${l.user_var}": "${2.result}"})
...     loop_group.add_workflow_comp("3", set_variable_component)
...
...     # 添加分支组件来决定是否继续循环
...     # BranchComponent用于根据条件选择不同的执行路径
...     sw = BranchComponent()
...     # 第一个分支条件：当当前循环索引(l.index)大于等于(循环次数-1)时，执行break组件
...     # 注意：索引从0开始，所以循环3次时索引值为0,1,2，当索引=2时应该中断
...     sw.add_branch("${l.index} >= ${loop_number} - 1", ["4"], "1")
...     # 第二个分支条件：当当前循环索引小于(循环次数-1)时，进入循环结束节点，开始下一轮循环
...     # 注意：分支目标必须是循环体内部的节点，否则会出现 Channel not found 错误
...     sw.add_branch("${l.index} < ${loop_number} - 1", ["5"], "2")
...
...     loop_group.add_workflow_comp("sw", sw)
...
...     # 添加break组件
...     # BreakComponent用于在满足条件时显式中断循环执行
...     # 这是在使用always_true循环类型时控制循环次数的关键组件
...     break_node = BreakComponent()
...     loop_group.add_workflow_comp("4", break_node)
...
...     # 添加空节点作为循环的结束节点
...     empty_node = EmptyNode("5")
...     loop_group.add_workflow_comp("5", empty_node)
...
...     # 设置循环体的起始节点和结束节点
...     loop_group.start_nodes(["1"])
...     loop_group.end_nodes(["5"])
...     # 设置循环体内各组件的连接关系
...     loop_group.add_connection("1", "2")
...     loop_group.add_connection("2", "3")
...     loop_group.add_connection("3", "sw")
...     loop_group.add_connection("4", "5")
...
...     # 创建LoopComponent
...     # 参数1: loop_group - 定义的循环体
...     # 参数2: output_schema - 定义循环组件的输出结构
...     # - results: 收集每次循环中AddTenNode("1")的结果到数组
...     # - user_var: 保留循环结束后的最终中间变量值
...     loop_component = LoopComponent(loop_group, {"results": "${1.result}", "user_var": "${l.user_var}"})
...
...     # 添加到工作流
...     # loop_type: "always_true" - 表示循环会一直执行直到遇到BreakComponent中断
...     # intermediate_var: 初始化循环内的中间变量，这里将input_number的值赋给user_var
...     # 在always_true类型的循环中，必须通过BreakComponent来控制循环次数或终止条件
...     flow.add_workflow_comp("l", loop_component, inputs_schema={"loop_type": "always_true",
...                                                                "intermediate_var": {"user_var": "${input_number}"}})
...
...     # 设置连接
...     flow.add_connection("s", "l")
...     flow.add_connection("l", "e")
...     return await flow.invoke({"input_number": 2, "loop_number": 2}, WorkflowRuntime())
>>>
>>> if __name__ == "__main__":
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
>>> # 预期结果说明：
>>> # - array_result: [10, 11] 是循环中每个AddTenNode("1")处理后的结果数组
>>> #   (索引0+10=10, 索引1+10=11)
>>> # - user_var: 22 是循环结束后的最终中间变量值，计算过程：
>>> #   初始值2 → 2+10=12 → 12+10=22（共2次循环）
>>> # 在always_true类型的循环中，循环执行次数由BreakComponent和分支条件共同控制
>>> # 此示例中，当l.index >= loop_number - 1 (1 >= 2-1=1)时触发BreakComponent中断循环
{'output': {'array_result': [10, 11], 'user_var': 22}}
```
