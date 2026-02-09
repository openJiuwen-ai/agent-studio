# openjiuwen.core.runtime.resources_manager.resource_manager

## class openjiuwen.core.runtime.resources_manager.resource_manager.ResourceMgr

```python
class openjiuwen.core.runtime.resources_manager.resource_manager.ResourceMgr()
```

Resource manager implementation that manages the lifecycle of resources such as models, workflows, prompts, and tools, and provides unified access to the respective resource managers.

### tool

```python
def tool() -> ToolMgr
```

Get a ToolMgr instance.

**Returns**:

- **ToolMgr**: The ToolMgr instance.

**Examples**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # Create a resource manager instance
>>> resource_mgr = ResourceMgr()
>>>
>>> # Get the tool manager
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

Get a PromptMgr instance for managing and operating Prompt template resources.

**Returns**:

- PromptMgr: The Prompt manager instance.

**Examples**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # Create a resource manager instance
>>> resource_mgr = ResourceMgr()
>>>
>>> # Get the prompt manager
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

Get a ModelMgr instance for managing and operating model resources.

**Returns**:

- ModelMgr: The model manager instance.

**Examples**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # Create a resource manager instance
>>> resource_mgr = ResourceMgr()
>>>
>>> # Get the model manager
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

Get a WorkflowMgr instance for managing and operating workflow resources.

**Returns**:

- WorkflowMgr: The workflow manager instance.

**Examples**:

```python
>>> from openjiuwen.core.runtime.resources_manager.resource_manager import ResourceMgr
>>>
>>> # Create a resource manager instance
>>> resource_mgr = ResourceMgr()
>>>
>>> # Get the workflow manager
>>> workflow_mgr = resource_mgr.workflow()
>>> print(f"Workflow manager found: {workflow_mgr is not None}")
>>> print(f"WorkflowMgr type: {type(workflow_mgr).__name__}")
Workflow manager found: True
WorkflowMgr type: WorkflowMgr
```