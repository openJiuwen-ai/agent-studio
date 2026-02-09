# workflow_agent

`openjiuwen.agent.workflow_agent`是openJiuwen中的Agent模块，提供WorkflowAgent的创建和执行等能力。

**Classes**：

| CLASS                                | DESCRIPTION               |
|--------------------------------------| ------------------------- |
| [WorkflowAgent](./workflow_agent.md#class-openjiuwenagentworkflow_agentworkflowagent) | WorkflowAgent是一种专注于多步骤、任务导向的流程自动化Agent，通过严格遵循用户预定义的任务流程高效地执行复杂任务。用户可预先设定清晰的任务步骤、执行条件及角色分工，将任务拆解为多个可执行的子任务或工具，并通过组件间的拓扑连接与数据传递，逐步推进整个工作流，最终输出预期结果。其侧重于基于预设流程实现任务的规范化与高效化执行，适用于任务结构清晰、可分解为多个步骤的场景。        |