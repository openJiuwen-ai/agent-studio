# openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder

## class openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder.FeedbackPromptBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder.FeedbackPromptBuilder(model_config: ModelConfig)
```

`FeedbackPromptBuilder`为提示词反馈优化器，能够根据用户提供的反馈信息，自动分析并优化原始提示词，提升其准确性、清晰度与执行效果。

**参数**：

* **model_config**([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的运行时配置，用于指定模型标识、参数设置及访问凭据。

### build

```python
build(prompt: str | Template, feedback: str, mode: Literal["general", "insert", "select"] = "general", start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> Optional[str]
```

根据用户提供的原始提示词及对应的反馈信息，通过智能分析与重构，生成优化后的提示词，从而提升提示词的准确性。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：待优化的原始提示词。
* **feedback**(str)：用户提供的反馈信息。
* **mode**(Literal["general", "insert", "select"], 可选)：可选的三种模式。默认值：`"general"`。
  - `"general"`：通用模式，对原始提示词进行整体优化。
  - `"insert"`：插入模式，在原始提示词指定位置插入优化内容。
  - `"select"`：选择模式，用于选择原始提示词需要优化的部分，进行局部优化。
* **start_pos**(int, 可选)：当模式为`"insert"`时，为必填项，表示优化内容的插入位置。当模式为`"select"`时，为必填项，表示部分优化的起始索引。默认值：`None`。
* **end_pos**(int, 可选)：当模式为`"select"`时，为必填项，表示部分优化的结束索引。默认值：`None`。

**返回**：

* **Optional[str]**，优化后的提示词。

**异常**：
 
* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder import FeedbackPromptBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>>
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建FeedbackPromptBuilder对象
>>> feedback_builder = FeedbackPromptBuilder(config)
>>>
>>> # 3. 执行提示词生成
>>> response = feedback_builder.build(prompt="你是一个旅行助手", feedback="丰富一下")
你是一个专业的旅行助手，能够提供旅行规划、景点推荐和当地文化介绍
```

### stream_build

```python
stream_build(prompt: str | Template, feedback: str, mode: Literal["general", "insert", "select"] = "general", start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> Generator
```

根据用户提供的原始提示词及对应的反馈信息，通过智能分析与重构，流式生成优化后的提示词，从而提升提示词的准确性。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：待优化的原始提示词。
* **feedback**(str)：用户提供的反馈信息。
* **mode**(Literal["general", "insert", "select"], 可选)：可选的三种模式。默认值：`"general"`。
  - `"general"`：通用模式，对原始提示词进行整体优化。
  - `"insert"`：插入模式，在原始提示词指定位置插入优化内容。
  - `"select"`：选择模式，用于选择原始提示词需要优化的部分，进行局部优化。
* **start_pos**(int, 可选)：当模式为`"insert"`时，为必填项，表示优化内容的插入位置。当模式为`"select"`时，为必填项，表示部分优化的起始索引。默认值：`None`。
* **end_pos**(int, 可选)：当模式为`"select"`时，为必填项，表示部分优化的结束索引。默认值：`None`。

**返回**：

* **Generator**，优化后提示词的流式迭代器。

**异常**：

* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from openjiuwen.agent_builder.prompt_builder.builder.feedback_prompt_builder import FeedbackPromptBuilder
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> 
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建FeedbackPromptBuilder对象
>>> feedback_builder = FeedbackPromptBuilder(config)
>>>
>>> # 3. 执行提示词生成
>>> response = feedback_builder.stream_build(prompt="你是一个旅行助手", feedback="丰富一下")
>>> for chunk in response:
...     print(chunk)
你
是一个
专业的
旅行
助手
（省略更多内容）
```

