# Component

`openjiuwen.core.component`提供了openJiuwen预置的组件，开发者向工作流中添加预置组件，能够编排实现自定义的业务逻辑。

**Classes**：

| CLASS                                                   | DESCRIPTION              |
|---------------------------------------------------------|--------------------------|
| [WorkflowComponent](./component/base.md#class-openjiuwencorecomponentbaseworkflowcomponent)                          | 自定义工作流组件的抽象基类。           |
| [LLMComponent](./component/llm_comp.md#class-openjiuwencorecomponentllm_compllmcomponent)                           | openJiuwen预置的大模型组件。      |
| [LLMCompConfig](./component/llm_comp.md#class-openjiuwencorecomponentllm_compllmcompconfig)                          | 大模型组件配置信息的数据类。           |
| [IntentDetectionComponent](./component/intent_detection_comp.md#class-openjiuwencorecomponentintent_detection_compintentdetectioncomponent)  | openJiuwen预置的意图识别组件。     |
| [IntentDetectionCompConfig](./component/intent_detection_comp.md#class-openjiuwencorecomponentintent_detection_compintentdetectioncompconfig) | 意图识别组件配置信息的数据类。          |
| [QuestionerComponent](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compquestionercomponent)             | openJiuwen预置的提问器组件。      |
| [QuestionerConfig](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compquestionerconfig)                | 提问器组件配置信息的数据类。           |
| [FieldInfo](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compfieldinfo)                       | 提问器组件待提取参数的元数据信息的数据类。    |
| [ToolComponent](./component/tool_comp.md#class-openjiuwencorecomponenttool_comptoolcomponent)                         | openJiuwen预置的插件组件。       |
| [ToolComponentConfig](./component/tool_comp.md#class-openjiuwencorecomponenttool_comptoolcomponentconfig)                   | 插件组件配置信息的数据类。            |
| [Start](./component/start_comp.md#class-openjiuwencorecomponentstart_compstart)                                | openJiuwen预置的工作流开始组件。    |
| [BranchComponent](./component/branch_comp.md#class-openjiuwencorecomponentbranch_compbranchcomponent)                     | openJiuwen预置的工作流分支组件。    |
| [LoopComponent](./component/loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent)                         | 标准循环组件类。                 |
| [LoopType](./component/loop_comp.md#class-openjiuwencorecomponentloop_complooptype)                              | 循环类型枚举类。                 |
| [LoopGroup](./component/loop_comp.md#class-openjiuwencorecomponentloop_comploopgroup)                             | 循环体，是构建循环逻辑的基础容器。        |
| [SubWorkflowComponent](./component/workflow_comp.md#class-openjiuwencorecomponentworkflow_compsubworkflowcomponent)              | openJiuwen预置的子工作流组件。     |
| [SetVariableComponent](./component/set_variable_comp.md#class-openjiuwencorecomponentset_variable_compsetvariablecomponent)          | openJiuwen预置的工作流的变量赋值组件。 |
| [BreakComponent](./component/break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent)                       | 中断组件类，用于控制循环的中断。         |
| [FuncCondition](./component/condition/condition.md#class-openjiuwencorecomponentconditionconditionfunccondition)               | 基于函数的条件判断实现。             |
| [AlwaysTrue](./component/condition/condition.md#class-openjiuwencorecomponentconditionconditionalwaystrue)                  | 恒成立的条件判断实现。              |
| [ExpressionCondition](./component/condition/expression.md#class-openjiuwencorecomponentconditionexpressionexpressioncondition)        | 基于表达式的条件判断实现。            |
| [BranchRouter](./component/branch_router.md#class-openjiuwencorecomponentbranch_routerbranchrouter)                      | 实现分支路由器的核心类。             |
| [End](./component/end_comp.md#class-openjiuwencorecomponentend_compend)                                    | openJiuwen预置的工作流结束组件。    |
| [EndConfig](./component/end_comp.md#class-openjiuwencorecomponentend_compendconfig)                              | 结束组件配置信息的数据类             |
