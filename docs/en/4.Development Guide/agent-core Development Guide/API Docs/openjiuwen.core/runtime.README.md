# runtime

`openjiuwen.core.runtime` is the core execution engine and management framework for Agents and Workflows in the openJiuwen framework. It provides an isolated and stable contextual environment for task execution. By abstracting the complexity of underlying infrastructure, the Runtime enables unified scheduling and governance across the full task lifecycle.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [ComponentExecutable](./runtime/base.md) | Abstract class for component executors. |
| [Runtime](./runtime/runtime.md) | Core runtime operation class for Agent and Workflow execution. |
| [WorkflowRuntime](./runtime/workflow.md) | Core runtime context for workflow execution; a specialised implementation of `Runtime` for workflow scenarios. |
| [InteractiveInput](./runtime/interaction.md) | Class for constructing user–workflow interactive inputs in interruption scenarios. |
| [InteractionOutput](./runtime/interaction.md) | Data class representing interaction outputs between the workflow and the user. |
