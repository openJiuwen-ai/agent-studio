# openjiuwen.core.runtime.resources_manager.workflow_manager

## class openjiuwen.core.runtime.resources_manager.workflow_manager.WorkflowMgr

Workflow resource management class that handles registering, retrieving, and removing workflow instances, and provides workflow tool information.

### add_workflow

```python
def add_workflow(workflow_id: str, workflow: Union[Workflow, WorkflowProvider]) -> None
```

Add a workflow instance or provider to the resource manager, establishing a mapping between the ID and the workflow instance.

**Parameters**:

- **workflow_id** (str): The unique identifier of the workflow.
- **workflow** (Union[Workflow, WorkflowProvider]): A workflow instance or provider.
  - WorkflowProvider: A Callable[[], Workflow] that lazily creates a workflow instance on demand, enabling lazy initialization, improved resource efficiency, and type safety.

**Example**:

```python
>>> # Create a real workflow instance
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # Create a workflow manager instance
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # Create a basic workflow
>>> workflow = Workflow()
>>> 
>>> # Configure workflow components
>>> # Create a simple input component
>>> start_config = {
...     "inputs": [
...         {"id": "user_input", "required": True}
...     ]
>>> }
>>> workflow.set_start_comp("start", Start(conf=start_config))
>>> 
>>> # Add an output component
>>> workflow.set_end_comp("end", End())
>>> 
>>> # Add a connection
>>> workflow.add_connection("start", "end")
>>> 
>>> # Add the workflow instance to the manager
>>> workflow_mgr.add_workflow("test_workflow", workflow)

>>> print("Workflow added successfully")
Workflow added successfully
```

### add_workflows

```python
def add_workflows(workflows: List[Tuple[str, Union[Workflow, WorkflowProvider]]]) -> None
```

Add multiple workflow instances to the resource manager in bulk, establishing mappings between IDs and workflow instances.

**Parameters**:

- workflows (List[Tuple[str, Union[Workflow, WorkflowProvider]]]): A list of workflows, where each element is a tuple of (workflow ID, workflow instance).

**Example**:

```python
>>> # Create real workflow instances
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> 
>>> # Create a workflow manager instance
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # Create multiple workflow instances
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
>>> # Batch add workflows
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

Retrieve a specific workflow instance from the resource manager. Supports lazy loading and execution tracing.

**Parameters**:

- workflow_id (str): The unique identifier of the workflow.
- runtime (optional): The runtime environment instance.

**Returns**:

- Workflow: The corresponding workflow instance.

**Example**:

```python
>>> # Create real workflow instances
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # Create a workflow manager instance
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # Create multiple workflow instances
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
>>> # Batch add workflows
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

Remove a specific workflow instance from the resource manager.

**Parameters**:

- workflow_key (str): The workflow key, typically the workflow ID or a key generated by generate_workflow_key.

**Returns**:

- Optional[Workflow]: The removed workflow instance; returns None if it does not exist.

**Example**:

```python
>>> # Create real workflow instances
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # Create a workflow manager instance
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # Create multiple workflow instances
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
>>> # Batch add workflows
>>> workflows_list = [
...     ("workflow1", workflow1),
...     ("workflow2", workflow2)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> 
>>> # Remove a workflow instance
>>> removed_workflow = workflow_mgr.remove_workflow("workflow2")
>>> print(f"Workflow removed: {removed_workflow is not None}")
Workflow removed: True
```

### get_tool_infos

```python
def get_tool_infos() -> List[Dict[str, Any]]
```

Get a list of workflow tool information.

**Returns**:

- List[Dict[str, Any]]: A list of workflow tool information, where each element contains metadata for a workflow.

**Example**:

```python
>>> # Create real workflow instances
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import WorkflowMgr
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> 
>>> # Create a workflow manager instance
>>> workflow_mgr = WorkflowMgr()
>>> 
>>> # Create multiple workflow instances
>>> workflow1 = Workflow()
>>> workflow1.set_start_comp("start1", Start(conf={"inputs": [{"id": "input1", "required": True}]}))
>>> workflow1.set_end_comp("end1", End())
>>> workflow1.add_connection("start1", "end1")
>>> 
>>> # Batch add workflows
>>> workflows_list = [
...     ("workflow1", workflow1)
>>> ]
>>> workflow_mgr.add_workflows(workflows_list)
>>> 
>>> # Get workflow tool information
>>> workflow_infos = workflow_mgr.get_tool_infos()
>>> print(f"Number of workflow tools: {len(workflow_infos)}")
>>> for info in workflow_infos:
...     print(f"Workflow tool type: {info.type}")
Number of workflow tools: 1
Workflow tool type: function
```

### generate_workflow_key

```python
def generate_workflow_key(workflow_id: str, version: Optional[int] = None) -> str
```

Generate a unique workflow key.

**Parameters**:

- workflow_id (str): The unique identifier of the workflow.
- version (str): The workflow version.

**Returns**:

- str: The generated workflow key.

**Example**:

```python
>>> from openjiuwen.core.runtime.resources_manager.workflow_manager import generate_workflow_key
>>> # **Example**: generate a workflow key
>>> key1 = generate_workflow_key("text_processing", 1)
>>> print(f"Workflow key 1: {key1}")
# Workflow key 1: text_processing_1
```