# openjiuwen.core.component.llm_comp

## class openjiuwen.core.component.llm_comp.LLMCompConfig

Data class defining the configuration for the LLM component.

**Parameters**:

- **model** ([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)):
  Configuration for the large language model.
  Default: `None`, meaning no model is configured.
  Note: if the model is not configured, or the model configuration is invalid, the component will raise an exception.

- **template_content** (List, optional):
  User-defined prompt templates.
  Default: `[]`, meaning no prompt templates are configured.
  Note:
  - The template must contain at least one user prompt with `role=user`.
  - One or more system prompts with `role=system` may appear before the user prompt, or there may be no system prompts at all.

- **response_format** (Dict):
  Output format configuration, in the form `{"type": "text/markdown/json"}`, indicating text, markdown, or JSON output.
  Note:
  - This field must be specified.
  - The value must be one of `text`, `markdown`, or `json`; otherwise, configuration validation will fail.

- **enable_history** (bool, optional):
  Whether to include conversation history in the input sent to the LLM.
  `True` means conversation history is included; `False` means it is not.
  Default: `False`.

- **output_config** (Dict):
  Configuration for output fields.
  It can be configured as:
  `{"param_key": {"type": "string", "description": "", "required": True}}`
  which defines a single output parameter named `param_key`.

  Field definitions:
  - type: the output field type. Supported types are `string`, `integer`, `boolean`, `number`, `array`, and `object`.
  - description: description of the output field.
  - required: whether the output field is mandatory.

  Notes:
  - When `response_format` is `{"type": "text"}` or `{"type": "markdown"}`, only one output parameter may be configured.
  - When `response_format` is `{"type": "json"}`, at least one output parameter must be configured.

  Additional rules:
  - If the output field type is `array`, an `items` field must be provided to describe the type of elements in the array.
    All elements in the array must have the same type, e.g. `array[string]`, `array[object]`.
  - If the output field type is `object`, a `properties` field must be provided to describe each key in the object.

  Example of an output parameter named `output` with type `array[object]`:

  ```json
  output_config = {
    "output": {
      "type": "array",
      "description": "List of personal information",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Name"
          },
          "age": {
            "type": "integer",
            "description": "Age"
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

The LLM component is used to interact with a large language model.

When adding and executing this component in a workflow, the following constraints apply:

- Input:
  User-defined key–value pairs used to fill placeholders in the custom prompt templates.
  Input key–value pairs may also be omitted; the LLM component itself does not enforce input constraints.

- Output:
  Based on the parameters defined in `output_config`, the LLM-generated results are returned as the corresponding output fields.

**Parameters**:

- **component_config** ([LLMCompConfig](#class-openjiuwencorecomponentllm_compllmcompconfig), optional):
  Configuration for the LLM component.

**Exceptions**:

- **JiuWenBaseException**:
  The base exception type for openJiuwen.
  For detailed information and resolution methods, see
  [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

```python
import os
import asyncio

from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.component.llm_comp import LLMCompConfig, LLMComponent
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.workflow.base import Workflow

os.environ['LLM_SSL_VERIFY'] = 'false'

MODEL_PROVIDER = ""
MODEL_NAME = ""
API_BASE = ""
API_KEY = ""

async def demo_llm_component():
    workflow = Workflow()

    model_config = ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=30,
        )
    )

    config = LLMCompConfig(
        model=model_config,
        template_content=[
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": "{{query}}"}
        ],
        response_format={"type": "text"},
        output_config={
            "output": {
                "type": "string",
                "description": "Output text",
                "required": True
            }
        },
    )

    llm_component = LLMComponent(config)

    start_config = {
        "inputs": [
            {"id": "query", "required": True}
        ]
    }

    start_component = Start(start_config)

    workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
    workflow.set_end_comp("end", End(), inputs_schema={"output": "${llm.output}"})
    workflow.add_workflow_comp("llm", llm_component, inputs_schema={"query": "${start.query}"})
    workflow.add_connection("start", "llm")
    workflow.add_connection("llm", "end")

    result = await workflow.invoke(
        {"query": "Generate a poem line about the moon", "conversation_id": "aaa123"},
        WorkflowRuntime()
    )

    print(f"{result}")

def main():
    asyncio.run(demo_llm_component())

if __name__ == "__main__":
    main()

The output of the LLM component in the workflow is:
{"output": "The moon drifts farther as one walks, the wind arrives carrying the scent of osmanthus"}
```
