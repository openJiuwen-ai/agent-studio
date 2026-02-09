# openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder

## class openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder.BadCasePromptBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder.BadCasePromptBuilder(model_config: ModelConfig)
```

BadCasePromptBuilder is a bad-case prompt optimizer. It leverages typical failure cases from evaluation results to target and refine prompts, improving model performance in edge scenarios.

**Parameters:**

- **model_config** ([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Runtime configuration of the LLM, used to specify the model identifier, parameter settings, and access credentials.

### build

```python
build(prompt: str | Template, cases: List[EvaluatedCase]) -> Optional[str]
```

Given the original prompt and several representative failure examples, it systematically analyzes and restructures the prompt to precisely optimize it and improve accuracy on the bad cases.

**Parameters:**

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt to be optimized.
- **cases** (List[[EvaluatedCase](../../tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]): A set of bad examples, each an EvaluatedCase object.

**Returns:**

- **Optional[str]**, the optimized prompt.

**Exceptions:**

- JiuWenBaseException: Base exception for openjiuwen. For detailed information and solutions, see [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples:**

```python
>>> import os
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.agent_builder.tune.base import EvaluatedCase, Case
>>> from openjiuwen.agent_builder.prompt_builder.builder.badcase_prompt_builder import BadCasePromptBuilder
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> 
>>> # 1. Create model configuration
>>> model_info = BaseModelInfo(api_key="",   # Replace with your actual API key
...                            api_base="",  # API base URL
...                            model=""      # Model name
...              )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a BadCasePromptBuilder
>>> builder = BadCasePromptBuilder(config)
>>>
>>> # 3. Build bad cases
>>> BAD_CASES = [
...     EvaluatedCase(case=Case(
...         inputs={"query": "Pan Zhiheng (c. 1536–1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, from She County and Yansi, Anhui, later residing in Jinling (present-day Nanjing, Jiangsu)"},
...         label={"label": "[Pan Zhiheng]"}),
...         answer={"answer": "[Pan Zhiheng, Binghuasheng]"}
...     ),
...     EvaluatedCase(case=Case(
...         inputs={"query": "Guo Zaoqing (1532–1593), courtesy name Jianchu, art name Haiyue, a native of Huananli, Fuqing County, Fujian (now Fuqing City), younger brother of Guo Yuqing. Guo Zaoqing was famous in his youth and once studied while traveling in Wu and Yue"},
...         label={"label": "[Guo Zaoqing, Guo Yuqing]"}),
...         answer={"answer": "[Guo Zaoqing, Guo Yuqing, Wu Yue]"}
...     ),
... ]
>>> # 4. Optimize the prompt based on bad cases
>>> response = builder.build(prompt="You are a person-name information extraction assistant", cases=BAD_CASES)
You are a professional person-name extraction assistant. Focus on accurately extracting personal names in the text, ignore other information, and ensure the extracted names are complete and correct.
```

### stream_build

```python
stream_build(prompt: str | Template, cases: List[EvaluatedCase]) -> Generator
```

Given the original prompt and several representative failure examples, it performs systematic analysis and restructuring to precisely optimize the prompt and stream the optimized result.

**Parameters:**

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt to be optimized.
- **cases** (List[[EvaluatedCase](../../tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)]): A set of bad examples, each an EvaluatedCase object.

**Returns:**

- Generator, a streaming iterator that yields the optimized prompt.

**Exceptions:**

- JiuWenBaseException: Base exception for openjiuwen. For detailed information and solutions, see [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples:**

```python
>>> import os
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.agent_builder.tune.base import EvaluatedCase, Case
>>> from openjiuwen.agent_builder.prompt_builder.builder.badcase_prompt_builder import BadCasePromptBuilder
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> 
>>> # 1. Create model configuration
>>> model_info = BaseModelInfo(api_key="",   # Replace with your actual API key
...                            api_base="",  # API base URL
...                            model=""      # Model name
...              )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a BadCasePromptBuilder
>>> builder = BadCasePromptBuilder(config)
>>>
>>> # 3. Build bad cases
>>> BAD_CASES = [
...     EvaluatedCase(case=Case(
...         inputs={"query": "Pan Zhiheng (c. 1536–1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, from She County and Yansi, Anhui, later residing in Jinling (present-day Nanjing, Jiangsu)"},
...         label={"label": "[Pan Zhiheng]"}),
...         answer={"answer": "[Pan Zhiheng, Binghuasheng]"}
...     ),
...     EvaluatedCase(case=Case(
...         inputs={"query": "Guo Zaoqing (1532–1593), courtesy name Jianchu, art name Haiyue, a native of Huananli, Fuqing County, Fujian (now Fuqing City), younger brother of Guo Yuqing. Guo Zaoqing was famous in his youth and once studied while traveling in Wu and Yue"},
...         label={"label": "[Guo Zaoqing, Guo Yuqing]"}),
...         answer={"answer": "[Guo Zaoqing, Guo Yuqing, Wu Yue]"}
...     ),
... ]
>>> # 4. Optimize the prompt based on bad cases
>>> response = builder.build(prompt="You are a person-name information extraction assistant", cases=BAD_CASES)
>>> for chunk in response:
...     print(chunk)
You
are a
professional
person-name
information
(more content omitted)
```