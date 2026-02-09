# openjiuwen.core.runtime.resources_manager.workflow_manager

## class openjiuwen.core.runtime.resources_manager.workflow_manager.WorkflowMgr

```python
class openjiuwen.core.runtime.resources_manager.workflow_manager.WorkflowMgr()
```

工作流资源管理类，管理工作流实例的注册、查找和移除，支持工作流工具信息获取。


### add_workflow

```python
def add_workflow(workflow_id: str, workflow: Union[Workflow, WorkflowProvider]) -> None
```

向资源管理器中添加工作流实例或提供者，建立ID与工作流实例的映射关系。

**参数**:

- **workflow_id**(str): 工作流的唯一标识符。
- **workflow**(Union[Workflow, WorkflowProvider]): 工作流实例或提供者。
	- **WorkflowProvider**: `Callable[[], Workflow]` 类型，工作流实例的延迟加载工厂函数，用于按需创建工作流对象，实现资源的惰性初始化，提高系统资源管理效率和类型安全性。

**样例**:

```python
>>> # 创建真实工作流实例
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # 创建工作流管理实例
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # 创建基础工作流
>>> workflow = Workflow()
>>> 
>>> # 设置工作流组件
>>> # 创建简单的输入组件
>>> start_config = {
...     "inputs": [
...         {"id": "user_input", "required": True}
...     ]
>>> }
>>> workflow.set_start_comp("start", Start(conf=start_config))
>>> 
>>> # 添加输出组件
>>> workflow.set_end_comp("end", End())
>>> 
>>> # 添加连接关系
>>> workflow.add_connection("start", "end")
>>> 
>>> # 添加工作流实例到管理器
>>> workflow_mgr.add_workflow("test_workflow", workflow)

>>> print("Workflow added successfully")
Workflow added successfully
```

### add_workflows

```python
def add_workflows(workflows: List[Tuple[str, Union[Workflow, WorkflowProvider]]]) -> None
```

批量向资源管理器添加工作流实例，建立ID与工作流实例的映射关系。

**参数**:

- **workflows**(List[Tuple[str, Union[Workflow, WorkflowProvider]]]): 工作流列表，每个元素为(工作流ID, 工作流实例)的元组。

**样例**:

```python
>>> # 创建真实工作流实例
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> 
>>> # 创建工作流管理实例
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # 创建多个工作流实例
>>> workflow1 = Workflow()
>>> workflow1.set_start_comp("start1", Start(conf={"inputs": [{"id": "input1", "required": True}]}))
>>> workflow1.set_end_comp("end1", End())
>>> workflow1.add_connection("start1", "end1")
>>> 
>>> workflow2 = Workflow()
>>> workflow2.set_start_comp("start2", Start(conf={"inputs": [{"id": "input2", "required": True}]}))
>>> workflow2.set_end_comp("end2", End())
>>> workflow2.add_connection("start2", "end2")
>>> 
>>> # 批量添加工作流
>>> workflows_list = [
...     ("workflow1", workflow1),
...     ("workflow2", workflow2)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> print("Workflows added successfully")
Workflows added successfully
```

### get_workflow

```python
def get_workflow(workflow_id: str, runtime=None) -> Workflow
```

从资源管理器中获取指定的工作流实例。支持延迟加载和执行跟踪。

**参数**:

- **workflow_id**(str): 工作流的唯一标识符。
- **runtime**(可选): 运行时环境实例。

**返回**:

- **Workflow**: 对应的工作流实例。

**样例**:

```python
>>> # 创建真实工作流实例
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # 创建工作流管理实例
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # 创建多个工作流实例
>>> workflow1 = Workflow()
>>> workflow1.set_start_comp("start1", Start(conf={"inputs": [{"id": "input1", "required": True}]}))
>>> workflow1.set_end_comp("end1", End())
>>> workflow1.add_connection("start1", "end1")
>>> 
>>> workflow2 = Workflow()
>>> workflow2.set_start_comp("start2", Start(conf={"inputs": [{"id": "input2", "required": True}]}))
>>> workflow2.set_end_comp("end2", End())
>>> workflow2.add_connection("start2", "end2")
>>> 
>>> # 批量添加工作流
>>> workflows_list = [
...     ("workflow1", workflow1),
...     ("workflow2", workflow2)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> 
workflow = workflow_mgr.get_workflow("workflow1")
if workflow:
    print("Workflow got successfully")
Workflow got successfully
```

### remove_workflow

```python
def remove_workflow(workflow_key: str) -> Optional[Workflow]
```

从资源管理器中移除指定的工作流实例。

**参数**:

- **workflow_key**(str): 工作流的键，通常为工作流ID或由generate_workflow_key生成的键。

**返回**:

- **Optional[Workflow]**: 被移除的工作流实例，若不存在则返回None。

**样例**:

```python
>>> # 创建真实工作流实例
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # 创建工作流管理实例
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # 创建多个工作流实例
>>> workflow1 = Workflow()
>>> workflow1.set_start_comp("start1", Start(conf={"inputs": [{"id": "input1", "required": True}]}))
>>> workflow1.set_end_comp("end1", End())
>>> workflow1.add_connection("start1", "end1")
>>> 
>>> workflow2 = Workflow()
>>> workflow2.set_start_comp("start2", Start(conf={"inputs": [{"id": "input2", "required": True}]}))
>>> workflow2.set_end_comp("end2", End())
>>> workflow2.add_connection("start2", "end2")
>>> 
>>> # 批量添加工作流
>>> workflows_list = [
...     ("workflow1", workflow1),
...     ("workflow2", workflow2)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> 
>>> # 移除工作流实例
>>> removed_workflow = workflow_mgr.remove_workflow("workflow2")
>>> print(f"移除工作流: {removed_workflow is not None}")
移除工作流: True
```

### get_tool_infos

```python
def get_tool_infos() -> List[Dict[str, Any]]
```

获取工作流工具信息列表。

**返回**:

- **List[Dict[str, Any]]**: 工作流工具信息列表，每个元素包含工作流的元数据。

**样例**:

```python
>>> # 创建真实工作流实例
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # 创建工作流管理实例
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # 创建多个工作流实例
>>> workflow1 = Workflow()
>>> workflow1.set_start_comp("start1", Start(conf={"inputs": [{"id": "input1", "required": True}]}))
>>> workflow1.set_end_comp("end1", End())
>>> workflow1.add_connection("start1", "end1")
>>> 
>>> # 批量添加工作流
>>> workflows_list = [
...     ("workflow1", workflow1)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> 
>>> # 获取工作流工具信息
>>> workflow_infos = workflow_mgr.get_tool_infos()
>>> print(f"工作流工具数量: {len(workflow_infos)}")
>>> for info in workflow_infos:
...     print(f"工作流工具类型: {info.type}")
工作流工具数量: 1
工作流工具类型: function
```
### generate_workflow_key

```python
def generate_workflow_key(workflow_id: str, version: Optional[int] = None) -> str
```

生成工作流的唯一键。

**参数**:

- **workflow_id**(str): 工作流的唯一标识符。
- **version**(str): 工作流的版本号。

**返回**:

- **str**: 生成的工作流键。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import generate_workflow_key
>>> # 生成工作流键示例
>>> key1 = generate_workflow_key("text_processing", 1)
>>> print(f"工作流键1: {key1}")
# 工作流键1: text_processing_1
```