# openjiuwen.core.component.llm_comp

## class openjiuwen.core.component.llm_comp.LLMCompConfig

定义大模型组件配置信息的数据类。

**参数**：

* **model**([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的配置信息。默认值：`None`，表示未配置大模型。注意：未配置大模型、或配置大模型错误，组件将抛出异常。
* **template_content**(List, 可选)：用户自定义的提示词模板。默认值：`[]`，表示未配置提示词模板。注意：必须包含至少一个`role=user`的用户提示词；在用户提示词前，可以存在若干个`role=system`的系统提示词，也可以没有系统提示词。
* **response_format**(Dict)：输出格式配置，格式为`{"type": "text/markdown/json"}`，分别表示输出文本、markdown、json格式的输出。注意：必须指定输出格式，且必须为text、markdown、json中的一种，否则会配置校验失败。
* **enable_history**(bool, 可选)：表示调用大模型的输入信息中，是否包含对话历史，`True`表示使用对话历史，`False`表示不使用对话历史。默认值：`False`。
* **output_config**(Dict)：输出字段的配置信息，可以配置为`{"param_key": {"type": "string", "description": "", "required": True}}`，表示包含一个字段名为`param_key`的输出参数，`type`表示输出字段的类型（支持`string`、`integer`、`boolean`、`number`、`array`、`object`，共6种类型），`description`表示输出字段的功能，`required`表示输出字段是否必须。注意：当`response_format`配置为`{"type": "text"}`或者`{"type": "markdown"}`时，只能配置一个输出参数；当`response_format`配置为`{"type": "json"}`时，需要配置至少一个输出参数。
  此外，当输出参数类型配置为列表时，即`type=array`，需要补充`items`字段，介绍列表内元素的类型（列表内每个元素的类型必须保持统一，即`array[string]`、`array[object]`等）；当输出参数类型配置为对象时，即`type=object`，需要补充`properties`字段，用于介绍对象内每个键的信息。
  以下是一个类型为`array[object]`的输出参数`output`的示例：

  ```json
  output_config = {
    "output": {
     "type": "array",
     "description": "个人信息列表",
     "items": {
      "type": "object",
      "properties": {
       "name": {
        "type": "string",
        "description": "姓名"
       },
       "age": {
        "type": "integer",
        "description": "年龄"
       }
      },
      "required": ["name", "age"]
     },
     "required": true
    }
  }
  ```

## class openjiuwen.core.component.llm_comp.LLMComponent

```python
class openjiuwen.core.component.llm_comp.LLMComponent(component_config: Optional[LLMCompConfig] = None)
```

大模型组件，用于与大模型的交互。

在工作流中添加并执行该组件时，需要遵循以下约束：

* 输入：用户自定义的Key-Value键值对，用于填充自定义提示词模板的占位符；也可以不指定输入键值对，LLM组件不作约束。
* 输出：根据用户配置`output_config`中的指定参数，大模型生成结果作为对应参数的输出结果。

**参数**：

* **component_config**([LLMCompConfig](#class-openjiuwencorecomponentllm_compllmcompconfig), 可选)：大模型组件的配置信息。

**异常**：

* **JiuWenBaseException**：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import os
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.llm_comp import LLMCompConfig, LLMComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> os.environ['LLM_SSL_VERIFY']='false'
>>> 
>>> MODEL_PROVIDER = ""
>>> MODEL_NAME = ""
>>> API_BASE = ""
>>> API_KEY = ""
>>> 
>>> 
>>> async def demo_llm_component():
...     workflow = Workflow()
... 
...     model_config = ModelConfig(
...         model_provider = MODEL_PROVIDER,
...         model_info = BaseModelInfo(
...         model = MODEL_NAME,
...         api_base = API_BASE,
...         api_key = API_KEY,
...         temperature = 0.7,
...         top_p = 0.9,
...         timeout = 30,
...             )
...         )
... 
...     config = LLMCompConfig(
...                  model=model_config,
...                  template_content=[
...                      {"role": "system", "content": "你是一个AI助手。"},
...                      {"role": "user", "content": "{{query}}"}
...                  ],
...                  response_format={"type": "text"},
...                  output_config={
...                      "output": {"type": "string", "description": "输出文本", "required": True}
...                  },
...              )
...     llm_component = LLMComponent(config)
... 
...     start_config = {
...      "inputs": [
...          {"id": "query", "required": True}
...      ]
...     }
... 
...     start_component = Start(start_config)
... 
...     workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"output": "${llm.output}"})
...     workflow.add_workflow_comp("llm", llm_component, inputs_schema={"query": "${start.query}"})
...     workflow.add_connection("start", "llm")
...     workflow.add_connection("llm", "end")
... 
...     result = await workflow.invoke({"query": "生成一句关于月亮的诗句", "conversation_id": "aaa123"}, WorkflowRuntime())
... 
...     print(f"{result}")
>>> 
>>> def main():
...     asyncio.run(demo_llm_component())
>>> 
>>> if __name__ == "__main__":
...    main()

LLM组件在工作流中的输出为{"output": "月走随人远，风来带桂香"}
```
