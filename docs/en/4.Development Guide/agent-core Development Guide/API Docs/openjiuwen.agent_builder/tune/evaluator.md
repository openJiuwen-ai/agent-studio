# openjiuwen.agent_builder.tune.evaluator.evaluator

## class openjiuwen.agent_builder.tune.evaluator.evaluator.DefaultEvaluator

```python
openjiuwen.agent_builder.tune.evaluator.evaluator.DefaultEvaluator(model_config: ModelConfig, metric: str = "")
```

`DefaultEvaluator` is the default evaluator class. It compares the case labels with the agent’s actual outputs using an LLM according to the given evaluation rules, and returns a score and the reasoning basis.
Parameters:

- **model_config** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): The LLM configuration used for evaluation.
- **metric** (str, optional): A custom description of evaluation criteria based on your scenario, for example: "The answer must not exceed 10 characters, otherwise the score is 0." Default: `""`. When metric is empty, scoring is based on semantic similarity between the label and the actual output: identical or similar yields 1, different yields 0.

### evaluate

```python
evaluate(case: Case, predict: Dict[str, Any]) -> EvaluatedCase
```

Evaluate a single case.

**Parameters:**

- **case** ([Case](base.md#class-openjiuwenagent_buildertunebasecase)): The test case object that includes inputs, expected outputs, and tools.
- **predict** (Dict[str, Any]): The model’s prediction in dict format, e.g. {"answer": "The Sun is a star"}.

**Returns:**

- **[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)**: The evaluation result object, including the score and reasoning.

**Example:**

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.optimizer.joint_optimizer import JointOptimizer
>>> from openjiuwen.agent_builder.tune.evaluator.evaluator import DefaultEvaluator
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> model_config = ModelConfig(
...     model_provider=MODEL_PROVIDER,
...     model_info=BaseModelInfo(
...         api_base=API_BASE,
...         api_key=API_KEY,
...         model=MODEL_NAME
...     )
... )
>>> # 1. Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     model=LLMCallConfig(
...         model=model_config,
...         # Prompt content to be optimized
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     ),
...     description=''
... )
>>> agent = create_chat_agent(config, None)
>>> 
>>> # 2. Build a test case
>>> case = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536–1621), courtesy name Jingsheng, style names Luanxiaosheng and Binghuasheng, from She County (Yansi), Anhui; resided in Jinling (present-day Nanjing, Jiangsu)."},
...     label={"output": "[Pan Zhiheng]"}
... )
>>> 
>>> # 3. Get the agent's predicted result
>>> async def forward(agent, cases):
...     return await agent.invoke(case.inputs)
>>> predict = asyncio.run(forward(agent, case))
>>> 
>>> # 4. Create an instruction optimizer and bind agent parameters
>>> optimizer = JointOptimizer(model_config, agent.get_llm_calls())
>>> 
>>> # 5. Create an evaluator
>>> evaluator = DefaultEvaluator(
...     model_config,
...     metric="For non-tool calls, the two answers must be exactly the same, including quantity and names. "
...            "However, differences in single/double quotes, formatting, and the tool_calls field can be ignored. "
...            "For tool calls, only check whether the plugin name and parameters in tool_calls are identical; ignore text content."
... )
>>> 
>>> # 6. Evaluate a single case
>>> eval_result = evaluator.evaluate(case, predict)
>>> 
>>> # 7. Print evaluation details
>>> print(f"score: {eval_result.score}, reason: {eval_result.reason}, "
...       f"answer: {eval_result.answer}, label: {eval_result.case.label}")
>>> 
>>> # 8. Perform prompt optimization
>>> optimizer.backward([eval_result])
>>> optimizer.update()
>>> 
>>> # 9. Get the agent's new predicted result
>>> predict = asyncio.run(forward(agent, case))
>>> 
>>> # 10. Evaluate the case again
>>> eval_result = evaluator.evaluate(case, predict)
>>> 
>>> # 11. Print evaluation details
>>> print(f"score: {eval_result.score}, reason: {eval_result.reason}, "
...       f"answer: {eval_result.answer}, label: {eval_result.case.label}")
```

### batch_evaluate

```python
batch_evaluate(cases: List[Case] | CaseLoader, predicts: List[Dict[str, Any]], **kwargs) -> List[[EvaluatedCase]]
```

Evaluate a list of cases in batch.

**Parameters:**

- **cases** (List[[Case](base.md#class-openjiuwenagent_buildertunebasecase)] | [CaseLoader](dataset.md#class-openjiuwenagent_buildertunedatasetcase_loadercaseloader)): A set of raw test cases to be evaluated. Each `Case` should include inputs, expected outputs, tool definitions, etc.
- **predicts** (List[Dict[str, Any]]): A list of model predictions corresponding one-to-one with `cases`. Each dict should contain the model’s structured output (e.g., `output`, `reasoning`).
- **kwargs** (Dict[str, Any]): Optional parameters, supporting:
  - **num_parallel** (int): Number of parallel evaluation threads, in [1, 20], default `1`. The actual parallelism will not exceed the number of `cases`.

**Returns**:

- **List[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)**: A list of evaluation results. Each item is an `EvaluatedCase` instance that encapsulates the original case, model output, evaluation score, and reasoning.

Example:

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.optimizer.joint_optimizer import JointOptimizer
>>> from openjiuwen.agent_builder.tune.evaluator.evaluator import DefaultEvaluator
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> model_config = ModelConfig(
...     model_provider=MODEL_PROVIDER,
...     model_info=BaseModelInfo(
...         api_base=API_BASE,
...         api_key=API_KEY,
...         model=MODEL_NAME
...     )
... )
>>> # 1. Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     model=LLMCallConfig(
...         model=model_config,
...         # Prompt content to be optimized
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     ),
...     description=''
... )
>>> agent = create_chat_agent(config, None)
>>> 
>>> # 2. Build test cases
>>> cases = [
...     Case(
...         inputs={"query": "Pan Zhiheng (c. 1536–1621), courtesy name Jingsheng, style names Luanxiaosheng and Binghuasheng, from She County (Yansi), Anhui; resided in Jinling (present-day Nanjing, Jiangsu)."},
...         label={"output": "[Pan Zhiheng]"}
...     ),
...     Case(
...         inputs={"query": "Emperor Gaozu’s 22 sons: Empress Dou gave birth to Jiancheng (Li Jiancheng), Emperor Taizong (Li Shimin), Xuanba (Li Xuanba), and Yuanji (Li Yuanji); Consort Wan gave birth to Zhiyun (Li Zhiyun); Concubine Mo gave birth to Yuanjing (Li Yuanjing); Concubine Sun gave birth to Yuanchang (Li Yuanchang)."},
...         label={"output": "[Li Jiancheng, Li Shimin, Li Xuanba, Li Yuanji, Li Zhiyun, Li Yuanjing, Li Yuanchang]"}
...     )
... ]
>>> 
>>> # 3. Get the agent’s predictions
>>> # Asynchronous forward inference function
>>> async def forward(agent, cases):
...     return [await agent.invoke(case.inputs) for case in cases]
>>> predicts = asyncio.run(forward(agent, cases))
>>> 
>>> # 4. Create an instruction optimizer and bind agent parameters
>>> optimizer = JointOptimizer(model_config, agent.get_llm_calls())
>>> 
>>> # 5. Create an evaluator
>>> evaluator = DefaultEvaluator(
...     model_config,
...     metric="The two answers must be exactly the same, including quantity and names; differences in single/double quotes may be ignored."
... )
>>> 
>>> # 6. Run the initial evaluation
>>> evaluated_cases = evaluator.batch_evaluate(cases, predicts)
>>> 
>>> # 7. Print evaluation details
>>> for eval_result in evaluated_cases:
...     print(f"score: {eval_result.score}, reason: {eval_result.reason}, "
...           f"answer: {eval_result.answer}, label: {eval_result.case.label}")
score: 1.0, reason: The model’s answer matches the ground truth in both names and count; although the quote formatting differs, such differences can be ignored under the rule., answer: {'output': "['Pan Zhiheng']", 'tool_calls': []}, label: {'output': '[Pan Zhiheng]'}
score: 0.0, reason: The model’s answer includes aliases or shortened forms not present in the ground truth, such as 'Jiancheng', 'Emperor Taizong', 'Xuanba', 'Yuanji', 'Zhiyun', 'Yuanjing', 'Yuanchang', which do not match the full names in the ground truth., answer: {'output': "['Jiancheng', 'Li Jiancheng', 'Emperor Taizong', 'Li Shimin', 'Xuanba', 'Li Xuanba', 'Yuanji', 'Li Yuanji', 'Zhiyun', 'Li Zhiyun', 'Yuanjing', 'Li Yuanjing', 'Yuanchang', 'Li Yuanchang']", 'tool_calls': []}, label: {'output': '[Li Jiancheng, Li Shimin, Li Xuanba, Li Yuanji, Li Zhiyun, Li Yuanjing, Li Yuanchang]'}
```