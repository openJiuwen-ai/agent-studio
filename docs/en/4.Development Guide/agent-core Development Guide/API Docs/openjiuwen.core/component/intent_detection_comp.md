# openjiuwen.core.component.intent_detection_comp

## class openjiuwen.core.component.intent_detection_comp.IntentDetectionCompConfig

Configuration for the intent detection component.

**Parameters:**

- **category_name_list** (List, optional): User-defined intent categories. Default: `[]`, meaning no categories are configured.
  Note: the intent detection component always includes a built-in default intent. If none of the user-defined intents match, the component guarantees that the default intent will be selected as a fallback.
- **model** ([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): LLM configuration.
  Note: if the LLM is not configured, or the configuration is invalid, the component will raise an exception.
- **user_prompt** (str, optional): User-defined prompt text. This will be inserted as a snippet into the component’s built-in prompt template, to help the LLM identify the user’s intent more accurately. Default: `""`, meaning no custom prompt is provided.
  This field is optional and only affects intent detection quality.
- **example_content** (List[str], optional): User-provided examples. This will be inserted as a snippet into the component’s built-in prompt template, providing examples to help the LLM identify the user’s intent more accurately. Default: `[]`, meaning no examples are provided.
  This field is optional and only affects intent detection quality.
- **enable_history** (bool, optional): Whether to include conversation history in the input passed to the LLM. `True` means history is used; `False` means it is not used. Default: `False`.
- **chat_history_max_turn** (int, optional): The maximum number of turns of conversation history to include (one turn means one user–assistant exchange).
  Value range: a positive integer (> 0). There is no upper limit; if the conversation has fewer turns than the configured maximum, the actual number of available turns is used.
  Default: 3.
  Note: this field only takes effect when `enable_history=True`. If there are fewer than 3 turns, the actual number of turns is used.

## class openjiuwen.core.component.intent_detection_comp.IntentDetectionComponent

```python
class openjiuwen.core.component.intent_detection_comp.IntentDetectionComponent(component_config: Optional[IntentDetectionCompConfig] = None)
```

The intent detection component uses an LLM to precisely parse and classify the user’s input intent. Based on the downstream branch routing rules configured by the user, it automatically routes the task flow to the corresponding workflow component for processing.

When using this component, the following constraints apply:

- Input: the intent detection component input must include the required field `query`, and may also include custom fields.
- Output: the component output includes the intent detection result, as follows:

  - **classification_id** (int): The intent class index. User-defined intents start from 1, where `1` corresponds to the first user-defined intent, and subsequent intent categories increment in order. `0` corresponds to the default intent, i.e., none of the user-defined intents matched.
  - **category_name** (str): The matched user intent category.
  - **reason** (str): The rationale for the classification.

**Parameters**:

- **component_config** ([IntentDetectionCompConfig](#class-openjiuwencorecomponentintent_detection_compintentdetectioncompconfig), optional): Configuration for the intent detection component.

**Exceptions**:

- **JiuWenBaseException**: The base exception type for openJiuwen. For details and resolution methods, see StatusCode
  (../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

### add_branch

```python
add_branch(condition: Union[str, Callable[[], bool], Condition], target: Union[str, list[str]], branch_id: str = None)
```

The intent detection component adds routing rules to downstream branches via the `add_branch` method.

**Parameters**:

- **condition** (Union[str, Callable[[], bool], Condition]): The branch condition expression or condition object. Three types are supported:
  - **str**: A string expression. The expression must include the intent detection component’s id within the workflow. `classification_id` refers to the output field of the intent detection component. `1` corresponds to the first user-defined intent, and subsequent intents increment in order.
  - **Callable[[], bool]**: A callable that returns a boolean indicating whether the condition is satisfied.
  - **[Condition](./condition/condition.md)**: A condition object implementing the `Condition` interface. Implementations include `FuncCondition`, `ExpressionCondition`, `AlwaysTrue`, etc.
- **target** (Union[str, list[str]]): The set of downstream component ids to route to when the condition is satisfied.
  Note: the target downstream component ids must already exist in the workflow; otherwise, an exception will be raised.
- **branch_id** (str, optional): The name of the branch route. Default: `None`, meaning no branch name is configured.

**Example**:

For an intent detection component that has been created successfully, add routing rules to downstream branches.

```python
>>> import asyncio
>>> import os
>>> 
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionCompConfig, IntentDetectionComponent
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
>>> async def demo_intent_dectection_component():
...     model_config = ModelConfig(
...         model_provider=MODEL_PROVIDER,
...         model_info=BaseModelInfo(
...         model=MODEL_NAME,
...         api_base=API_BASE,
...         api_key=API_KEY,
...         temperature=0.7,
...         top_p=0.9,
...         timeout=30  # Added timeout setting
...         ))
...     workflow = Workflow()
...     
...     config = IntentDetectionCompConfig(
...      category_name_list=["Query attractions in a location", "Query weather in a location"],
...      model=model_config,
...      user_prompt="Please determine the user's intent"
...     )
...     intent_component = IntentDetectionComponent(config)
...     
...     start_config = {
...          "inputs": [
...              {"id": "query", "required": True}
...          ]
...         }
...     
...     start_component = Start(start_config)
...     
...     intent_component.add_branch("${intent.classification_id} == 1", ["end"], "Attractions query branch")
...     intent_component.add_branch("${intent.classification_id} == 2", ["end"], "Weather query branch")
...     intent_component.add_branch("${intent.classification_id} == 0", ["end"], "Default branch")
...     
...     # Add the intent detection component object to the workflow via Workflow.add_workflow_comp.
...     # Name the component "intent", and in the input schema reference the value of the query field from the start component.
...     workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"output": "${intent}"})
...     workflow.add_workflow_comp(
...              "intent",
...              intent_component,
...              inputs_schema={"query": "${start.query}"},
...          )
...     workflow.add_connection("start", "intent")
...     workflow.add_connection("intent", "end")
...     result = await workflow.invoke({"query": "Query today's weather in Shanghai", "conversation_id": "c123"}, WorkflowRuntime())
...     
...     print(f"{result.result.get('output', {}).get('output', result.result)}")
>>> 
>>> def main():
...     asyncio.run(demo_intent_dectection_component())
>>> 
>>> if __name__ == "__main__":
...    main()
>>> 
>>> 
>>> # Possible output example:
{
    "classification_id": 2,
    "reason": "The user is asking what the weather in Shanghai is like, so it is classified as a weather query request",
    "category_name": "Query weather in a location"
}
>>> 
>>> # When the user input is "Please recommend a restaurant"
>>> result = await workflow.invoke({"query": "Please recommend a restaurant", "conversation_id": "c123"}, WorkflowRuntime())
>>> # The intent is neither a weather query nor an attractions query, so it is classified as the default intent; a possible output example:
{
    "classification_id": 0,
    "reason": "The request did not match any configured intent and is classified as the default intent",
    "category_name": "Default intent"
}
```
