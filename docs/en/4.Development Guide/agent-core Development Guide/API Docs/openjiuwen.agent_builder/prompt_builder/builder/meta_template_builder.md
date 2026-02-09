# openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder

## class openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder.MetaTemplateBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder.MetaTemplateBuilder(model_config: ModelConfig)
```

MetaTemplateBuilder is a prompt generation optimizer. It enhances the original prompt via meta templates to improve semantics, restructure the content, and guide behavior, thereby increasing the accuracy of model outputs.

**Parameters:**

- **model_config** ([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Runtime configuration for the model. It is used to specify the model identifier, parameter settings, and access credentials.

### register_meta_template

```python
register_meta_template(name: str, meta_template: str | Template)
```

Register a user-defined meta template.

**Parameters:**

- **name** (str): The name of the meta template to register.
- **meta_template** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The meta template content to register.

**Examples:**

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> # 1. Define a custom meta template prompt
>>> template = "this is a string meta template"
>>>
>>> # 2. Register the meta template prompt
>>> model_info = BaseModelInfo(api_key="",  # Replace with your actual API key
...                            api_base="",  # API endpoint
...                            model=""      # Model name
...             )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>> meta_template_builder = MetaTemplateBuilder(config)
>>> meta_template_builder.register_meta_template("custom_template", template)
```

### build

```python
build(prompt: str | Template, tools: Optional[List[ToolInfo]] = None, template_type: Literal["general", "plan", "other"] = "general", custom_template_name: Optional[str] = None) -> Optional[str]
```

Generate a prompt that is richer, more structured, and more logically rigorous based on the user-provided raw prompt and the selected meta template.

**Parameters:**

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt.
- **tools** (List[[ToolInfo](../../../openjiuwen.core/utils/tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], optional): Information about tools to be invoked. Default: None.
- **template_type** (Literal["general", "plan", "other"], optional): The meta template type to use. Default: "general".
  - "general": Use a general meta template for common scenarios.
  - "plan": Use a planning meta template to generate a structured reasoning path.
  - "other": Use a user-defined meta template for custom needs.
- **custom_template_name** (str, optional): The name of the user-selected meta template (required when template_type="other"). Default: None.

**Returns:**

- **Optional[str]**: The generated prompt content.

**Exceptions:**

- **JiuWenBaseException:** The base exception for openjiuwen. For details and solutions, refer to [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples:**

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> # 1. Create the model configuration
>>> model_info = BaseModelInfo(api_key="",  # Replace with your actual API key
...                            api_base="",  # API endpoint
...                            model=""      # Model name
...             )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a MetaTemplateBuilder instance
>>> builder = MetaTemplateBuilder(config)
>>>
>>> # 3. Generate the prompt
>>> response = builder.build(prompt="You are a travel assistant")
>>> print(response)
## Persona
Travel assistant
Define the role or identity you will play: An experienced travel planner, familiar with tourist attractions and cultural features worldwide.
List the role’s professional skills or specialties: Skilled at creating personalized travel plans, providing suggestions for transportation, lodging, dining, and activities, and tailoring itineraries to the user’s budget and interests.
(more content omitted)
```

### stream_build

```python
stream_build(prompt: str | Template, tools: Optional[List[ToolInfo]] = None, template_type: Literal["general", "plan", "other"] = "general", custom_template_name: Optional[str] = None) -> Generator
```

Stream the generation of a prompt that is richer, more structured, and more logically rigorous based on the user-provided raw prompt and the selected meta template.

**Parameters:**

- **prompt** (str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)): The original prompt.
- **tools** (List[[ToolInfo](../../../openjiuwen.core/utils/tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], optional): Information about tools to be invoked. Default: None.
- **template_type** (Literal["general", "plan", "other"], optional): The meta template type to use. Default: "general".
  - "general": Use a general meta template for common scenarios.
  - "plan": Use a planning meta template to generate a structured reasoning path.
  - "other": Use a user-defined meta template for custom needs.
- **custom_template_name** (str, optional): The name of the user-selected meta template (required when template_type="other"). Default: None.

**Returns:**

- Generator: An iterator that streams the generated prompt content.

**Exceptions:**

- JiuWenBaseException: The base exception for openjiuwen. For details and solutions, refer to [StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples:**

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> # 1. Create the model configuration
>>> model_info = BaseModelInfo(api_key="",  # Replace with your actual API key
...                            api_base="",  # API endpoint
...                            model=""      # Model name
...             )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. Create a MetaTemplateBuilder instance
>>> builder = MetaTemplateBuilder(config)
>>>
>>> # 3. Stream the prompt generation
>>> response = builder.stream_build(prompt="You are a travel assistant")
>>> for chunk in response:
...     print(chunk)
##
Per
so
na
De
fine
the
role
you
will
play
or
iden
tity
(more content omitted)
```