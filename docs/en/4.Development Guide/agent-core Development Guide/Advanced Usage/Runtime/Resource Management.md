openJiuwen's `Runtime` provides resource management capabilities, making it easy for users to acquire, use, or release different resource instances. This avoids repeatedly creating instances and wasting resources, and also improves creation performance. Currently, `Runtime` manages the following four types of resources:

- **Workflow instances**: `Workflow` instances that encapsulate the component execution logic.
- **Large model instances**: `BaseModelClient` instances that include model configuration, API keys, and runtime call parameters, used to send inference requests and interact with external systems.
- **Prompt template instances**: `Template` instances, runtime objects composed of a template name and prompt content.
- **Tool instances**: `Tool` instances, executable components created from predefined templates to accomplish specific tasks and return structured results.

# Workflow Instance Management

`Runtime` provides capabilities to add, query, delete, and batch add `Workflow` instances.

Use the `add_workflow` interface to add a workflow instance. You need to specify a unique workflow name, which can later be used via the `get_workflow` interface to query the added workflow.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

workflow1 = _create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="1", version="1")))
runtime.add_workflow("1_1", workflow1)
workflow_1 = await runtime.get_workflow("1_1")
metadata_1 = workflow_1.config().metadata
print(metadata_1)
```

Output:

```python
name='' id='1' version='1' description=''
```

Use the `add_workflows` interface to batch add workflow instances. Each workflow instance must have a unique name, and you can use the `get_workflow` interface to query it later.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

workflow2 = _create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="2", version="2")))
workflow3 = _create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="3", version="3")))
runtime.add_workflows([("2_2", workflow2), ("3_3", workflow3)])

workflow_2 = await runtime.get_workflow("2_2")
metadata_2 = workflow_2.config().metadata
workflow_3 = await runtime.get_workflow("3_3")
metadata_3 = workflow_3.config().metadata
print(metadata_2)
print(metadata_3)
```

Returns:

```python
name='' id='2' version='2' description=''
name='' id='3' version='3' description=''
```

Use the `remove_workflow` interface to delete an already added workflow instance by its specified name.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
runtime.remove_workflow("2_2")
workflow_2 = await runtime.get_workflow("2_2")
print(workflow_2)
```

Output:

```python
None
```

Complete code:

```python
import asyncio

from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata


class CustomComponent(WorkflowComponent, ComponentExecutable):
    def __init__(self, workflow_id):
        super().__init__()
        self._workflow_id = workflow_id

    def _create_workflow(self, workflow_config):
        workflow = Workflow(workflow_config)
        workflow.set_start_comp("start", Start())
        workflow.set_end_comp("end", End())
        workflow.add_connection("start", "end")
        return workflow

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        # Add 1 workflow
        workflow1 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="1", version="1")))
        runtime.add_workflow("1_1", workflow1)
        workflow_1 = await runtime.get_workflow("1_1")
        metadata_1 = workflow_1.config().metadata
        print(metadata_1)

        # Batch add workflows
        workflow2 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="2", version="2")))
        workflow3 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="3", version="3")))
        runtime.add_workflows([("2_2", workflow2), ("3_3", workflow3)])

        workflow_2 = await runtime.get_workflow("2_2")
        metadata_2 = workflow_2.config().metadata
        workflow_3 = await runtime.get_workflow("3_3")
        metadata_3 = workflow_3.config().metadata
        print(metadata_2)
        print(metadata_3)

        runtime.remove_workflow("2_2")
        workflow_2 = await runtime.get_workflow("2_2")
        print(workflow_2)

flow = Workflow()
flow.set_start_comp("start", Start())
flow.add_workflow_comp("custom", CustomComponent("custom"))
flow.set_end_comp("end", End())
flow.add_connection("start", "custom")
flow.add_connection("custom", "end")



if __name__ == "__main__":
    asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
```

# Prompt Template Instance Management

`Runtime` provides capabilities to add, query, delete, and batch add prompt templates.

Use the `add_prompt` interface to add a `Prompt` template instance. You need to specify a unique template name, which can later be used via the `get_prompt` interface to query the added template.

```python
from openjiuwen.core.agent.agent import AgentRuntime
from openjiuwen.core.utils.prompt.template.template import Template

user_prompt = """
    {{user_prompt}}

    The currently available function categories are:
    {{category_info}}

    Conversation history between the user and assistant:
    {{chat_history}}

    Current input:
    {{input}}

    Please analyze based on the current input and conversation history and output the most suitable function category. Output format is JSON:
    {"class": "Category xx"}
    If there is no suitable category, please output {{default_class}}.
    """
intent_detection_template=Template(name="default",content=[{"role": "user", "content": user_prompt}])
runtime = AgentRuntime()
runtime.add_prompt("default_template", intent_detection_template)

print(runtime.get_prompt("default_template").name)
```

Output:

```python
default
```

`Runtime` also provides batch add capabilities. For example:
Use the `add_prompts` interface to batch add `Prompt` template instances. Each template instance must have a unique name, and you can use the `get_prompt` interface to query it later.

```python
from openjiuwen.core.utils.prompt.template.template import Template

intent_detection_template_1 = Template(name="default_1", content=[{"role": "user", "content": "{{user_prompt}}"}])
question_template = Template(name="ask", content=[{"role": "user", "content": "{{chat_history}}"}])
runtime.add_prompts([("default_template", intent_detection_template_1), ("question_template", question_template)])

print(runtime.get_prompt('default_template').name)
print(runtime.get_prompt('question_template').name)
```

Output:

```python
default_1
ask
```

Use the `remove_prompt` interface to delete an already added `Prompt` template instance by its template name.

```python
runtime.remove_prompt("default_template")
print(runtime.get_prompt("default_template"))
```

Output:

```python
None
```

Complete code:

```python
import asyncio

from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.utils.prompt.template.template import Template
from openjiuwen.core.workflow.base import Workflow


class CustomComponent(WorkflowComponent, ComponentExecutable):
    def __init__(self, workflow_id):
        super().__init__()
        self._workflow_id = workflow_id

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        user_prompt = """
            {{user_prompt}}

            The currently available function categories are:
            {{category_info}}

            Conversation history between the user and assistant:
            {{chat_history}}

            Current input:
            {{input}}

            Please analyze based on the current input and conversation history and output the most suitable function category. Output format is JSON:
            {"class": "Category xx"}
            If there is no suitable category, please output {{default_class}}.
            """
        intent_detection_template = Template(name="default", content=[{"role": "user", "content": user_prompt}])
        runtime.add_prompt("default_template", intent_detection_template)

        print(runtime.get_prompt("default_template").name)

        intent_detection_template_1 = Template(name="default_1", content=[{"role": "user", "content": "{{user_prompt}}"}])
        question_template = Template(name="ask", content=[{"role": "user", "content": "{{chat_history}}"}])
        runtime.add_prompts([("default_template", intent_detection_template_1), ("question_template", question_template)])

        print(runtime.get_prompt('default_template').name)
        print(runtime.get_prompt('question_template').name)

        runtime.remove_prompt("default_template")
        print(runtime.get_prompt("default_template"))

flow = Workflow()
flow.set_start_comp("start", Start())
flow.add_workflow_comp("custom", CustomComponent("custom"))
flow.set_end_comp("end", End())
flow.add_connection("start", "custom")
flow.add_connection("custom", "end")


if __name__ == "__main__":
    asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
```

# Large Model Instance Management

`Runtime` provides capabilities to add, query, delete, and batch add large model instances.

Use the `add_model` interface to add a large model instance. You need to specify a unique instance name, which can later be used via the `get_model` interface to query the added instance.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
model = _get_model(10)
runtime.add_model("model", model)
saved_model = runtime.get_model("model")
print(f"Saved model: {type(saved_model).__name__}")
```

Output:

```python
Saved model: Siliconflow
```

Use the `add_models` interface to batch add large model instances. Each large model instance must have a unique name, and you can use the `get_model` interface to query them later.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
model1 = _get_model(1)
model2 = _get_model(2)
runtime.add_models([("model_1", model1), ("model_2", model2)])
print(f"model_1 exists: {runtime.get_model('model_1') is not None}")
print(f"model_2 exists: {runtime.get_model('model_2') is not None}")
```

Output:

```python
model_1 exists: True
model_2 exists: True
```

Use the `remove_model` interface to delete an already added large model instance by its specified name.

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
runtime.remove_model("model_1")
print(f"After removal model_1: {runtime.get_model('model_1')}")
```

Output:

```python
After removal model_1: None
```

Complete code:

```python
import asyncio

from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
from openjiuwen.core.workflow.base import Workflow


class CustomComponent(WorkflowComponent, ComponentExecutable):
    def __init__(self, workflow_id):
        super().__init__()
        self._workflow_id = workflow_id

    def _get_model(self, timeout):
        # You need to replace api_base and api_key
        return ModelFactory().get_model(model_provider="openai", api_key="sk-****************************", api_base="your path model service", max_retrie=1, timeout=timeout)

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        model = self._get_model(10)
        runtime.add_model("model", model)
        saved_model = runtime.get_model("model")
        print(f"Saved model: {type(saved_model).__name__}")

        model1 = self._get_model(1)
        model2 = self._get_model(2)
        runtime.add_models([("model_1", model1), ("model_2", model2)])
        print(f"model_1 exists: {runtime.get_model('model_1') is not None}")
        print(f"model_2 exists: {runtime.get_model('model_2') is not None}")

        runtime.remove_model("model_1")
        print(f"After removal model_1: {runtime.get_model('model_1')}")

flow = Workflow()
flow.set_start_comp("start", Start())
flow.add_workflow_comp("custom", CustomComponent("custom"))
flow.set_end_comp("end", End())
flow.add_connection("start", "custom")
flow.add_connection("custom", "end")

if __name__ == "__main__":
    asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
```

# Tool Instance Management

`Runtime` provides capabilities to add, query, delete, and batch add tool instances.

Use the `add_tool` interface to add a tool instance. You need to specify a unique instance name, which can later be used via the `get_tool` interface to query the added instance.

```python
from openjiuwen.core.utils.tool.function.function import LocalFunction
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.agent.agent import AgentRuntime

add_plugin = LocalFunction(
    name="add",
    description="Addition",
    params=[
        Param(name="a", description="Addend", type="number", required=True),
        Param(name="b", description="Augend", type="number", required=True),
    ],
    func=lambda a, b: a + b
)
runtime = AgentRuntime()
runtime.add_tool("add_plugin", add_plugin)

tool = runtime.get_tool("add_plugin")
print(tool.name)
```

Output:

```python
add
```

Use the `add_tools` interface to batch add tool instances. Each tool instance must have a unique name, and you can use the `get_tool` interface to query them later.

```python
from openjiuwen.core.utils.tool.function.function import LocalFunction
from openjiuwen.core.utils.tool.param import Param

add_plugin = LocalFunction(
    name="add",
    description="Addition",
    params=[
        Param(name="a", description="Addend", type="number", required=True),
        Param(name="b", description="Augend", type="number", required=True),
    ],
    func=lambda a, b: a + b
)

multiply_plugin = LocalFunction(
    name="multiply",
    description="Multiplication",
    params=[
        Param(name="a", description="Multiplier", type="number", required=True),
        Param(name="b", description="Multiplicand", type="number", required=True),
    ],
    func=lambda a, b: a * b
)


runtime.add_tools([("add_plugin", add_plugin), ("multiply_plugin", multiply_plugin)])
tool = runtime.get_tool("multiply_plugin")
print(tool.name)
```

Output:

```python
multiply
```

Use the `remove_tool` interface to delete an already added tool instance by its specified name.

```python
runtime.remove_tool("add_plugin")
print(runtime.get_tool("add_plugin"))
```

Output:

```python
None
```

Complete code:

```python
import asyncio

from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.utils.tool.function.function import LocalFunction
from openjiuwen.core.utils.tool.param import Param
from openjiuwen.core.workflow.base import Workflow


class CustomComponent(WorkflowComponent, ComponentExecutable):
    def __init__(self, workflow_id):
        super().__init__()
        self._workflow_id = workflow_id

    def _create_workflow(self, workflow_config):
        workflow = Workflow(workflow_config)
        workflow.set_start_comp("start", Start())
        workflow.set_end_comp("end", End())
        workflow.add_connection("start", "end")
        return workflow

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        add_plugin = LocalFunction(
            name="add",
            description="Addition",
            params=[
                Param(name="a", description="Addend", type="number", required=True),
                Param(name="b", description="Augend", type="number", required=True),
            ],
            func=lambda a, b: a + b
        )
        runtime.add_tool("add_plugin", add_plugin)

        tool = runtime.get_tool("add_plugin")
        print(tool.name)

        add_plugin = LocalFunction(
            name="add",
            description="Addition",
            params=[
                Param(name="a", description="Addend", type="number", required=True),
                Param(name="b", description="Augend", type="number", required=True),
            ],
            func=lambda a, b: a + b
        )

        multiply_plugin = LocalFunction(
            name="multiply",
            description="Multiplication",
            params=[
                Param(name="a", description="Multiplier", type="number", required=True),
                Param(name="b", description="Multiplicand", type="number", required=True),
            ],
            func=lambda a, b: a * b
        )

        runtime.add_tools([("add_plugin", add_plugin), ("multiply_plugin", multiply_plugin)])
        tool = runtime.get_tool("multiply_plugin")
        print(tool.name)

        runtime.remove_tool("add_plugin")
        print(runtime.get_tool("add_plugin"))


flow = Workflow()
flow.set_start_comp("start", Start())
flow.add_workflow_comp("custom", CustomComponent("custom"))
flow.set_end_comp("end", End())
flow.add_connection("start", "custom")
flow.add_connection("custom", "end")

if __name__ == "__main__":
    asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
```