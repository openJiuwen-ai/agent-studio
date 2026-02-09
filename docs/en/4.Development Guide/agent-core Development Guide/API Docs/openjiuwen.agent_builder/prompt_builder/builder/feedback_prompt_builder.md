# openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder

## class openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder.FeedbackPromptBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder.FeedbackPromptBuilder(model_config: ModelConfig)
```

`FeedbackPromptBuilder` is a prompt feedback optimizer that automatically analyzes and refines the original prompt based on user-provided feedback, improving its accuracy, clarity, and effectiveness.

**Parameters:**

- **model_config** ([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): The LLM runtime configuration, used to specify the model identifier, parameter settings, and access credentials.

### build

```python
build(prompt: str | Template, feedback: str, mode: Literal["general", "insert", "select"] = "general", start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> Optional[str]
```

Generates an optimized prompt by intelligently analyzing and restructuring the original prompt and corresponding feedback to improve accuracy.

**Parameters:**

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt to be optimized.
- **feedback** (str): User-provided feedback.
- **mode** (Literal["general", "insert", "select"], optional): Three available modes. Default: `"general"`.
  - `"general"`: General mode; applies holistic optimization to the original prompt.
  - `"insert"`: Insert mode; inserts optimized content at a specified position in the original prompt.
  - `"select"`: Select mode; choose a subsection of the original prompt for localized optimization.
- **start_pos** (int, optional): When in `"insert"` mode, it indicates the insertion position for optimized content. When in `"select"` mode, it indicates the start index of the selected segment. Default: `None`.
- **end_pos** (int, optional): When in `"select"` mode, it indicates the end index of the selected segment. Default: `None`.

**Returns:**

- **Optional[str]**, the optimized prompt.

**Exceptions:**

- **JiuWenBaseException**: The base exception in openjiuwen. For details and solutions, see [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples:**

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder import FeedbackPromptBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>>
>>> # 1. Create model configuration
>>> model_info = BaseModelInfo(api_key="",  # Replace with your actual API key
...                            api_base="", # API base URL
...                            model=""     # Model name
...              )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a FeedbackPromptBuilder instance
>>> feedback_builder = FeedbackPromptBuilder(config)
>>>
>>> # 3. Build the prompt
>>> response = feedback_builder.build(prompt="You are a travel assistant", feedback="Enrich it")
You are a professional travel assistant capable of providing travel planning, attraction recommendations, and local cultural introductions
```

### stream_build

```python
stream_build(prompt: str | Template, feedback: str, mode: Literal["general", "insert", "select"] = "general", start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> Generator
```

Generates an optimized prompt with stream via intellgient analysis and restructuring the original prompt and corresponding feedback to improve accuracy.

**Parameters**：

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt to be optimized.
- **feedback** (str): User-provided feedback.
- **mode** (Literal["general", "insert", "select"], optional): Three available modes. Default: `"general"`.
  - `"general"`: General mode; applies holistic optimization to the original prompt.
  - `"insert"`: Insert mode; inserts optimized content at a specified position in the original prompt.
  - `"select"`: Select mode; choose a subsection of the original prompt for localized optimization.
- **start_pos** (int, optional): Required in `"insert"` mode, indicating the insertion position for optimized content. Required in `"select"` mode, indicating the start index of the selected segment. Default: `None`.
- **end_pos** (int, optional): Required in `"select"` mode, indicating the end index of the selected segment. Default: `None`.

**Returns**:

- **Generator**, a streaming iterator yielding the optimized prompt.

**Exceptions**:

- **JiuWenBaseException**: The base exception in openjiuwen. For details and solutions, see [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**:

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder import FeedbackPromptBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> 
>>> # 1. Create model configuration
>>> model_info = BaseModelInfo(api_key="",  # Replace with your actual API key
...                            api_base="", # API base URL
...                            model=""     # Model name
...              )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a FeedbackPromptBuilder instance
>>> feedback_builder = FeedbackPromptBuilder(config)
>>>
>>> # 3. Build the prompt in streaming mode
>>> response = feedback_builder.stream_build(prompt="You are a travel assistant", feedback="Enrich it")
>>> for chunk in response:
...     print(chunk)
You
are a
professional
travel
assistant
(more content omitted)
```