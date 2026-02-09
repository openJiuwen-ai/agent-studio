# openjiuwen.agent_builder.tune.optimizer

## class openjiuwen.agent_builder.tune.optimizer.instruction_optimizer.InstructionOptimizer

```python
openjiuwen.agent_builder.tune.optimizer.instruction_optimizer.InstructionOptimizer(model_config: ModelConfig, parameters: Optional[Dict[str, LLMCall]] = None, **kwargs)
```

The `InstructionOptimizer` is a prompt instruction optimizer for Agents. By analyzing feedback generated from incorrect input-output cases, it refines the internal prompt template and improves the Agent’s accuracy on those error cases.
**Parameters**:

- **model_config** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Configuration of the optimization model. A stronger model is recommended.
- **parameters** (Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)], optional): Agent prompt optimization parameters. Can be empty. If empty, you must later bind parameters via the bind_parameter interface. Default: `None`. Parameters can be obtained via get_llm_calls (currently supported only by ChatAgent).

**Example**:

```python
>>> import os
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.optimizer.instruction_optimizer import InstructionOptimizer
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
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
>>> 
>>> # 1. Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     model=LLMCallConfig(
...         model=model_config,
...         # Optimizable prompt content
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     ),
...     description=''
... )
>>> agent = create_chat_agent(config, tools=[])
>>> 
>>> # 2. Create the instruction optimizer and bind the agent parameters
>>> optimizer = InstructionOptimizer(model_config, agent.get_llm_calls())
```

### bind_parameter

```python
bind_parameter(parameters: Dict[str, LLMCall])
```

Manually bind or update the parameters to be optimized.

**Parameters**:

- **parameters**(Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)]): The Agent parameters to optimize.

**Exceptions**:

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

    **Example**:

```python
>>> optimizer.bind_parameter(agent.get_llm_calls())
```

### backward:

```python
backward(evaluated_cases: List[EvaluatedCase])
```

Perform text-gradient updates based on evaluated cases.

**Parameters**:

- **evaluated_cases** (List[[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]): The evaluated cases.

**Exceptions**:

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

```python
>>> from openjiuwen.agent_builder.tune.base import Case, EvaluatedCase
>>> case = Case(inputs={"query": "How many r's are in 'strawberry'?"}, label={"output": "3"})
>>> 
>>> evaluated_cases = [
...     EvaluatedCase(case=case, answer={"output": "2"}, score=0.0, reason="There are 3 r's in 'strawberry', but the model answered 2; the counts do not match.")
... ]
>>> optimizer.backward(evaluated_cases)
```

### update

```python
update()
```

Update the Agent’s prompt content. This interface must be called after backward.

**Exceptions**:

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

```python
>>> optimizer.update()
At this point, the agent’s prompt has been updated, for example: "You are a chat assistant. Please carefully analyze the user’s question, such as math problems, and provide the answer."
```

## class openjiuwen.agent_builder.tune.optimizer.example_optimizer.ExampleOptimizer

```python
openjiuwen.agent_builder.tune.optimizer.example_optimizer.ExampleOptimizer(model_config: ModelConfig, parameters: Optional[Dict[str, LLMCall]] = None, num_examples: int = 1)
```

The `ExampleOptimizer` is a prompt example optimizer for Agents. By inductively analyzing error cases, it adds the most representative examples to the prompt to improve the Agent’s performance on those errors.
**Parameters:**

- **model_config** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Configuration of the optimization model. A stronger model is recommended.
- **parameters** (Optional[Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)]]): Agent prompt optimization parameters. Can be empty; you can bind parameters later via bind_parameter. Default: `None`.
- **num_examples** (int, optional): The number of examples allowed to be added to the prompt. Range: [0, 20]. Default: `1`.

**Example:**

```python
>>> import os
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.optimizer.example_optimizer import ExampleOptimizer
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
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
>>> 
>>> # 1. Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     model=LLMCallConfig(
...         model=model_config,
...         # Optimizable prompt content
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     ),
...     description=''
... )
>>> agent = create_chat_agent(config, tools=[])
>>> 
>>> # 2. Create the example optimizer and bind the agent parameters
>>> optimizer = ExampleOptimizer(model_config, agent.get_llm_calls(), 1)
```

### bind_parameter

```python
bind_parameter(parameters: Dict[str, LLMCall])
```

Manually bind or update the parameters to be optimized.

Parameters:

- **parameters** (Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)]): The Agent parameters to optimize.

Exceptions:

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example:**

```python
>>> optimizer.bind_parameter(agent.get_llm_calls())
```

### backward

```python
backward(evaluated_cases: List[EvaluatedCase])
```

Perform text-gradient updates based on evaluated cases.

**Parameters**:

- evaluated_cases (List[[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]): The evaluated cases.

**Exceptions**:

- JiuWenBaseException: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case, EvaluatedCase
>>> case = Case(inputs={"query": "How many r's are in 'strawberry'?"}, label={"output": "3"})
>>> 
>>> evaluated_cases = [
...     EvaluatedCase(case=case, answer={"output": "2"}, score=0.0, reason="There are 3 r's in 'strawberry', but the model answered 2; the counts do not match.")
... ]
>>> optimizer.backward(evaluated_cases)
```

### update

```python
update()
```
Update the Agent’s prompt content. This interface must be called after backward.

**Exceptions**:

- JiuWenBaseException: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

```python
>>> optimizer.update()
At this point, the agent’s prompt has been updated, for example: "You are a chat assistant. example-1:\n[question]: query: How many r's are in 'strawberry'?\n[expected answer]: output: 3"
```

## class openjiuwen.agent_builder.tune.optimizer.joint_optimizer.JointOptimizer

```python
openjiuwen.agent_builder.tune.optimizer.joint_optimizer.JointOptimizer(model_config: ModelConfig, parameters: Optional[Dict[str, LLMCall]] = None, num_examples: int = 1)
```

The `JointOptimizer` is a combined optimizer for prompt instructions and examples. It simultaneously optimizes prompt content and selects effective examples to improve the Agent’s performance.
**Parameters:**

- **model_config** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Configuration of the optimization model. A stronger model is recommended.
- **parameters** (Optional[Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)]]): Agent prompt optimization parameters. Can be empty; you can bind parameters later via bind_parameter. Default: `None`.
- **num_examples** (int, optional): The number of examples allowed to be added to the prompt. Range: [0, 20]. Default: `1`.

**Example:**

```python
>>> import os
>>> from openjiuwen.agent.config.base import LLMCallConfig
>>> from openjiuwen.agent_builder.tune.optimizer.joint_optimizer import JointOptimizer
>>> from openjiuwen.agent.chat_agent import create_chat_agent_config, create_chat_agent
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
>>> 
>>> # 1. Create the ChatAgent to be optimized
>>> config = create_chat_agent_config(
...     agent_id='chat_agent',
...     agent_version='1.0.0',
...     model=LLMCallConfig(
...         model=model_config,
...         # Optimizable prompt content
...         system_prompt=[{"role": "system", "content": "You are a chat assistant"}],
...     ),
...     description=''
... )
>>> agent = create_chat_agent(config, tools=[])
>>> 
>>> # 2. Create the joint optimizer and bind the agent parameters
>>> optimizer = JointOptimizer(model_config, agent.get_llm_calls(), 1)
```

### bind_parameter

```python
bind_parameter(parameters: Dict[str, LLMCall])
```

Manually bind or update the parameters to be optimized.

**Parameters:**

- **parameters** (Dict[str, [LLMCall](../../openjiuwen.core/operator/llm_call/base.md#class-openjiuwencoreoperatorllm_callbasellmcall)]): The Agent parameters to optimize.

**Exceptions:**

- J**iuWenBaseException:** The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example:**

```python
>>> optimizer.bind_parameter(agent.get_llm_calls())
```

### backward:

```python
backward(evaluated_cases: List[EvaluatedCase])
```

Perform text-gradient updates based on evaluated cases.

**Parameters:**

- **evaluated_cases** (List[[EvaluatedCase](base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]): The evaluated cases.

**Exceptions:**

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example:**

```python
>>> case = Case(inputs={"query": "How many r's are in 'strawberry'?"}, label={"output": "3"})
>>> 
>>> evaluated_cases = [
>>>     EvaluatedCase(case=case, answer={"output": "2"}, score=0.0, reason="There are 3 r's in 'strawberry', but the model answered 2; the counts do not match.")
>>> ]
>>> optimizer.backward(evaluated_cases)
```

### update

```python
update()
```

Update the Agent’s prompt content. This interface must be called after backward.

**Exceptions:**

- **JiuWenBaseException**: The base exception of openjiuwen. For detailed information and troubleshooting, see [StatusCode](../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example:**

```python
>>> optimizer.update()
At this point, the agent’s prompt has been updated, for example: "You are a chat assistant. Please carefully analyze the user’s question, such as math problems, and provide the answer. example-1:\n[question]: query: How many r's are in 'strawberry'?\n[expected answer]: output: 3"
```