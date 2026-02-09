# openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder

## class openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder.MetaTemplateBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder.MetaTemplateBuilder(model_config: ModelConfig)
```

`MetaTemplateBuilder`为提示词生成优化器，通过元模板，对原始提示词进行语义增强、结构重构与行为引导，从而提升模型输出的准确性。

**参数**：

* **model_config**([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的运行时配置，用于指定模型标识、参数设置及访问凭据。

### register_meta_template

```python
register_meta_template(name: str, meta_template: str | Template)
```

注册用户自定义的元模板。

**参数**：

* **name**(str)：待注册的元模板名称。
* **meta_template**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：待注册的元模板内容。

**样例**：

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>>
>>> # 1. 自定义元模板提示词
>>> template = "this is a string meta template"
>>>
>>> # 2. 注册元模板提示词
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
...						   api_base="",  # API地址
...						   model="" 	# 模型名称
...			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>> meta_template_builder = MetaTemplateBuilder(config)
>>> meta_template_builder.register_meta_template("custom_template", template)
```

### build

```python
build(prompt: str | Template, tools: Optional[List[ToolInfo]] = None, template_type: Literal["general", "plan", "other"] = "general", custom_template_name: Optional[str] = None) -> Optional[str]
```

基于用户提供的原始提示词及所选定的元模板，生成内容更加丰富、结构更加完整、逻辑更加严谨的提示词。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：原始提示词。
* **tools**(List[[ToolInfo](../../../openjiuwen.core/utils/tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], 可选)：待调用的工具信息。默认值：`None`。
* **template_type**(Literal["general", "plan", "other"], 可选)：选择的元模版类型。默认值：`"general"`。
  - `"general"`：使用通用元模板生成提示词，适用于常规场景。
  - `"plan"`：使用规划类元模板，生成具备结构化思考路径的提示词。
  - `"other"`：使用用户自定义的元模板，灵活生成符合特定需求的提示词。
* **custom_template_name**(str, 可选)：用户选择的元模版名称。默认值：`None`。

**返回**：

* **Optional[str]**，生成的提示词内容。

**异常**：

* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建MetaTemplateBuilder对象
>>> builder = MetaTemplateBuilder(config)
>>>
>>> # 3. 执行提示词生成
>>> response = builder.build(prompt="你是一个旅行助手")
>>> print(response)
## 人设
旅行助手
定义你将扮演的角色或身份：一位经验丰富的旅行规划师，熟悉全球各地的旅游景点和文化特色。
列举角色的专业技能或特长：擅长制定个性化的旅行计划，提供交通、住宿、餐饮和活动建议，能够根据用户的预算和兴趣定制行程。
（省略更多内容）
```

### stream_build

```python
stream_build(prompt: str | Template, tools: Optional[List[ToolInfo]] = None, template_type: Literal["general", "plan", "other"] = "general", custom_template_name: Optional[str] = None) -> Generator
```

基于用户提供的原始提示词及所选定的元模板，流式生成内容更加丰富、结构更加完整、逻辑更加严谨的提示词。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：原始提示词。
* **tools**(List[[ToolInfo](../../../openjiuwen.core/utils/tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], 可选)：待调用的工具信息。默认值：`None`。
* **template_type**(Literal["general", "plan", "other"], 可选)：选择的元模版类型。默认值：`"general"`。
  - `"general"`：使用通用元模板生成提示词，适用于常规场景。
  - `"plan"`：使用规划类元模板，生成具备结构化思考路径的提示词。
  - `"other"`：使用用户自定义的元模板，灵活生成符合特定需求的提示词。
* **custom_template_name**(str, 可选)：用户选择的元模版名称。默认值：`None`。

**返回**：

* **Generator**，流式生成提示词内容，迭代器。

**异常**：

* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建MetaTemplateBuilder对象
>>> builder = MetaTemplateBuilder(config)
>>>
>>> # 3. 执行提示词生成
>>> response = builder.stream_build(prompt="你是一个旅行助手")
>>> for chunk in response:
...     print(chunk)
##
人
设
定义
你
将
扮演
的角色
或
身份
（省略更多内容）
```

