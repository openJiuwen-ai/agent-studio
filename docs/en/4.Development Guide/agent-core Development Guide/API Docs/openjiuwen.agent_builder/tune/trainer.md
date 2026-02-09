# openjiuwen.agent_builder.tune.trainer.trainer

## class openjiuwen.agent_builder.tune.trainer.trainer.Trainer

```python
openjiuwen.agent_builder.tune.trainer.trainer.Trainer(optimizer: BaseOptimizer, evaluator: BaseEvaluator, **kwargs)
```

The `Trainer` class provides a unified training and evaluation interface for agent optimization by flexibly binding an optimizer and an evaluator, enabling one-click improvement of agent capabilities.
**Parameters:**

- **optimizer** (BaseOptimizer): The optimizer bound to the trainer. Currently supports: [InstructionOptimizer](optimizer.md#class-openjiuwenagent_buildertuneoptimizerinstruction_optimizerinstructionoptimizer), [ExampleOptimizer](optimizer.md#class-openjiuwenagent_buildertuneoptimizerexample_optimizerexampleoptimizer), [JointOptimizer](optimizer.md#class-openjiuwenagent_buildertuneoptimizerjoint_optimizerjointoptimizer).
- **evaluator** (BaseEvaluator): The evaluator bound to the trainer, such as [DefaultEvaluator](evaluator.md#class-openjiuwenagent_buildertuneevaluatorevaluatordefaultevaluator).
- **kwargs** (Dict, optional): Optional training hyperparameters.
  - **num_parallel** (int, optional): Training/evaluation concurrency. Range: [1, 20], default: `1`.
  - **early_stop_score** (float, optional): Early stopping threshold. When the agent’s performance exceeds this score, iterative training stops. Range: [0, 1], default: `1`.

**Examples**:

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.tune.optimizer.joint_optimizer import InstructionOptimizer
>>> from openjiuwen.agent_builder.tune.evaluator.evaluator import DefaultEvaluator
>>> from openjiuwen.agent_builder.tune.trainer.trainer import Trainer
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> # 1. Create tuned LLM model configuration
>>> model_config = ModelConfig(
...     model_provider=MODEL_PROVIDER,
...     model_info=BaseModelInfo(
...         api_base=API_BASE,
...         api_key=API_KEY,
...         model=MODEL_NAME
...     )
... )
>>> # 2. Create an instruction optimizer
>>> optimizer = InstructionOptimizer(model_config)
>>> # 3. Create an evaluator and define the scoring rule
>>> evaluator = DefaultEvaluator(
...     model_config,
...     metric="The two answers must be consistent. Note: Quotation mark formatting can be ignored."
... )
>>> # 4. Create the trainer
>>> trainer = Trainer(
...     optimizer=optimizer,
...     evaluator=evaluator,
...     num_parallel=5
... )
```

### train

```python
train(agent: Agent, train_cases: CaseLoader, val_cases: Optional[CaseLoader] = None, **kwargs) -> Optional[Agent]
```

Train an agent using the given training dataset together with the optimizer and evaluator.

**Parameters:**

- **agent** (Agent): The agent to be optimized.
- **train_cases** ([CaseLoader](dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)): Training dataset.
- **val_cases** ([CaseLoader](dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader), optional): Validation dataset.
- **kwargs** (Dict, optional): Optional training hyperparameters.
  - **num_iterations** (int, optional): Number of training iterations. Range: [1, 20], default: `3`.

**Returns**:
**Optional[Agent]**, the optimized agent object. May return `None` if an error occurs during training.

**Exceptions**:

- **JiuWenBaseException**: Base exception class for openjiuwen. For detailed information and solutions, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**:

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.dataset.case_loader import CaseLoader
>>> from openjiuwen.agent_builder.tune.trainer.trainer import Trainer
>>> from openjiuwen.agent_builder.tune.evaluator.evaluator import DefaultEvaluator
>>> from openjiuwen.agent_builder.tune.optimizer.instruction_optimizer import InstructionOptimizer
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> model_config = ModelConfig(
...     model_provider=MODEL_PROVIDER,
...     model_info=BaseModelInfo(
...         api_base=API_BASE,
...         api_key=API_KEY,
...         model=MODEL_NAME
...     )
... )
>>> # Create an instruction optimizer
>>> optimizer = InstructionOptimizer(model_config)
>>> # Create an evaluator and define the scoring rule
>>> evaluator = DefaultEvaluator(
...     model_config,
...     metric="The two answers must be consistent. Note: Quotation mark formatting can be ignored."
... )
# Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     description='Chat Agent Test',
...     model=LLMCallConfig(
...         model=model_config,
...         # Prompt content that can be optimized
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     )
... )
>>> agent = create_chat_agent(config)
>>> trainer = Trainer(optimizer=optimizer,evaluator=evaluator)
>>> case = Case(inputs={"query": "How many 'r' are in 'strawberry'?"}, label={"output": "3"})
>>> case_loader = CaseLoader(cases=[case])
>>> agent = trainer.train(agent, case_loader)
```

### evaluate

```python
evaluate(agent: Agent, cases: CaseLoader) -> Tuple[float, List[EvaluatedCase]]
```

Evaluate an agent’s performance on a dataset.

**Parameters**:

- **agent** (Agent): The agent to be evaluated.
- **cases** ([CaseLoader](dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)): The dataset to evaluate on.

**Returns**:
**Tuple[float, List[[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]]**. The first element is a score between 0 and 1 (higher is better). The second element is the evaluated dataset with per-case score, model answer, and reasoning.

**Exceptions**:

- **JiuWenBaseException**: Base exception class for openjiuwen. For detailed information and solutions, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

Examples:

```python
>>> case = Case(inputs={"query": "How many 'r' are in 'strawberry'?"}, label={"output": "3"})
>>> case_loader = CaseLoader(cases=[case])
>>> score, evaluated_cases = trainer.evaluate(agent, case_loader)
>>> print(score)
>>> print(evaluated_cases)
1.0
case=Case(inputs={'query': "How many 'r' are in 'strawberry'?"}, label={'output': '3'}, tools=None, case_id='case_0'), answer={'output': '"strawberry" contains 3 letters "r".', 'tool_calls': []}, score=1.0, reason="The model's answer and the reference answer have the same meaning and conclusion: both state that the word 'strawberry' contains 3 letters 'r'. Although the model's answer is more verbose, the conclusion matches the reference and satisfies the validation requirement."
```

### predict

```python
predict(agent: Agent, cases: CaseLoader) -> List[Dict]
```

Generate the agent’s full outputs on the given dataset.

**Parameters**:

- agent (Agent): The agent to test.
- cases ([CaseLoader](dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)): The dataset to test on.

**Returns**:
**List[Dict]**, the agent’s responses for each input.

**Exceptions**:

- **JiuWenBaseException**: Base exception class for openjiuwen. For detailed information and solutions, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**:

```python
>>> case = Case(inputs={"query": "How many 'r' are in 'strawberry'?"}, label={"output": "3"})
>>> case_loader = CaseLoader(cases=[case])
>>> answers = trainer.predict(agent, case_loader)
>>> print(answers )
[{'output': '"strawberry" contains 3 letters "r".', 'tool_calls': []}]
```