# openjiuwen.core.component.questioner_comp

## class openjiuwen.core.component.questioner_comp.FieldInfo

The Questioner component supports parameter extraction. This data structure describes metadata for parameters to be extracted.

**Parameters**:

- **field_name** (str): The name of the parameter to extract.
- **description** (str): A functional description of the parameter to extract.
- **cn_field_name** (str, optional): The text exposed in follow-up questions for this parameter, so it is recommended to be a concise version of `description`. Default: `""`, meaning not configured; by default, the value of `description` is used.
- **required** (bool, optional): Whether this parameter is required. `True` means required; `False` means optional. Default: `False`.
  Note: the Questioner follow-up flow is triggered only when required parameters have not been successfully extracted.
- **default_value** (Any, optional): Default value for the parameter to extract. Default: `""`, meaning no effective default value is configured.
  Note: only parameters that fail to be extracted will be assigned an effective default value.

**Example**:

```
>>> fieldInfo = FieldInfo(field_name="date", description="time", required=True, default_value="today")
```

## class openjiuwen.core.component.questioner_comp.QuestionerConfig

Configuration for the Questioner component. It is required when creating the Questioner component.

**Parameters**:

- **model** ([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): LLM configuration.
  Note: if the model is not configured, or the model configuration is invalid, the component will raise an exception.
- **response_type** (str, optional): Runtime mode for the Questioner component. Currently only `reply_directly` is supported, i.e., direct Q&A mode. Default: `reply_directly`.
  Note: any other value will cause an error.
- **question_content** (str, optional): A custom preset question. Once set, the component will definitely ask the user a follow-up question. Default: `""`, meaning no preset question is configured.
  Note: preset questions have the highest priority. If configured, when the workflow reaches the Questioner component, it will always ask this preset question.
- **extract_fields_from_response** (bool, optional): Parameter extraction switch. `True` enables extraction; `False` disables it. Default: `False`.
  Note: when extraction is enabled:
  - if a preset question `question_content` is configured, the user’s reply is used as the basis for the first extraction attempt;
  - if no preset question is configured, the component uses the fixed input field `query` as the basis for the first extraction attempt.
- **field_names** (List[[FieldInfo](#class-openjiuwencorecomponentquestioner_compfieldinfo)], optional): Parameter definitions to extract. Default: `[]`, meaning no fields are configured.
  Note: if `extract_fields_from_response=True` but no fields are configured, an exception is raised.
- **max_response** (int, optional): Maximum number of follow-up attempts. Default: 3, meaning up to 3 follow-up questions.
  Value range: a positive integer (> 0).
  Note: if the maximum is reached and the component still cannot extract values for all target parameters, an exception is raised.
- **with_chat_history** (bool, optional): Whether the Questioner input includes conversation history. `True` includes history; `False` does not. Default: `False`.
- **chat_history_max_rounds** (int, optional): Maximum number of conversation rounds to include (one round means one user–assistant exchange). Default: 5.
  Value range: a positive integer (> 0). No upper limit; if fewer rounds exist than configured, the actual number of rounds is used.
  Note: this field only takes effect when `enable_history=True`. If there are fewer than 5 rounds, the actual number of rounds is used.
- **extra_prompt_for_fields_extraction** (str, optional): User-defined prompt text inserted into the component’s built-in prompt template, used to provide constraints and help the LLM extract parameters more effectively. Default: `""`, meaning not configured.
  This field is optional and only affects extraction quality.
- **example_content** (str, optional): User-defined examples inserted into the component’s built-in prompt template, used to provide examples and help the LLM extract parameters more effectively. Default: `""`, meaning not configured.
  This field is optional and only affects extraction quality.

**Example**:

```python
>>> # Define the parameter metadata to extract
>>> key_fields = [
...             FieldInfo(
...                 field_name="location",
...                 description="location",
...                 required=True
...             ),
...             FieldInfo(
...                 field_name="date",
...                 description="time",
...                 required=True,
...                 default_value="today",
...             ),
...         ]
>>> # Create the Questioner configuration object
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

The Questioner component supports configuring preset questions, proactively asking the user based on the preset question, and collecting feedback. It also supports enabling parameter extraction: once enabled, the system combines user feedback and optional conversation history to extract specified parameters. Without exceeding the maximum number of follow-up attempts, it can continue asking follow-up questions to guide the user to complete missing information. In addition, the component supports flexible integration with custom third-party LLMs and flexible configuration of prompt templates for parameter extraction.

When using this component, the following constraints apply:

- Input: the Questioner component input includes a fixed field `query`.
  Note: once `question_content` is set in the configuration, the component will require the user to answer the question and provide feedback, and this feedback has higher priority than `query`. Custom fields are also supported.
- Output: the component output includes:
  - `question`: the most recent follow-up question asked to the user
  - `user_response`: the most recent user feedback
  - extracted parameters output as key–value pairs
  Details:
  - **question** (str): The most recent follow-up question. Default: `""`, meaning no follow-up was triggered.
    Note: if `question_content` is configured and only one follow-up is asked, then `question` is the preset question.
  - **user_response** (str): The most recent user feedback. Default: `""`, meaning no user feedback was triggered.
  - **key–value pairs**: When the extraction switch `extract_fields_from_response` is enabled, the extracted parameter values are returned as key–value pairs. The keys are defined in `field_names`, and the Questioner component is responsible for extracting the corresponding values. If extraction is disabled, no extracted parameter results are returned.

**Parameters**:

- **component_config** ([QuestionerConfig](#class-openjiuwencorecomponentquestioner_compquestionerconfig), optional): Configuration for the Questioner component.

**Exceptions**:

- **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and resolution methods, see
  [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

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
...     # Define the parameter metadata to extract
...     key_fields = [
...         FieldInfo(
...             field_name="location",
...             description="location",
...             required=True
...         ),
...         FieldInfo(
...             field_name="date",
...             description="time",
...             required=True,
...             default_value="today",
...         ),
...     ]
...     # Create the Questioner configuration object
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
...     # Add the Questioner component object to the workflow via Workflow.add_workflow_comp.
...     # Name the component "questioner", and in the input schema reference the value of the query field from the start component.
...     workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"output": "${questioner.location}"})
...     workflow.add_workflow_comp(
...                 "questioner",
...                 questioner_component,
...                 inputs_schema={"query": "${start.query}"}
...             )
...     workflow.add_connection("start", "questioner")
...     workflow.add_connection("questioner", "end")
...
...     result = await workflow.invoke({"query": "Shanghai on 1 Aug 2025", "conversation_id": "c123"}, WorkflowRuntime())
...     print(f"{result}")
...     # Since the Questioner input is sufficient for extracting all parameters in one pass,
...     # and no follow-up or user-feedback interaction is triggered, the output is:
...     # result={'output': {'output': 'Shanghai'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
... 
...     session_id = "test_questioner"
...     workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # Create a WorkflowRuntime for this session id based on TaskRuntime
...     result = await workflow.invoke({"query": "The date is 1 Aug 2025", "conversation_id": "c123"}, workflow_runtime)
...     print(f"{result}")
...     # Workflow output: it proactively asks the user a follow-up question.
...     # Note: at this point the state indicates that user input is required, and the output contains the follow-up question:
...     # result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供location相关的信息'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
... 
...     # After the user replies with location information, e.g. "The location is Hangzhou", continue executing the workflow.
...     user_input = InteractiveInput()
...     user_input.update('questioner', "The location is Hangzhou")  # Get the interrupted component id from the previous follow-up (id='questioner' in this example) and provide the user feedback
...     workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # Keep Runtime state stable for the same session id to resume workflow execution from the breakpoint
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
>>> # Output of this invocation of the Questioner component:
result={'output': {'output': 'Hangzhou'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
>>> 
>>> # When the user input is irrelevant (e.g. "Help me book a flight")
>>> user_input.update(interrupted_component_id, "Help me book a flight")
>>> workflow_runtime = TaskRuntime(trace_id=session_id).create_workflow_runtime()  # Keep Runtime state stable for the same session id to resume workflow execution from the breakpoint
>>> result = await workflow.invoke(user_input, workflow_runtime)
>>> # If parameter extraction remains incomplete and the max follow-up count has been reached, a JiuWenBaseException is raised:
>>> # Error code: 100005
>>> # Error message: "component [questioner] encountered an exception while executing ability [invoke], error detail: Questioner component exceed max response."
```