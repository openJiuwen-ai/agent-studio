# openjiuwen.core.component.common.configs.model_config

## class openjiuwen.core.component.common.configs.model_config.ModelConfig

Configuration class for large language model invocation objects.

* **model_provider** (str): The provider of the large language model service. Currently supported values are `siliconflow` and `openai`.
* **model_info** ([BaseModelInfo](../../utils/llm/base.md#class-openjiuwencoreutilsllmbasebasemodelinfo)): Configuration information for the large language model service. Default value: `BaseModelInfo()`
