# openjiuwen.core.component.base

## class openjiuwen.core.component.base.WorkflowComponent

`WorkflowComponent`是自定义工作流组件的抽象基类。所有自定义组件需继承该类，并实现将自身加入图以及转换为可执行单元（`ComponentExecutable`）的逻辑。

### add_component

```python
add_component(graph: Graph, node_id: str, wait_for_all: bool = False)
```

定义如何将当前组件加入到指定`graph`。

**参数**：

- **graph**([Graph](../graph/base.md#class-graph))：`workflow`的`graph`实例。
- **node_id**(str)：本组件在`graph`中唯一的`node_id`。
- **wait_for_all**(bool)：本组件是否需要等待前置组件全部执行完成，`True`表示等待，`False`表示不等待。默认值：`False`。

**样例**：

```python
>>> import asyncio
>>> import random
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.branch_router import BranchRouter
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> # 自定义组件`CustomIntentComponent`实现了`add_component`接口，用于为本组件定制内置的条件边，并自定义实现了接口`add_branch`用于绑定内置条件边的目标节点。
>>> # 创建自定义组件，并实现add_component接口
>>> class CustomIntentComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, default_intents):
...         super().__init__()
...         self._intents = default_intents
...         self._router = BranchRouter()
... 
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
...         graph.add_conditional_edges(node_id, self._router)
... 
...     def add_branch(self, condition: str, target: list[str], branch_id:str):
...         self._router.add_branch(condition=condition, target=target, branch_id=branch_id)
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         self._router.set_runtime(runtime)
...         return {'result': self._intents[random.randint(0, len(self._intents) - 1)]}
>>> 
>>> 
>>> class TravelComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, node_id):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'[{self.node_id}] inputs = {inputs}')
...         return inputs
>>> 
>>> 
>>> class EatComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, node_id):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'[{self.node_id}] inputs = {inputs}')
...         return inputs
>>> 
>>> 
>>> async def run_workflow():
...     # 创建工作流
...     flow = Workflow()
...     flow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
... 
...     intent_component = CustomIntentComponent(["出行", "餐饮"])
...     intent_component.add_branch(condition="${intent.result} == '出行'", target=['travel'], branch_id='1')
...     intent_component.add_branch(condition="${intent.result} == '餐饮'", target=['eat'], branch_id='2')
...     flow.add_workflow_comp("intent", intent_component, inputs_schema={"query": "${start.query}"})
...     flow.add_workflow_comp("eat", EatComponent("eat"), inputs_schema={"intent": '${intent.result}'})
...     flow.add_workflow_comp("travel", TravelComponent("travel"), inputs_schema={"intent": '${intent.result}'})
...     flow.set_end_comp("end", End(), inputs_schema={"eat": "${eat.intent}", "travel": "${travel.intent}"})
...     flow.add_connection("start", "intent")
...     flow.add_connection("eat", "end")
...     flow.add_connection("travel", "end")
... 
...     runtime = WorkflowRuntime()
...     output = await flow.invoke({"user_inputs": {"query": "去新疆"}}, runtime)
...     print(output.result)
>>> 
>>> if __name__ == '__main__':
...     asyncio.get_event_loop().run_until_complete(run_workflow())
[travel] inputs = {'intent': '出行'}
{'output': {'travel': '出行'}}
```

### to_executable

```python
to_executable() -> Executable
```

返回该组件对应的可执行实例，openJiuwen支持用户自定义实现`ComponentExecutable`，作为本接口的返回，用于运行时调度执行。

**返回**：

**[Executable](../graph/base.md)**，本组件的执行实例。

**样例**：

```python

>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # `CalculateComponent`继承`WorkflowComponent`，是用于数学运算的组件，实现`to_executable`方法提供了实现计算逻辑的`ComputeExecutor`实例，实现`add_component`方法将`CalculateComponent`节点添加到工作流中。
>>> # 创建自定义组件，并实现to_executable接口
>>> class CalculateComponent(WorkflowComponent):
...     def to_executable(self) -> Executable:
...         return ComputeExecutor()
>>> 
>>> class ComputeExecutor(ComponentExecutable):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {'result': self.__calculate__(data=inputs.get('data'))}
... 
...     def __calculate__(self, data):
...         operator = data.get('operator')
...         a = data.get('a')
...         b = data.get('b')
...         if operator == 'add':
...             return a + b
...         if operator == 'multiply':
...             return a * b
...         if operator == 'substract':
...             return a - b
...         return a / b
>>> 
>>> async def run_workflow():
...     # 创建工作流，并执行
...     flow = Workflow()
...     flow.set_start_comp("start", Start(), inputs_schema={"a": "${user_inputs.a}", "b": "${user_inputs.b}", "operator": "${user_inputs.operator}"})
...     flow.add_workflow_comp("compute", CalculateComponent(), inputs_schema={"data": "${start}"})
...     flow.set_end_comp("end", End(), inputs_schema={"result": "${compute.result}"})
...     flow.add_connection("start", "compute")
...     flow.add_connection("compute", "end")
...     runtime = WorkflowRuntime()
...     output = await flow.invoke({"user_inputs": {"a": 1, "b": 2, "operator": "add"}}, runtime)
...     print(output.result)
>>> 
>>> 
>>> if __name__ == '__main__':
...     asyncio.run(run_workflow())
{'output': {'result': 3}}
```
