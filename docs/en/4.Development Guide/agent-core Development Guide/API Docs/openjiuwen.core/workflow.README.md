# workflow

`openjiuwen.core.workflow` is the foundational module in the openJiuwen framework that supports workflow orchestration and execution. A workflow refers to a mechanism in which multiple components or Agents collaborate in an orderly manner according to a pre-designed orchestration process to complete complex tasks, with the goal of improving the efficiency and stability of complex task processing.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [WorkflowSpec](./workflow/workflow_config.md) | Defines the workflow structure and relationships between components. It contains an internal graph structure and is not recommended for users to configure manually. |
| [WorkflowMetadata](./workflow/workflow_config.md) | Data class for workflow metadata, used to describe the basic properties of a workflow. |
| [ComponentAbility](./workflow/workflow_config.md) | Enumeration class defining the capabilities of workflow components. |
| [WorkflowInputsSchema](./workflow/workflow_config.md) | Input parameter schema for workflow tool plugins. |
| [WorkflowConfig](./workflow/workflow_config.md) | Configuration structure data class. |
| [WorkflowOutput](./workflow/base.md) | Data class representing the output result of a workflow execution via `invoke`. |
| [WorkflowChunk](./workflow/base.md) | Data class representing a data frame returned from streaming workflow execution. |
| [WorkflowExecutionState](./workflow/base.md) | Enumeration class defining execution states for workflow `invoke`. |
| [Workflow](./workflow/base.md) | Workflow class. |
