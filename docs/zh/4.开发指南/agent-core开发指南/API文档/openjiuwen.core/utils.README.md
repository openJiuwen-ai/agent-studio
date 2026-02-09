# tool

`openjiuwen.core.utils.tool`是openJiuwen的工具模块，支持将开发者自定义工具转换成可被LLM识别与调用的工具。

**Classes**：

| CLASS                                                                                                                                                      | DESCRIPTION               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| [Param](./utils/tool/param.md)                                                                            | Tool的参数配置类。        |
| [Tool](./utils/tool/base.md)                                | Tool基类。                |
| [RestfulApi](./utils/tool/service_api/restful_api.md) | restful风格接口工具封装。 |

**Functions**：

| FUNCTION                                                                                                             | DESCRIPTION                                     |
| -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| [tool](./utils/tool/tool.md#tool)     | 支持开发者自定义配置Param参数的tool装饰器。     |

# llm

`openjiuwen.core.utils.llm` 是openJiuwen中用于统一管理和调用大模型实例的核心模块，主要解决以下两个问题：

- 如何通过统一接口加载不同类型的大模型
- 如何保证模型的唯一性、可复用性

**Classes**：

| CLASS                                                                                                                            | DESCRIPTION                                                          |
|----------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [ModelFactory](./utils/llm/model_utils/model_factory.md#class-openjiuwencoreutilsllmmodel_utilsmodel_factorymodelfactory)        | 加载和管理多个聊天模型                                                                 |
| [RequestChatModel](./utils/llm/model_utils/default_model.md#class-openjiuwencoreutilsllmmodel_utilsdefault_modelrequestchatmodel) | 面向OpenAI Chat Completions协议的​通用HTTP客户端实现​                                                                 |
| [OpenAIChatModel](./utils/llm/model_utils/default_model.md#class-openjiuwencoreutilsllmmodel_utilsdefault_modelopenaichatmodel)  | 兼容OpenAI定义标准的调用大模型的实现                                                                 |                                                 |

# prompt

`openjiuwen.core.utils.prompt.template`提供了openJiuwen的提示词模板和模板管理功能，开发者可以快速构建、填充提示词模板，并进行统一管理。

**Classes**：

| CLASS                     | DESCRIPTION  |
|---------------------------|--------------|
| [Template](./utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)                      | 提示词模板。       |

# config

`openjiuwen.core.utils.config`是openJiuwen解析开发者配置文件的模块。

**Classes**：

| CLASS                                       | DESCRIPTION        |
|---------------------------------------------|--------------------|
| [UserConfig](./utils/config/user_config.md#class-openjiuwencoreutilsconfiguser_configuserconfig) | 读取用户的`ini`格式的配置文件。 |


# output_parser

`openjiuwen.core.utils.output_parser`是openJiuwen提供的输出解析器。框架不仅定义了输出解析器的基类，还预置了针对Json和Markdown格式的两种输出解析器。

**Classes**：

| CLASS                                            | DESCRIPTION                  |
|--------------------------------------------------|------------------------------|
| [BaseOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parserbasebaseoutputparser)     | 定义了输出解析器的基类。                 |
| [JsonOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parserjson_output_parserjsonoutputparser)     | 解析任意字符和大模型输出结果中包含的Json数据。    |
| [MarkdownOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parsermarkdown_output_parsermarkdownoutputparser) | 解析任意字符和大模型输出结果包含的Markdown信息。 |
