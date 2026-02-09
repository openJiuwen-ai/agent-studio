# tune

openJiuwen's agent tuning capabilities.

**Classes**:

| CLASS                                                                                                                           | DESCRIPTION                                 |
|---------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| [Case](./tune/base.md#class-openjiuwenagent_buildertunebasecase)                                                                | Case class.                                  |
| [EvaluatedCase](./tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)                                              | Evaluated case class.                        |
| [CaseLoader](./tune/dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)                                   | Case loader class.                           |
| [DefaultEvaluator](./tune/evaluator.md#class-openjiuwenagent_buildertuneevaluatorevaluatordefaultevaluator)                     | Default case evaluator class.                |
| [InstructionOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerinstruction_optimizerinstructionoptimizer) | Prompt instruction optimizer class.          |
| [ExampleOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerexample_optimizerexampleoptimizer)             | Prompt example optimizer class.              |
| [JointOptimizer](./tune/optimizer.md#class-openjiuwenagent_buildertuneoptimizerjoint_optimizerjointoptimizer)                   | Prompt instruction–example joint optimizer class. |
| [Trainer](./tune/trainer.md#class-openjiuwenagent_buildertunetrainertrainertrainer)                                             | Agent trainer class.                         |