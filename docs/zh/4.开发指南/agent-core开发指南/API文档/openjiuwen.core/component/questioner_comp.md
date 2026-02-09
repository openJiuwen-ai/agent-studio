# openjiuwen.core.component.questioner_comp

## class openjiuwen.core.component.questioner_comp.FieldInfo

提问器组件支持提取参数，该数据结构描述了待提取参数的元数据信息。

**参数**：

- **field_name**(str)：待提取参数的参数名。
- **description**(str)：待提取参数的功能描述。
- **cn_field_name**(str, 可选)：待提取参数在追问中暴露的信息，所以建议为`description`的精简信息。默认值：`""`，表示未配置，默认会采用`description`的值。
- **required**(bool, 可选)：是否为必选参数，`True`表示为必选参数，`False`表示为非必选参数。默认值：`False`。注意：只有必选参数未被提取到值时，才会触发提问器组件的追问流程。
- **default_value**(Any, 可选)：待提取参数的默认值。默认值：`""`，表示未配置有效默认值。注意：未提取到值的参数，才会用有效默认值对该参数赋值。

**样例**：

```python
>>> fieldInfo = FieldInfo(field_name="date", description="时间", required=True, default_value="today")
```

## class openjiuwen.core.component.questioner_comp.QuestionerConfig

提问器组件的配置信息，创建提问器组件时对其有依赖。

**参数**：

- **model**​([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的配置信息。注意：未配置大模型、或配置大模型错误，组件将抛出异常。
- **response_type**(str, 可选)：提问器组件的运行模式，当前只支持配置`reply_directly`，即直接问答模式。默认值：`reply_directly`。注意：该字段配置其他任意值，均会报错。
- **question_content**(str, 可选)：自定义的预设问题，一旦设置了预设问题，就一定会向用户追问。默认值：`""`，表示未配置预设问题。注意：用户预设问题的优先级最高，一旦配置了，当工作流执行到提问器组件时，提问器组件必然向用户追问该预设问题。
- **extract_fields_from_response**(bool, 可选)：是否提取参数开关。`True`表示开启提取参数，`False`表示不开启提取参数。默认值：`False`。注意：在提取参数开关打开的情况中，如果配置了预设问题`question_content`，用户的答复将作为首次提取参数的依据；如果未配置预设问题，则组件固定输入`query`，将作为首次提取参数的依据。
- **field_names**(List[[FieldInfo](#class-openjiuwencorecomponentquestioner_compfieldinfo)], 可选)：如果需要提取参数，需要提取的参数信息。默认值：`[]`，表示未配置待提取的参数。注意：如果`extract_fields_from_response`配置为`True`，但未配置待提取的参数，则抛出异常。
- **max_response**(int, 可选)：提问器的最大追问次数。默认值：3，表示最大追问次数为3次。取值范围：大于0的正整数。注意：如果达到最大追问次数后仍然无法提取到所有待提取的参数的值，则抛出异常。
- **with_chat_history**(bool, 可选)：表示提问器的输入信息中，是否包含对话历史，`True`表示使用对话历史，`False`表示不使用对话历史信息。默认值：`False`。
- **chat_history_max_rounds**(int, 可选)：表示选取对话历史的最大轮数（一轮具体指user-assistant一次对话）。默认值：5。取值范围：大于0的正整数，没有上限设置，达不到预设轮数的按照实际对话轮数取。注意：`enable_history=True`时该字段才生效，不足5轮时取实际的对话轮数。
- **extra_prompt_for_fields_extraction**(str, 可选)：用户自定义的提示词信息，该信息将作为片段填充到提问器组件自带的提示词模板中，用于提供约束信息、提示大模型更好地提取参数信息。默认值：`""`，表示未配置用户自定义的提示信息。可以不配置，该字段只会影响参数提取的效果。
- **example_content**(str, 可选)：用户自定义的示例，该信息将作为片段填充到提问器组件自带的提示词模板中，用于提供示例、提示大模型更好地提取参数信息。默认值：`""`，表示未配置示例。可以不配置，该字段只会影响提问器组件参数提取的效果。

**样例**：

```python
>>> # 定义待提取的参数信息
>>> key_fields = [
...             FieldInfo(
...                 field_name="location",
...                 description="地点",
...                 required=True
...             ),
...             FieldInfo(
...                 field_name="date",
...                 description="时间",
...                 required=True,
...                 default_value="today",
...             ),
...         ]
>>> # 创建提问器的配置对象
>>> questioner_config = QuestionerConfig(
...             model=model_config,
...             question_content="",
...             extract_fields_from_response=True,
...             field_names=key_fields,
...             with_chat_history=False
...         )
```

## class openjiuwen.core.component.questioner_comp.QuestionerComponent

```python
class openjiuwen.core.component.questioner_comp.QuestionerComponent(questioner_comp_config: QuestionerConfig = None)
```

提问器组件支持配置预设问题、并基于预设问题主动向用户提问并收集反馈。同时，支持配置参数提取开关，一旦开启，系统将结合用户反馈和可选的对话历史，提取指定参数。在不超过最大追问次数的前提下，可持续追问，引导用户完善信息。此外，组件还支持灵活对接自定义的三方大模型，灵活配置提取参数的提示词模板。

调用该组件时需要遵循以下约束：

- 输入：提问器组件的输入包括固定字段`query`，注意：一旦在提问器组件的配置中设置了question_content，就会要求用户回答问题、给出反馈，并且该反馈的优先级高于`query`；同时支持输入自定义字段。
- 输出：提问器组件的输出定义包括最近一次向用户追问的内容`question`、最近一次用户的反馈内容`user_response`以及以key-value键值对的形式输出提问器提取到的参数。具体如下：
  - **question**(str)：最近一次向用户追问的内容，默认值：`""`，表示未触发追问用户。注意：如果配置了预设问题`question_content`、且只追问了一次，则question即为预设问题。
  - **user_response**(str)：最近一次用户的反馈内容。默认值：`""`，表示未触发用户反馈。
  - **key-value键值对**：当参数提取的开关`extract_fields_>>> from_response`打开，提问器提取到的参数，这些待提取参数的键在`field_names`中已经定义，提问器组件负责提取这些待提取参数的值；如果参数提取的开关关闭，则不存在参数提取的结果。

**参数**：

- **component_config**([QuestionerConfig](#class-openjiuwencorecomponentquestioner_compquestionerconfig), 可选): 提问器组件的配置信息。

**异常**：

- ​**JiuWenBaseException**​：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import asyncio
>>> import os
>>> 
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.questioner_comp import FieldInfo, QuestionerConfig, QuestionerComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.runtime.wrapper import TaskRuntime
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
>>> async def demo_questioner_component():
...     
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
...     # 定义待提取的参数信息
...     key_fields = [
...         FieldInfo(
...             field_name="location",
...             description="地点",
...             required=True
...         ),
 ...        FieldInfo(
...             field_name="date",
...             description="时间",
...             required=True,
...             default_value="today",
...         ),
...     ]
...     # 创建提问器的配置对象
...     questioner_config = QuestionerConfig(
...         model=model_config,
...         question_content="",
...         extract_fields_from_response=True,
...         field_names=key_fields,
...         with_chat_history=False
...     )
...     questioner_component = QuestionerComponent(questioner_comp_config=questioner_config)
... 
...     start_config = {
...              "inputs": [
...                  {"id": "query", "required": True}
...              ]
...             }
... 
...     start_component = Start(start_config)
...     # 通过`Workflow`的`add_workflow_comp`方法将提问器组件对象添加到工作流中，组件名称为"questioner"，输入参数引用了开始组件的query字段的值
...     workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"output": "${questioner.location}"})
...     workflow.add_workflow_comp(
...                 "questioner",
...                 questioner_component,
...                 inputs_schema={"query": "${start.query}"}
...             )
...     workflow.add_connection("start", "questioner")
...     workflow.add_connection("questioner", "end")

...     result = await workflow.invoke({"query": "2025年8月1日的上海", "conversation_id": "c123"}, WorkflowRuntime())
...     print(f"{result}")
...     # 由于提问器组件的输入已经能够支撑提问器一次性提取参数完整，且未触发追问和用户反馈的交互过程，所以输出结果如下：
...     # result={'output': {'output': '上海'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
... 
...     session_id = "test_questioner"
...     workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # 基于TaskRuntime，创建一个对应该session id的工作流Runtime
...     result = await workflow.invoke({"query": "时间是2025年8月1日", "conversation_id": "c123"}, workflow_runtime)
...     print(f"{result}")
...     # 工作流输出结果，主动向用户追问，注意此时的状态state为需要用户反馈，输出内容为追问用户的问题：
...     # result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供地点相关的信息'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
... 
...     # 用户反馈追问的地点信息`"地点是杭州"`后，继续执行工作流
...     user_input = InteractiveInput()
...     user_input.update('questioner', "地点是杭州")  # 从上一次追问用户的信息中能够获取到工作流中的断点组件id(本示例中id='questioner')，并且反馈用户结果
...     workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # 基于TaskRuntime保证同一session id时，Runtime中的状态维持不变，从而实现工作流的断点继续执行
...     result = await workflow.invoke(user_input, workflow_runtime)
...     print(f"{result}")
>>>
>>> def main():
...     asyncio.run(demo_questioner_component())
>>>
>>> if __name__ == "__main__":
...    main()
>>>
>>>
>>> # 提问器组件此次调用过程中的输出结果为：
result={'output': {'output': '杭州'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>

>>> 当用户输入是无关信息时（例如"帮我订机票"）
>>> user_input.update(interrupted_component_id, "帮我订机票")
>>> workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # 基于TaskRuntime保证同一session id时，Runtime中的状态维持不变，从而实现工作流的断点继续执行
>>> result = await workflow.invoke(user_input, workflow_runtime)
>>> # 参数提取不完整，如已达到最大追问轮数，则抛出异常JiuWenBaseException
错误码为100005
错误信息为"component [questioner] encountered an exception while executing ability [invoke], error detail: Questioner component exceed max response."
```
