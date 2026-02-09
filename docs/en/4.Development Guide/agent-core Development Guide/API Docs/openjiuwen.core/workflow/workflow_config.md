# openjiuwen.core.workflow.workflow_config

## class openjiuwen.core.workflow.workflow_config.WorkflowSpec

Defines the workflow structure and relationships between components. This is an internal graph structure and is not recommended for manual configuration by users.

- comp_configs (Dict[str, NodeSpec]): Configuration of all components in the workflow. Default: {}.
- stream_edges (Dict[str, list[str]]): Connections between components, defining the edges of the data flow. Default: {}.

## class openjiuwen.core.workflow.workflow_config.WorkflowMetadata

A workflow metadata dataclass that describes the basic properties of a workflow.

- name (str): Workflow name. Default: "".
- id (str): Workflow ID, a unique identifier. Default: "" (a UUID will be assigned by the system).
- version (str): Workflow version. Default: "".
- description (str): Workflow description. Default: "".

**Example**:

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowMetadata
>>> 
>>> metadata = WorkflowMetadata(id='fick_worklfow_id', name='Workflow', version='version_1', description='This is an example')
```

## class openjiuwen.core.workflow.workflow_config.ComponentAbility

An enumeration of workflow component capabilities.

- INVOKE: Process batch data into batch data.
- STREAM: Process batch data into streaming data.
- COLLECT: Aggregate streaming data into batch data.
- TRANSFORM: Process streaming data into streaming data.

## class openjiuwen.core.workflow.workflow_config.WorkflowInputsSchema

Defines the input parameter schema for treating a workflow as a tool plugin. This schema describes input parameter types, constraints, and descriptions.

- type (str): Tool type, must be "object". Default: "".
- properties (Dict[str, Any]): Defines the input parameter descriptions for the workflow. Keys are parameter names, and values include the parameter type (type), description (description), whether it is required (required), etc. Default: {}, indicating no input parameters.
- required (List[str]): A list of required input parameters for the workflow. Default: [], meaning no inputs are passed to the workflow tool. Note: If the workflow tool plugin requires inputs that are not provided, results may be affected.

**Example**:

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowInputsSchema
>>> 
>>> workflow_inputs_schema = WorkflowInputsSchema(
...     type="object",
...     properties={
...         "query": {
...             "type": "string",  # Can be string, integer, array, object, list, number
...             "description": "User query",
...             "required": True  # Indicates whether this parameter is required by the third-party plugin. If True, the LLM should auto-generate required parameters based on the current properties object.
...         }
...     },
...     required=['query']
... )
...
```

## class openjiuwen.core.workflow.workflow_config.WorkflowConfig

The configuration dataclass for a Workflow.

- metadata ([WorkflowMetadata](./workflow_config.md#class-openjiuwencoreworkflowworkflow_configworkflowmetadata)): Workflow metadata such as id, version, type, etc. Default: WorkflowMetadata().
- stream_timeout (float): Timeout between streaming message frames, in seconds. Default: 0.2 seconds.
- workflow_inputs_schema (Optional[[WorkflowInputsSchema](./workflow_config.md#class-openjiuwencoreworkflowworkflow_configworkflowinputsschema)]): Input parameter schema when treating the workflow as a tool plugin.

**Example**:

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowInputsSchema, WorkflowConfig, WorkflowMetadata
>>> 
>>> # Define the workflow input schema
>>> workflow_inputs_schema = WorkflowInputsSchema(
...     type="object",
...     properties={
...         "query": {
...             "type": "string",
...             "description": "User query",
...             "required": True
...         }
...     },
...     required=['query']
... )
...
>>> # Create WorkflowConfig
>>> workflow_config = WorkflowConfig(
...     metadata=WorkflowMetadata(id='fick_worklfow_id', name='Workflow', version='version_1', description='This is an example'),
...     workflow_inputs_schema=workflow_inputs_schema
... )
```

## type alias openjiuwen.core.workflow.workflow_config.Transformer:Callable[[Any], Any]

Transformer is a function used to transform a component’s input or output. It accepts any input type and returns any output type.

**Example**:

```python
>>> from typing import Any
>>> from openjiuwen.core.runtime.state import Transformer
>>> 
>>> def demo_transformer(data: Any) -> Any:
...      return {'a': 'a', 'b': 'b'}
... 
>>> transformer: Transformer = demo_transformer
```