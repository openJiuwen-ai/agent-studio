# runtime

`openjiuwen.core.runtime`是openJiuwen框架的智能体与工作流的核心执行引擎与管理框架，它为执行任务提供了一个隔离、稳定的上下文环境。通过抽象底层基础设施的复杂性，Runtime实现了对任务全生命周期的统一调度与治理。

**Classes**：

| CLASS                                 | DESCRIPTION                                                          |
|---------------------------------------|----------------------------------------------------------------------|
| [ComponentExecutable](./runtime/base.md)      | 组件执行器的抽象类。                                                                |
| [Runtime](./runtime/runtime.md)               | Agent、Workflow运行时核心操作类。                                                               |
| [WorkflowRuntime](./runtime/workflow.md)      | 工作流执行的核心运行时上下文，是`Runtime`的工作流场景的特殊实现。
| [InteractiveInput](./runtime/interaction.md)  | 中断场景下构造用户与工作流的交互输入类。
| [InteractionOutput](./runtime/interaction.md) | 工作流与用户的交互输出数据类。
