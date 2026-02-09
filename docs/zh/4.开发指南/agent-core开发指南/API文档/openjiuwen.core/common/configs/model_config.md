# openjiuwen.core.component.common.configs.model_config

## class openjiuwen.core.component.common.configs.model_config.ModelConfig

大模型调用对象的配置类。

* **model_provider**(str)：大模型服务的提供商，当前支持配置`siliconflow`、`openai`。
* **model_info**([BaseModelInfo](../../utils/llm/base.md#class-openjiuwencoreutilsllmbasebasemodelinfo))：大模型服务的配置信息。默认值：`BaseModelInfo()`
