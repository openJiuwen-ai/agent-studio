# openjiuwen.core.graph.base

## class Graph

```python
class openjiuwen.core.graph.base.Graph()
```

The Graph class is the base class for workflow execution graphs. It abstracts the process of building a graph, supports adding start, intermediate, and end nodes, and allows creating regular edges or conditional edges between them. When you implement custom nodes by inheriting WorkflowComponent and provide a custom add_component implementation, you can call Graph methods to control how nodes are added to the Graph.

### start_node

```python
start_node(self, node_id: str) -> Self
```

Specify the start node of the graph and return the current graph instance.

**Parameters:**

- node_id (str): The ID of the start node. If a start node has already been set, it will be overwritten by the current node_id.

Returns:

- Graph: The Graph instance itself.

Exceptions:

- JiuWenBaseException: The base exception class for openJiuwen. For detailed information and solutions, see StatusCode.

Example:

Define a custom node DemoCmpWithRandomStart and implement add_component to randomly choose and set a start node from a predefined list of start node IDs.

```python
>>> import random
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.graph.executable import Input, Output, Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> 
>>> 
>>> class DemoCmpWithRandomStart(WorkflowComponent, ComponentExecutable):
...     def __init__(self, start_ids):
...         super().__init__()
...         self.start_ids:list[str] = start_ids
...  
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         choose_idx = random.randint(0, len(self.start_ids))
...         graph.start_node(self.start_ids[choose_idx])
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
... 
...     def to_executable(self) -> Executable:
...         return self
...
```

### end_node

```python
end_node(self, node_id) -> Self
```

Specify the end node of the graph and return the current graph instance.

Parameters:

- node_id (str): The ID of the end node.

Returns:

- Graph: The Graph instance itself.

Exceptions:

- JiuWenBaseException: The base exception class for openJiuwen. For detailed information and solutions, see StatusCode.

Example:

Define a custom node DemoCmpWithRandomEnd and implement add_component to randomly choose and set an end node from a predefined list of end node IDs.

```python
>>> import random
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.graph.executable import Input, Output, Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> 
>>> 
>>> class DemoCmpWithRandomEnd(WorkflowComponent, ComponentExecutable):
...     def __init__(self, end_ids):
...         super().__init__()
...         self.end_ids:list[str] = end_ids
... 
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         choose_idx = random.randint(0, len(self.end_ids))
...         graph.end_node(self.end_ids[choose_idx])
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
... 
...     def to_executable(self) -> Executable:
...         return self
...
```

### add_node

```python
add_node(self, node_id: str, node: Executable, *, wait_for_all: bool=False) -> Self
```

Add an executable node to the graph and return the current graph instance.

Parameters:

- node_id (str): The node ID.
- node (Executable): The node instance.
- wait_for_all (bool, optional): Whether concurrent execution is supported. True allows concurrent execution and permits the node to run multiple times. False disables concurrency; the node waits for all predecessor nodes to finish before executing. Default: False.

Returns:

- Graph: The Graph instance itself.

Exceptions:

- JiuWenBaseException: The base exception class for openJiuwen. For detailed information and solutions, see StatusCode.

Example:

Define a custom node DemoCmpWithNode and implement add_component to add inner_node as a downstream node.

```python
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.graph.executable import Input, Output, Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> 
>>> 
>>> class DemoCmpWithNode(WorkflowComponent, ComponentExecutable):
...     def __init__(self):
...         super().__init__()
...         self.inner_node = InnerNode()
... 
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
...         graph.add_node("inner", self.inner_node(), wait_for_all=True)
...         graph.add_edge(node_id, "inner")
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
... 
...      def to_executable(self) -> Executable:
...         return self
... 
>>> class InnerNode(ComponentExecutable):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
```

### add_edge

```python
add_edge(self, source_node_id: Union[str, list[str]], target_node_id: str) -> Self
```

Add an edge from the specified source node(s) to the target node. Supports multiple edges from multiple sources to the same target. Returns the current graph instance.

Parameters:

- source_node_id (Union[str, list[str]]): The source node ID(s). If a list is provided, each source node will connect to the target node.
- target_node_id (str): The target node ID.

Returns:

- Graph: The Graph instance itself.

Exceptions:

- JiuWenBaseException: The base exception class for openJiuwen. For detailed information and solutions, see StatusCode.

Example:

Define a custom node DemoCmpWithNode and implement add_component to add inner_node as a downstream node and connect an edge.

```python
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.graph.executable import Input, Output, Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> 
>>> 
>>> class DemoCmpWithNode(WorkflowComponent, ComponentExecutable):
...     def __init__(self):
...         super().__init__()
...         self.inner_node = InnerNode()
... 
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
...         graph.add_node("inner", self.inner_node(), wait_for_all=True)
...         graph.add_edge(node_id, "inner")
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
... 
...     def to_executable(self) -> Executable:
...         return self
... 
>>> class InnerNode(ComponentExecutable):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
```

### add_conditional_edges

```python
add_conditional_edges(self, source_node_id: str, router: Router) -> Self
```

Add conditional edges originating from the source node. The router decides which target node(s) to connect to. Returns the current graph instance.

Parameters:

- source_node_id (str): The source node ID.
- router ([Router](#type-alias-router)): The router for conditional edges, used to determine the target node or list of targets. You can use the built-in BranchRouter or implement your own Router.

Returns:

- Graph: The Graph instance itself.

Exceptions:

- JiuWenBaseException: The base exception class for openJiuwen. For detailed information and solutions, see StatusCode.

Example:

```python
>>> import random
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.branch_router import BranchRouter
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> # Use the built-in Router implementation BranchRouter as the router for conditional edges
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
...
>>> # Pass the condition when creating branches
>>> intent_component = CustomIntentComponent(["travel", "dining"])
>>> intent_component.add_branch(condition="${intent.result} == 'travel'", target=['travel'], branch_id='1')
>>> intent_component.add_branch(condition="${intent.result} == 'dining'", target=['eat'], branch_id='2')
>>> 
>>> flow = Workflow()
>>> flow.add_workflow_comp("intent", intent_component, inputs_schema={"query": "${start.query}"})
```

## type alias Router

```python
openjiuwen.core.graph.base.Router: Union[Callable[..., Union[Hashable, list[Hashable]]], Callable[..., Awaitable[Union[Hashable, list[Hashable]]]],  Runnable[Any, Union[Hashable, list[Hashable]]] ]
```

Router is used by graphs or workflows to determine the target node or list of target nodes for conditional edges.

Example:

```python
>>> from openjiuwen.core.graph.base import Router
>>> 
>>> def router_demo(data):
...     return ["a"]
... 
>>> router:Router = router_demo
```