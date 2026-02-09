# openjiuwen.core.component.set_variable_comp

## class openjiuwen.core.component.set_variable_comp.SetVariableComponent

```python
class openjiuwen.core.component.set_variable_comp.SetVariableComponent(variable_mapping: dict[str, Any])
```

`SetVariableComponent` 是openJiuwen内置的工作流的变量赋值组件，该组件提供了配置变量映射、动态设置和管理变量的能力，用于实现工作流中数据的动态传递和状态管理。该组件也支持在循环组件[LoopComponent](./loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent)内部使用，通过变量赋值组件，可以实现循环过程中数据的动态更新和传递。

**参数**：

* **variable_mapping**(dict[str, Any])：变量映射字典，定义了要设置的变量名称和对应的变量取值，不可取值为`None`。该映射字典支持设置一个或多个键值对，键值对支持的类型如下所示：
  * 变量映射的键支持以下3种类型：

    | 类型| 描述 |  示例 |
    | :---: |  :---: |  :---: |
    | 非引用形式变量名称 | 字符串，直接获取变量名称 | `"node_a.var_value"` |
    | 单层引用形式变量名称 | 字符串，通过`"${variable_path}"`占位符语法取出变量名称，引用路径以符号`.`进行分割，只有单层路径 | `"${node_a.var_value}"`取出变量名称即`"node_a.var_value"` |
    | 嵌套引用形式变量名称 |字符串，通过`"${variable_path}"`占位符语法取出变量名称，引用路径以符号`.`进行分割，有多层路径  | `"${node_a.nested.var_value}"`取出变量名称即`"node_a.nested.var_value"` |

  * 变量映射的值支持以下3种类型：

    | 类型| 描述 |  示例 |
    | :---: |  :---: |  :---: |
    | 固定值 | 直接输入文本、数字等静态数据 | `"hello world"`、`123`等|
    | 单层动态引用 | 通过`"${variable_path}"`占位符语法取出变量动态值，引用路径以符号`.`进行分割，只有单层路径 | 假设`node_b.var_value = "hello world"`，则`"${node_b.var_value}"`取出变量动态值即`"hello world"` |
    | 嵌套动态引用 | 通过`"${variable_path}"`占位符语法取出变量动态值，引用路径以符号`.`进行分割，有多层路径 | 假设`node_b.nested = {"var_value": 123}`，则`"${node_b.nested.var_value}"`取出变量动态值即`123` |

**异常**：

* **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

* 样例1：
  
```python
>>> # 在循环体中使用`SetVariableComponent`设置中间变量
>>> import asyncio
>>> from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> 
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return inputs
... 
...     async def stream(self, inputs, runtime: Runtime, context: Context):
...         yield await self.invoke(inputs, runtime, context)
>>> 
>>> 
>>> # 创建工作流
>>> flow = Workflow()
>>> # MockStartNode: 工作流的起始节点，简单地将输入数据传递给下一个节点
>>> flow.set_start_comp("s", Start())
>>> # MockEndNode: 工作流的结束节点，收集并返回工作流的最终结果
>>> flow.set_end_comp("e", End(), inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
>>> # CommonNode: 通用节点，将输入数据原样返回
>>> flow.add_workflow_comp("a", CommonNode("a"))
>>> flow.add_workflow_comp("b", CommonNode("b"),
>>>                        inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})
>>> 
>>> # 创建循环体
>>> loop_group = LoopGroup()
>>> # AddTenNode: 特殊节点，将输入的source字段值加10后返回
>>> loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.index}"})
>>> loop_group.add_workflow_comp("2", AddTenNode("2"), inputs_schema={"source": "${l.user_var}"})
>>> # 使用SetVariableComponent设置中间变量
>>> set_variable_component = SetVariableComponent({"${l.user_var}": "${2.result}"})
>>> loop_group.add_workflow_comp("3", set_variable_component)
>>> loop_group.start_nodes(["1"])
>>> loop_group.end_nodes(["3"])
>>> loop_group.add_connection("1", "2")
>>> loop_group.add_connection("2", "3")
>>> 
>>> # 创建LoopComponent
>>> loop_component = LoopComponent(loop_group, {"results": "${1.result}", "user_var": "${l.user_var}"})
>>> 
>>> # 添加到工作流
>>> flow.add_workflow_comp("l", loop_component, inputs_schema={"loop_type": "number", "loop_number": 3,
>>>                                                            "intermediate_var": {"user_var": "${input_number}"}})
>>> 
>>> # 设置连接
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "l")
>>> flow.add_connection("l", "b")
>>> flow.add_connection("b", "e")
>>> 
>>> 
>>> async def run_workflow():
...     return await flow.invoke({"input_number": 2}, WorkflowRuntime())
>>> 
>>> 
>>> if __name__ == "__main__":
...     # 执行测试
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'array_result': [10, 11, 12], 'user_var': 32}}
```

* 样例2：
```python
>>> # 在循环体中使用`SetVariableComponent`设置中间变量
>>> import asyncio
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> 
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return inputs
... 
...     async def stream(self, inputs, runtime: Runtime, context: Context):
...         yield await self.invoke(inputs, runtime, context)
>>> 
>>> 
>>> flow = Workflow()
>>> flow.set_start_comp("s", Start())
>>> flow.set_end_comp("e", End(), inputs_schema={"result": "${a.nested.value}"})
>>> 
>>>  # 创建SetVariableComponent，设置嵌套结构变量
>>> set_variable_component = SetVariableComponent({"${a.nested.value}": 123})
>>> flow.add_workflow_comp("a", set_variable_component)
>>> 
>>>  # 设置连接
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "e")
>>> 
>>> 
>>> async def run_workflow():
...     return await flow.invoke({"input_number": 2}, WorkflowRuntime())
>>> 
>>> 
>>> if __name__ == "__main__":
...     # 执行测试
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'result': 123}}
```

* 样例3：
  
```python
>>> import asyncio
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> flow = Workflow()
>>> flow.set_start_comp("s", Start(), inputs_schema={"input_value": "${input_value}"})
>>> flow.set_end_comp("e", End(), inputs_schema={"result": "${c.result}"})
>>> 
>>>  # 创建计算节点
>>>  # AddTenNode: 特殊节点，将输入的source字段值加10后返回
>>> flow.add_workflow_comp("a", AddTenNode("a"), inputs_schema={"source": "${s.input_value}"})
>>> 
>>>  # 使用SetVariableComponent通过引用路径设置变量
>>> set_variable_component = SetVariableComponent({"${b.value}": "${a.result}"})
>>> flow.add_workflow_comp("b", set_variable_component)
>>> 
>>>  # 创建另一个计算节点，使用设置的变量
>>> flow.add_workflow_comp("c", AddTenNode("c"), inputs_schema={"source": "${b.value}"})
>>> 
>>>  # 设置连接
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "b")
>>> flow.add_connection("b", "c")
>>> flow.add_connection("c", "e")
>>> 
>>>  # 执行测试
>>> async def run_workflow():
...       return await flow.invoke({"input_value": 5}, WorkflowRuntime())
>>> 
>>> if __name__ == "__main__":
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'result': 25}}
```
