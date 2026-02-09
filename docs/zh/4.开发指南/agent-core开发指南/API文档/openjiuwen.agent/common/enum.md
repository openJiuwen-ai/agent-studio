# openjiuwen.agent.common.enum

## class openjiuwen.agent.common.enum.ControllerType

定义了控制器的类型。

- **ReActController**：ReAct类型的控制器。
- **WorkflowController**：Workflow类型的控制器。
- **Undefined**：未定义的控制器。

## class openjiuwen.agent.common.enum.TaskType

定义了子任务的类型。

- **PLUGIN**：插件类型的子任务。
- **WORKFLOW**：工作流类型的子任务。
- **MCP**：MCP类型的子任务。
- **UNDEFINED**：未定义的子任务类型。

## class openjiuwen.agent.common.enum.TaskStatus

定义了任务的执行状态。

- **PENDING**：已创建，尚未开始。
- **RUNNING**：正在执行。
- **SUCCESS**：成功结束。
- **FAILED**：异常结束。
- **CANCELLED**：被取消。
- **INTERRUPTED**：中断，等待用户输入。

## class openjiuwen.agent.common.enum.ReActControllerStatus

定义了ReAct控制器的状态。

- **NORMAL**：正常运行状态。
- **INTERRUPTED**：中断状态。
- **COMPLETED**：完成状态。
- **TIMEOUT**：超时状态。
