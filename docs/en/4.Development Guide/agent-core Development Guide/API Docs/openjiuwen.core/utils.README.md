# tool

`openjiuwen.core.utils.tool` is the tooling module of openJiuwen. It supports converting developer-defined custom tools into tools that can be recognised and invoked by LLMs.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [Param](./utils/tool/param.md) | Parameter configuration class for tools. |
| [Tool](./utils/tool/base.md) | Base class for tools. |
| [RestfulApi](./utils/tool/service_api/restful_api.md) | Wrapper for RESTful-style API tools. |

**Functions**：

| FUNCTION | DESCRIPTION |
|---------|-------------|
| [tool](./utils/tool/tool.md#tool) | A `tool` decorator that allows developers to customise and configure `Param` parameters. |


# llm

`openjiuwen.core.utils.llm` is the core module in openJiuwen for unified management and invocation of large language model instances. It primarily addresses the following two problems:

- How to load different types of large language models through a unified interface
- How to ensure model uniqueness and reusability

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [ModelFactory](./utils/llm/model_utils/model_factory.md#class-openjiuwencoreutilsllmmodel_utilsmodel_factorymodelfactory) | Loads and manages multiple chat models. |
| [RequestChatModel](./utils/llm/model_utils/default_model.md#class-openjiuwencoreutilsllmmodel_utilsdefault_modelrequestchatmodel) | A general-purpose HTTP client implementation targeting the OpenAI Chat Completions protocol. |
| [OpenAIChatModel](./utils/llm/model_utils/default_model.md#class-openjiuwencoreutilsllmmodel_utilsdefault_modelopenaichatmodel) | An implementation for invoking large language models compatible with the OpenAI-defined standard. |


# prompt

`openjiuwen.core.utils.prompt.template` provides prompt templates and template management functionality for openJiuwen. Developers can quickly build and populate prompt templates and manage them in a unified manner.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [Template](./utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate) | Prompt template. |


# config

`openjiuwen.core.utils.config` is the module used by openJiuwen to parse developer configuration files.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [UserConfig](./utils/config/user_config.md#class-openjiuwencoreutilsconfiguser_configuserconfig) | Reads user configuration files in `ini` format. |


# output_parser

`openjiuwen.core.utils.output_parser` provides output parsers for openJiuwen. The framework defines a base output parser and also includes two built-in output parsers for JSON and Markdown formats.

**Classes**：

| CLASS | DESCRIPTION |
|------|-------------|
| [BaseOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parserbasebaseoutputparser) | Defines the base class for output parsers. |
| [JsonOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parserjson_output_parserjsonoutputparser) | Parses JSON data contained within arbitrary text and large model outputs. |
| [MarkdownOutputParser](./utils/output_parser.md#class-openjiuwencoreutilsllmoutput_parsermarkdown_output_parsermarkdownoutputparser) | Parses Markdown content contained within arbitrary text and large model outputs. |
