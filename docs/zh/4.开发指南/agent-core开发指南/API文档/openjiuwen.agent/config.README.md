# config

`openjiuwen.agent.config`是openJiuwen中用于定义Agent各种运行参数、模型配置、调用模板与限制策略的核心配置模块。

**Classes**：

| CLASS                                                                  | DESCRIPTION                             |
|------------------------------------------------------------------------|-----------------------------------------|
| [AgentConfig](./config/base.md#class-openjiuwenagentconfigbaseagentconfig)                                  | 该类是所有Agent配置的基础类，定义了Agent的基本属性。            |
| [ConstrainConfig](./config/react_config.md#class-openjiuwenagentconfigreact_configconstrainconfig)          | 用于配置Agent创建时的约束限制参数。       |
| [IntentDetectionConfig](./config/react_config.md#class-openjiuwenagentconfigreact_configintentdetectionconfig)          | 为​预留类，用于配置意图检测功能的参数，当前为预留定义接口，暂不支持使用。     |
| [ReActAgentConfig](./config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig)          | 用于配置ReActAgent的所有参数。      |
| [WorkflowAgentConfig](./config/workflow_config.md#class-openjiuwenagentconfigworkflow_configworkflowagentconfig) | 用于配置WorkflowAgent的所有参数。 |              