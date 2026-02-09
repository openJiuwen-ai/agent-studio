# openjiuwen.core.component.loop_comp

## class openjiuwen.core.component.loop_comp.LoopGroup

循环体，用于组织和管理一组循环执行的组件。LoopGroup 是构建循环逻辑的基础容器，它可以包含多个组件并定义它们之间的连接关系，为工作流提供了强大的循环处理能力的基础支持。

### add_workflow_comp

```python
add_workflow_comp(comp_id: str, workflow_comp: Union[Executable, WorkflowComponent], *, comp_ability: list[ComponentAbility] = None, wait_for_all: bool = None, inputs_schema: dict = None, stream_inputs_schema: dict = None, outputs_schema: dict = None, stream_outputs_schema: dict = None, inputs_transformer=None, outputs_transformer=None, **kwargs) -> Self
```

添加工作流组件到循环体中。注意，循环体添加的组件只能在循环体内使用，不能在循环体外使用。同理，循环体外（使用`openjiuwen.core.workflow.base.BaseWorkFlow.add_workflow_comp`接口）添加的组件也只能在循环体外使用，不能在循环体内使用。

**参数**：

- **comp_id**(str)：组件的唯一标识符，用于在循环体中引用此组件。注意是整个 Workflow 中的唯一标识符，不能与其他组件重复。
- **workflow_comp**(Union[Executable, WorkflowComponent])：待添加的循环体组件实例，取值类型不可为`LoopComponent`。支持两种类型：
  - `Executable`：基础可执行组件（如函数、脚本、工具调用实例）。
  - `WorkflowComponent`：子工作流组件（即已定义的完整工作流，可作为当前工作流的一个子节点）。
- *：参数分隔符
- **comp_ability**(list[ComponentAbility], 可选)：组件的能力列表，用于指定组件支持的能力类型（如`INVOKE`、`STREAM`、`TRANSFORM`、`COLLECT`）。默认值：`None`，表示由系统自动推断组件能力。
- **wait_for_all**(bool, 可选)：是否等待所有前置依赖组件执行完成后再执行此组件。`True`表示需要等待所有前置依赖组件执行完成，`False`表示不需要。默认值：`None`，表示由系统根据组件能力自动决定（流式组件默认为`True`，其他组件默认为`False`）。
- **inputs_schema**(dict, 可选)：组件常规输入参数的结构 schema。用于校验输入数据的格式合法性。键名与组件输入参数名匹配，值与组件输入数据类型匹配，未配置时不校验输入格式。默认值：`None`。
- **stream_inputs_schema**(dict, 可选)：组件流式输入参数的结构 schema。用于定义流式输入数据的格式规范。默认值：`None`。
- **outputs_schema**(dict, 可选)：组件常规输出结果的结构 schema。用于定义输出数据的格式规范，便于后续组件解析；未配置时输出格式由组件自身决定。默认值：`None`。
- **stream_outputs_schema**(dict, 可选)：组件流式输出结果的结构 schema。用于定义流式输出数据的格式规范。默认值：`None`。
- **inputs_transformer**([Transformer](../workflow/workflow_config.md#type-alias-openjiuwencoreworkflowworkflow_configtransformercallableany-any), 可选)：输入数据转换器，负责在将数据传递给组件前进行格式转换或预处理，允许开发者注入自定义逻辑。schema规范结构在前，transformer格式转换在后，可同时配置。默认值：`None`。
- **outputs_transformer**([Transformer](../workflow/workflow_config.md#type-alias-openjiuwencoreworkflowworkflow_configtransformercallableany-any), 可选)：输出数据转换器，负责在组件产生结果后进行格式转换或后处理，允许开发者注入自定义逻辑。默认值：`None`。
- **kwargs**：预留参数，配置不生效。

> **说明**
>
> - inputs_schema和inputs_transformer的配置可参见开发文档中的要求，取值可引用上游组件的输出；outputs_schema和outputs_transformer的配置取值可使用组件本身输出。
> - inputs_schema和inputs_transformer均未配置时表示透传所有输入；outputs_schema和outputs_transformer均未配置时表示输出格式为组件自身输出。
> - schema和transform同时配置时，只有transformer生效。

**样例**：

```python
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # 自定义组件AddTenNode， 每次调用，对于inputs中的source累加10
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {"result": inputs["source"] + 10}
>>>
>>> # 创建循环体
>>> loop_group = LoopGroup()
>>> # 添加第一个组件，处理循环数组中的当前项
>>> # AddTenNode 是一个简单的组件，将输入的 source 字段值增加 10 并输出到 result 字段
>>> loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.item}"})
>>> # 添加第二个组件，处理中间变量
>>> loop_group.add_workflow_comp("2", AddTenNode("2"), inputs_schema={"source": "${l.user_var}"})
```

### start_nodes

```python
start_nodes(nodes: list[str]) -> Self
```

设置循环体的起始组件。

**参数**：

- **nodes**(list[str])：起始组件标识符列表。当前只支持设置一个起始组件，`nodes`列表中不可存在`None`值。示例：`['start_node']`。

**样例：**

```python
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # 设置循环体的起始组件
>>> loop_group = LoopGroup()
>>> loop_group.add_workflow_comp("1", AddTenNode("1"))
>>> loop_group.add_workflow_comp("2", AddTenNode("2"))
>>> # 指定组件"1"作为循环的起始组件
>>> loop_group.start_nodes(["1"])
```

### end_nodes

```python
end_nodes(nodes: list[str]) -> Self
```

设置循环体的结束组件。

**参数**：

- **nodes**(list[str])：结束组件标识符列表。当前只支持设置一个结束组件，`nodes`列表中不可存在`None`值。示例：`['end_node']`。

**样例**：

```python
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # 设置循环体的结束组件
>>> loop_group = LoopGroup()
>>> loop_group.add_workflow_comp("1", AddTenNode("1"))
>>> loop_group.add_workflow_comp("2", AddTenNode("2"))
>>> # 指定组件"2"作为循环的结束组件
>>> loop_group.end_nodes(["2"])
```

## class openjiuwen.core.component.loop_comp.LoopType

循环类型枚举类，定义了支持的循环类型。

- **Array**：数组循环，对数组中的每个元素执行循环。值为"array"。
- **Number**：数值循环，执行指定次数的循环。值为"number"。
- **AlwaysTrue**：无限循环，一直执行直到被中断。值为"always_true"。
- **Expression**：表达式循环，根据表达式结果决定是否继续循环。值为"expression"。

## class openjiuwen.core.component.loop_comp.LoopComponent

```python
class openjiuwen.core.component.loop_comp.LoopComponent(loop_group: LoopGroup, output_schema: dict)
```

标准循环组件类，是对循环功能的高级封装，提供了更简洁的使用方式。通过LoopComponent，可以方便地实现数组循环、数值循环等多种循环模式，并支持循环中断、中间变量传递等高级功能。

**参数**：

- **loop_group**([LoopGroup](#class-openjiuwencorecomponentloop_comploopgroup))：循环组实例，定义了循环体内要执行的组件。循环组中可以包含多个组件，并通过连接关系定义它们的执行顺序。`loop_group`内至少包含一个组件。
- **output_schema**(dict)：输出模式定义，用于从循环结果中提取特定字段。键为输出字段名，值为字段值的表达式路径。例如：`{"results": "${1.result}", "user_var": "${l.user_var}"}`表示将循环体内组件"1"的result字段和中间变量"user_var"作为循环组件的输出。

> **说明**
>
> 1. **循环体常用组件**：在循环功能实现中，通常需要与以下组件配合使用：
>
>    - [BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent)：用于控制循环的中断，当执行到此组件时，循环将立即停止。
>    - [SetVariableComponent](./set_variable_comp.md#class-openjiuwencorecomponentset_variable_compsetvariablecomponent)：用于在循环过程中设置变量值，支持引用路径和嵌套结构变量的设置。
> 2. **循环变量作用域**：循环内部的变量仅在循环内部可见，外部组件无法直接访问。
> 3. **中间变量初始化**：使用LoopComponent的intermediate_var参数可以在循环开始前初始化中间变量，确保循环逻辑的正确性。
> 4. **循环中断机制**：
>
>    - 使用BreakComponent时，需要在LoopComponent的循环体中正确配置中断逻辑。
>    - 循环中断后，已收集的结果仍会被保留并返回。
>    - 详细信息请参考[BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent)。
> 5. **循环条件类型**：根据不同的循环需求选择合适的循环类型：
>
>    - array：适用于需要遍历数组的场景。
>    - always_true：适用于需要无限循环直到显式中断的场景。
> 6. **性能考虑**：对于大数据集的循环，应注意内存使用和执行效率，避免在循环体中执行过于复杂的操作。

**样例**：

下面的示例展示了如何使用LoopComponent配合AlwaysTrue条件和BreakComponent实现需要在特定条件下中断的无限循环。

**注意**：AlwaysTrue条件会使循环持续执行，直到BreakComponent显式中断循环。详细信息请参考[BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent)。

```python
>>> import asyncio
>>>
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.break_comp import BreakComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.loop_comp import LoopComponent, LoopGroup
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>>
>>> # 通用节点组件，返回输入值
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {"output": inputs["value"]}
>>>
>>> # 创建LoopGroup
>>> loop_group = LoopGroup()
>>>
>>> # 创建通用节点作为循环体核心组件
>>> class commonNode(CommonNode):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         # 模拟循环体的工作，返回结果
...         return {"output": True}
>>>
>>> # 为LoopGroup添加工作流组件
>>> loop_group.add_workflow_comp("a", commonNode())
>>>
>>> # 创建分支组件用于条件判断
>>> branch_component = BranchComponent()
>>> loop_group.add_workflow_comp("branch", branch_component)
>>>
>>> # 创建变量设置组件，递增user_var
>>> set_variable_component = SetVariableComponent({"user_var": "${loop.user_var} + 1"})
>>> loop_group.add_workflow_comp("setVar", set_variable_component)
>>>
>>> # 创建终止循环组件
>>> break_node = BreakComponent()
>>> loop_group.add_workflow_comp("break", break_node)
>>>
>>> # 指定组件"a"为循环开始，组件"setVar"为正常循环结束
>>> loop_group.start_nodes(["a"])
>>> loop_group.end_nodes(["setVar"])
>>>
>>> # 设置BranchComponent的分支条件
>>> # 分支1: 继续循环，执行setVariableComponent
>>> branch_component.add_branch("${loop.index} < 2", ["setVar"])
>>> # 分支2: 终止循环，执行break组件
>>> branch_component.add_branch("${loop.index} >= 2", ["break"])
>>>
>>> # 设置组件连接
>>> loop_group.add_connection("a", "branch")
>>>
>>> # 创建LoopComponent，设置输出模式，捕获最终的中间变量、循环计数和循环结果
>>> loop_component = LoopComponent(
...     loop_group,
...     {
...         "user_var": "${loop.user_var}",
...         "loop_count": "${loop.index}",
...         "results": "${a.output}"
...     }
... )
>>>
>>> # 创建工作流实例
>>> workflow = Workflow()
>>>
>>> # 添加开始组件
>>> workflow.set_start_comp("s", Start({}))
>>>
>>> # 添加结束组件，引用loop组件的输出结果
>>> workflow.set_end_comp("e", End({}),
...                        inputs_schema={
...                            "user_var": "${loop.user_var}",
...                            "loop_count": "${loop.loop_count}",
...                            "results": "${loop.results}"
...                        })
>>>
>>> # 添加循环组件，设置为always_true循环类型和中间变量初始值
>>> workflow.add_workflow_comp("loop", loop_component,
...                               inputs_schema={
...                                   "loop_type": "always_true",
...                                   "intermediate_var": {"user_var": 0}
...                               })
>>>
>>> # 串行连接组件：start->loop->end
>>> workflow.add_connection("s", "loop")
>>> workflow.add_connection("loop", "e")
>>>
>>> # 调用invoke方法执行工作流
>>> result = asyncio.run(workflow.invoke({}, WorkflowRuntime()))
>>>
>>> print(f"执行结果: {result.result}")
>>> output = result.result.get('output', {})
>>>
>>> # 验证循环执行了3次
>>> assert output.get("loop_count") == 3, f"Expected loop_count == 3, got {output.get('loop_count')}"
>>>
>>> # 验证每个循环的执行结果
>>> expected_results = [True, True, True]
>>> assert output.get("results") == expected_results, f"Expected {expected_results}, got {output.get('results')}"
```
