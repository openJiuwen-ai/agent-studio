# openjiuwen.core.runtime.workflow

## class openjiuwen.core.runtime.workflow.WorkflowRuntime

```python
class openjiuwen.core.runtime.WorkflowRuntime(workflow_id="", parent: BaseRuntime=None, session_id: str=None, state: State=None, context: Context=None)
```

The core runtime context for workflow execution, a workflow-specific implementation of Runtime. It provides state management, configuration, storage, and traceability for workflow scenarios.

**Parameters**:

- **workflow_id** (str, optional): The workflow ID. Default: "".
- **parent** (BaseRuntime, optional): The core runtime type in the openJiuwen framework. Default: None. Not recommended to set.
- **session_id** (str, optional): Unique session identifier. Default: None; a UUID is generated automatically if not provided.
- **state** (State, optional): State storage engine. Default: None; an in-memory implementation (InMemoryState) is created by default. Not recommended to set.
- **context** (Context, optional): Context engine for storing user conversation data. Default: None, which disables the context engine.

**Examples**:

```python
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> 
>>> # The following two construction methods are recommended
>>> runtime = WorkflowRuntime()
>>> runtime2 = WorkflowRuntime(workflow_id="123", session_id="abc", context=None)
>>> print("WorkflowRuntime created successfully")
WorkflowRuntime created successfully
```