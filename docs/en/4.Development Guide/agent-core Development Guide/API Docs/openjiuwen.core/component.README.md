# Component

`openjiuwen.core.component` provides the built-in components of openJiuwen. By adding these prebuilt components to a workflow, developers can orchestrate and implement custom business logic.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [WorkflowComponent](./component/base.md#class-openjiuwencorecomponentbaseworkflowcomponent) | Abstract base class for custom workflow components. |
| [LLMComponent](./component/llm_comp.md#class-openjiuwencorecomponentllm_compllmcomponent)  | Built-in large language model (LLM) component provided by openJiuwen. |
| [LLMCompConfig](./component/llm_comp.md#class-openjiuwencorecomponentllm_compllmcompconfig) | Data class for LLM component configuration. |
| [IntentDetectionComponent](./component/intent_detection_comp.md#class-openjiuwencorecomponentintent_detection_compintentdetectioncomponent) | Built-in intent detection component provided by openJiuwen. |
| [IntentDetectionCompConfig](./component/intent_detection_comp.md#class-openjiuwencorecomponentintent_detection_compintentdetectioncompconfig) | Data class for intent detection component configuration. |
| [QuestionerComponent](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compquestionercomponent) | Built-in questioner component provided by openJiuwen. |
| [QuestionerConfig](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compquestionerconfig) | Data class for questioner component configuration. |
| [FieldInfo](./component/questioner_comp.md#class-openjiuwencorecomponentquestioner_compfieldinfo) | Data class describing metadata of parameters to be extracted by the questioner component. |
| [ToolComponent](./component/tool_comp.md#class-openjiuwencorecomponenttool_comptoolcomponent) | Built-in tool (plugin) component provided by openJiuwen. |
| [ToolComponentConfig](./component/tool_comp.md#class-openjiuwencorecomponenttool_comptoolcomponentconfig) | Data class for tool component configuration. |
| [Start](./component/start_comp.md#class-openjiuwencorecomponentstart_compstart) | Built-in workflow start component provided by openJiuwen. |
| [BranchComponent](./component/branch_comp.md#class-openjiuwencorecomponentbranch_compbranchcomponent) | Built-in workflow branching component provided by openJiuwen. |
| [LoopComponent](./component/loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent) | Standard loop component class. |
| [LoopType](./component/loop_comp.md#class-openjiuwencorecomponentloop_complooptype) | Enumeration class defining loop types. |
| [LoopGroup](./component/loop_comp.md#class-openjiuwencorecomponentloop_comploopgroup) | Loop body container, serving as the foundational structure for building loop logic. |
| [SubWorkflowComponent](./component/workflow_comp.md#class-openjiuwencorecomponentworkflow_compsubworkflowcomponent) | Built-in sub-workflow component provided by openJiuwen. |
| [SetVariableComponent](./component/set_variable_comp.md#class-openjiuwencorecomponentset_variable_compsetvariablecomponent) | Built-in workflow variable assignment component provided by openJiuwen. |
| [BreakComponent](./component/break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent) | Break component used to control loop interruption. |
| [FuncCondition](./component/condition/condition.md#class-openjiuwencorecomponentconditionconditionfunccondition) | Function-based condition evaluation implementation. |
| [AlwaysTrue](./component/condition/condition.md#class-openjiuwencorecomponentconditionconditionalwaystrue) | Condition implementation that always evaluates to true. |
| [ExpressionCondition](./component/condition/expression.md#class-openjiuwencorecomponentconditionexpressionexpressioncondition) | Expression-based condition evaluation implementation. |
| [BranchRouter](./component/branch_router.md#class-openjiuwencorecomponentbranch_routerbranchrouter) | Core class implementing branch routing logic. |
|| [End](./component/end_comp.md#class-openjiuwencorecomponentend_compend) | Built-in workflow end component provided by openJiuwen. |
|| [EndConfig](./component/end_comp.md#class-openjiuwencorecomponentend_compendconfig) | Data class for end component configuration. |
