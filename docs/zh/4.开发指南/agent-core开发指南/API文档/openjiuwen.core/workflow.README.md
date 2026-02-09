# workflow

`openjiuwen.core.workflow`是openJiuwen框架支持工作流编排与执行的基础模块。工作流具体指多个组件或Agent按照预先设计的编排流程进行有序协作，从而完成复杂任务的一种机制，旨在提升复杂任务的处理效率与稳定性。

**Classes**：

| CLASS                                                                                                                                                                | DESCRIPTION                                                         |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [WorkflowSpec](./workflow/workflow_config.md)                 | 负责工作流结构和组件关系的定义，内部graph结构，不建议用户手动设置。 |
| [WorkflowMetadata](./workflow/workflow_config.md)         | 工作流元信息数据类，用于描述工作流的基本属性。                      |
| [ComponentAbility](./workflow/workflow_config.md)         | 工作流组件的能力枚举类。                                            |
| [WorkflowInputsSchema](./workflow/workflow_config.md) | 工作流工具插件的输入参数结构。                                      |
| [WorkflowConfig](./workflow/workflow_config.md)             | 配置结构数据类。                                                    |
| [WorkflowOutput](./workflow/base.md)                        | 工作流执行invoke的输出结果的数据类。                                |
| [WorkflowChunk](./workflow/base.md)                          | 工作流执行stream返回的数据帧的数据类。                              |
| [WorkflowExecutionState](./workflow/base.md)        | 工作流执行invoke的执行状态的枚举类。                                |
| [Workflow](./workflow/base.md)                                    | 工作流类。                                                          |
