# tune

openJiuwen的agent调优功能。

**Classes**：

| CLASS                                                                                                                           | DESCRIPTION    |
|---------------------------------------------------------------------------------------------------------------------------------|----------------|
| [Case](./tune/base.md#class-openjiuwenagent_buildertunebasecase)                                                                | 用例类。           |
| [EvaluatedCase](./tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)                                              | 评估后的用例类。       |
| [CaseLoader](./tune/dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)                                   | 用例加载器类。        |
| [DefaultEvaluator](./tune/evaluator.md#class-openjiuwenagent_buildertuneevaluatorevaluatordefaultevaluator)                     | 默认用例评估器类。      |
| [InstructionOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerinstruction_optimizerinstructionoptimizer) | 提示词指令优化类。      |
| [ExampleOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerexample_optimizerexampleoptimizer)             | 提示词示例优化类。      |
| [JointOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerjoint_optimizerjointoptimizer)                   | 提示词指令-示例联合优化类。 |
| [Trainer](./tune/trainer.md#class-openjiuwenagent_buildertunetrainertrainertrainer)                                             | Agent训练器类。     |
