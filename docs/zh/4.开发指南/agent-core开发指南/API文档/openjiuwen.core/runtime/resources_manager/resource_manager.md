# openjiuwen.core.runtime.resources_manager.resource_manager

## class openjiuwen.core.runtime.resources_manager.resource_manager.ResourceMgr

```python
class openjiuwen.core.runtime.resources_manager.resource_manager.ResourceMgr()
```

资源管理器实现类，管理模型、工作流、Prompt、工具等资源的生命周期，统一提供各种资源管理器的访问接口。

### tool

```python
def tool() -> ToolMgr
```

获取ToolMgr实例。

**返回**:

- **ToolMgr**: ToolMgr实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # 创建资源管理器实例
>>> resource_mgr = ResourceMgr()
>>>
>>> # 获取工具管理器
>>> tool_mgr = resource_mgr.tool()
>>> print(f"Tool manager found: {tool_mgr is not None}")
>>> print(f"Tool manager type: {type(tool_mgr).__name__}")
Tool manager found: True
Tool manager type: ToolMgr
```

### prompt

```python
def prompt() -> PromptMgr
```

获取提示词管理器实例，用于管理和操作Prompt模板资源。

**返回**:

- **PromptMgr**: 提示词管理器实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # 创建资源管理器实例
>>> resource_mgr = ResourceMgr()
>>>
>>> # 获取提示管理器
>>> prompt_mgr = resource_mgr.prompt()
>>> print(f"Prompt manager found: {prompt_mgr is not None}")
>>> print(f"PromptMgr type: {type(prompt_mgr).__name__}")
Prompt manager found: True
PromptMgr type: PromptMgr
```

### model

```python
def model() -> ModelMgr
```

获取模型管理器实例，用于管理和操作模型资源。

**返回**:

- **ModelMgr**: 模型管理器实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # 创建资源管理器实例
>>> resource_mgr = ResourceMgr()
>>>
>>> # 获取模型管理器
>>> model_mgr = resource_mgr.model()
>>> print(f"Model manager found: {model_mgr is not None}")
>>> print(f"ModelMgr type: {type(model_mgr).__name__}")
Model manager found: True
ModelMgr type: ModelMgr
```

### workflow

```python
def workflow() -> WorkflowMgr
```

获取工作流管理器实例，用于管理和操作工作流资源。

**返回**:

- **WorkflowMgr**: 工作流管理器实例。

**样例**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # 创建资源管理器实例
>>> resource_mgr = ResourceMgr()
>>>
>>> # 获取工作流管理器
>>> workflow_mgr = resource_mgr.workflow()
>>> print(f"Workflow manager found: {workflow_mgr is not None}")
>>> print(f"WorkflowMgr type: {type(workflow_mgr).__name__}")
Workflow manager found: True
WorkflowMgr type: WorkflowMgr
```