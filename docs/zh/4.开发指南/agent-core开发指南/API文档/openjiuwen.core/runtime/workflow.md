# openjiuwen.core.runtime.workflow

## class openjiuwen.core.runtime.workflow.WorkflowRuntime

```python
class openjiuwen.core.runtime.WorkflowRuntime(workflow_id="", parent: BaseRuntime=None, session_id: str=None, state: State=None, context: Context=None)
```

工作流执行的核心运行时上下文，是`Runtime`的工作流场景的特殊实现，实现了工作流场景下的状态管理、配置、存储及溯源能力。

**参数**：

- **workflow_id**(str, 可选)：工作流的id，默认值：`""`。
- **parent**(BaseRuntime, 可选)：openJiuwen框架内核的runtime类型。默认值：`None`。不推荐设置。
- **session_id**(str, 可选)：会话唯一标识。默认值：`None`，未提供时自动生成 UUID。
- **state**(State, 可选)：状态存储引擎。默认值：`None`，默认创建内存态实现 (`InMemoryState`)。不推荐设置。
- **context** (Context, 可选)：用于存储用户对话信息的上下文引擎对象。默认值：`None`，表示不开启上下文引擎功能。

**样例**：

```python
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> 
>>> # 推荐使用如下两种构造方法
>>> runtime = WorkflowRuntime()
>>> runtime2 = WorkflowRuntime(workflow_id="123", session_id="abc", context=None)
>>> print("WorkflowRuntime created successfully")
WorkflowRuntime created successfully
```
