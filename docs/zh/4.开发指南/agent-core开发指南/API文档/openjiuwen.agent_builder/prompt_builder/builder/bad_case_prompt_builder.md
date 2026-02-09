# openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder

## class openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder.BadCasePromptBuilder

```python
openjiuwen.agent_builder.prompt_builder.builder.bad_case_prompt_builder.BadCasePromptBuilder(model_config: ModelConfig)
```

`BadCasePromptBuilder`为错误案例优化器，能够基于评测实验结果中的典型错误案例，对提示词进行定向优化，以提升模型在边缘场景下的表现。

**参数**：

* **model_config**([ModelConfig](../../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的运行时配置，用于指定模型标识、参数设置及访问凭据。

### build

```python
build(prompt: str | Template, cases: List[EvaluatedCase]) -> Optional[str]
```

基于用户提供的原始提示词及若干典型错误示例，通过系统化分析与重构，对提示词内容进行精准优化，以提升其在错误案例上的准确率。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：待优化的原始提示词。
* **cases**(List[[EvaluatedCase](../../tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)])：一组错误示例，每个示例为一个`EvaluatedCase`对象。

**返回**：

* **Optional[str]**，优化后的提示词。

**异常**：

* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.agent_builder.tune.base import EvaluatedCase, Case
>>> from openjiuwen.agent_builder.prompt_builder.builder.badcase_prompt_builder import BadCasePromptBuilder
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> 
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建BadCasePromptBuilder对象
>>> builder = BadCasePromptBuilder(config)
>>>
>>> # 3. 构造错误案例
>>> BAD_CASES = [
...     EvaluatedCase(case=Case(
...         inputs={"query": "潘之恒（约1536—1621）字景升，号鸾啸生，冰华生，安徽歙县、岩寺人，侨寓金陵（今江苏南京）"},
...         label={"label": "[潘之恒]"}),
...         answer={"answer": "[潘之恒, 冰华生]"}
...     ),
...     EvaluatedCase(case=Case(
...         inputs={"query": "郭造卿（1532—1593），字建初，号海岳，福建福清县化南里人（今福清市人），郭遇卿之弟，郭造卿少年的时候就很有名气，曾游学吴越"},
...         label={"label": "[郭造卿, 郭遇卿]"}),
...         answer={"answer": "[郭造卿, 郭遇卿, 吴越]"}
...     ),
... ]
>>> # 4. 执行提示词错误案例优化
>>> response = builder.build(prompt="你是一个人名信息提取助手", cases=BAD_CASES)
你是一个专业的人名信息提取助手，专注于准确提取文本中的人名，忽略其他信息，确保提取的人名完整且正确。
```

### stream_build

```python
stream_build(prompt: str | Template, cases: List[EvaluatedCase]) -> Generator
```

基于用户提供的原始提示词及若干典型错误示例，通过系统化分析与重构，对提示词内容进行精准优化，流式生成优化后的提示词。

**参数**：

* **prompt**(str | [Template](../../../openjiuwen.core/utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate))：待优化的原始提示词。
* **cases**(List[[EvaluatedCase](../../tune/base.md#class-openjiuwenagent_buildertunebaseevaluatedcase)])：一组错误示例，每个示例为一个`EvaluatedCase`对象。

**返回**：

* **Generator**，返回优化后提示词的流式输出迭代器。

**异常**：

* **JiuWenBaseException**：openjiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../../../openjiuwen.core/common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.agent_builder.tune.base import EvaluatedCase, Case
>>> from openjiuwen.agent_builder.prompt_builder.builder.badcase_prompt_builder import BadCasePromptBuilder
>>>
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> 
>>> # 1. 创建模型配置
>>> model_info = BaseModelInfo(api_key="",  # 替换为实际的API密钥
... 						   api_base="",  # API地址
... 						   model="" 	# 模型名称
... 			 )
>>> config = ModelConfig(model_provider="", model_info=model_info)
>>>
>>> # 2. 创建BadCasePromptBuilder对象
>>> builder = BadCasePromptBuilder(config)
>>>
>>> # 3.构造错误案例
>>> BAD_CASES = [
...     EvaluatedCase(case=Case(
...         inputs={"query": "潘之恒（约1536—1621）字景升，号鸾啸生，冰华生，安徽歙县、岩寺人，侨寓金陵（今江苏南京）"},
...         label={"label": "[潘之恒]"}),
...         answer={"answer": "[潘之恒, 冰华生]"}
...     ),
...     EvaluatedCase(case=Case(
...         inputs={"query": "郭造卿（1532—1593），字建初，号海岳，福建福清县化南里人（今福清市人），郭遇卿之弟，郭造卿少年的时候就很有名气，曾游学吴越"},
...         label={"label": "[郭造卿, 郭遇卿]"}),
...         answer={"answer": "[郭造卿, 郭遇卿, 吴越]"}
...     ),
... ]
>>> # 4. 执行提示词错误案例优化
>>> response = builder.build(prompt="你是一个人名信息提取助手", cases=BAD_CASES)
>>> for chunk in response:
... 	print(chunk)
你
是一个
专业
的人
名
信息
（省略更多内容）
```

