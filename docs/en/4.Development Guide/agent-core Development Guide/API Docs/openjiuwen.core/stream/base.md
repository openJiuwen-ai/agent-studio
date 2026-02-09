# openjiuwen.core.stream.base

## class openjiuwen.core.stream.base.BaseStreamMode

```python
class openjiuwen.core.stream.base.BaseStreamMode
```

By setting different BaseStreamMode types in the workflow's stream method, you can control the format and content of streaming output.

- **OUTPUT**: Standard streaming output format. Emits data of type OutputSchema.
- **TRACE**: Debug information streaming format. Emits data of type TraceSchema.
- **CUSTOM**: Custom streaming output format. Emits data of type CustomSchema.

## class openjiuwen.core.stream.base.OutputSchema

```python
class openjiuwen.core.stream.base.OutputSchema
```

Data class for the openJiuwen standard streaming output format.

- **type** (str): The type of streaming data. Currently supports two built-in streaming message types:
  - 'INTERACTION': Indicates an interrupt-type streaming message for interactive interruption.
  - 'end node stream': Indicates a streaming message from the [End](../component/end_comp.md) component.
- **index** (int): The index of the streaming data.
- **payload** (Any): The content of the streaming data.

**Examples**:

Example outputs obtained based on [BaseStreamMode.OUTPUT](#class-openjiuwencorestreambaseoutputschema):

```python
from openjiuwen.core.stream.base import OutputSchema

OutputSchema(type = 'end node stream', index = 0, payload = {'answer': 'Result:'}),
OutputSchema(type = 'end node stream', index = 1, payload = { 'answer': 'Check the weather in Shanghai on 2025-08-22' })
```

## class openjiuwen.core.stream.base.CustomSchema

```python
class openjiuwen.core.stream.base.CustomSchema
```

Data class for user-defined streaming output format.

- kwargs (dict, optional): User-defined streaming data.

**Examples**:

Example output obtained based on [BaseStreamMode.CUSTOM](#class-openjiuwencorestreambasecustomschema):

```python
CustomSchema(custom_output = 'Check the weather in Shanghai on 2025-08-22')
```

## class openjiuwen.core.stream.base.TraceSchema

```python
class openjiuwen.core.stream.base.TraceSchema
```

Data class for streaming debug information format.

- type (str): The type of streaming data. Currently supports two built-in debug information types:
  - 'tracer_workflow': Debug information for workflow components.
  - 'tracer_agent': Debug information for agents, including LLM and plugin calls.
- payload (Any): Debug information data with a built-in schema that includes a unique identifier, start/end time, inputs/outputs, error details, component status, and more.

  - Base trace fields:

    | Field               | Type         | Description                                                                 |
    |---------------------|--------------|-----------------------------------------------------------------------------|
    | traceId             | str          | Trace ID                                                                    |
    | startTime           | datetime     | Start time, e.g., `datetime.datetime(2025, 8, 22, 14, 39, 9, 678133)` represents 2:39:09.678133 PM on Aug 22, 2025 |
    | endTime             | datetime     | End time, e.g., `datetime.datetime(2025, 8, 22, 14, 40, 9, 678133)` represents 2:40:09.678133 PM on Aug 22, 2025   |
    | inputs              | dict         | Component inputs, e.g., `{'a_num': 1}`—the parameters required by the component |
    | outputs             | dict         | Component outputs, e.g., `{'result': 2}`—the component’s output values     |
    | error               | dict         | Component exception, e.g., `{"error_code": -1, "message": TypeError}`, including the error code and exception details |
    | invokeId            | str          | Event ID                                                                    |
    | parentInvokeId      | str          | Parent event ID—the event ID of the previously executed component           |
    | executionId         | str          | Execution ID, equal to traceId                                              |
    | onInvokeData        | List[dict]   | Runtime information recorded during component execution                     |
    | componentId         | str          | Component ID; typically empty unless explicitly provided                    |
    | componentName       | str          | Component name; typically empty unless explicitly provided                  |
    | componentType       | str          | Component type. For example, when adding a component via `workflow.add_workflow_comp("a", CustomComponent())`, "a" is the componentType |
    | status              | str          | Component status: "start", "running", "finish", "error"                     |

  - Loop component fields:

    | Field        | Type   | Description                                                  |
    |--------------|--------|--------------------------------------------------------------|
    | loopNodeId   | str    | If the component is inside a loop, the invokeId of that loop |
    | loopIndex    | int    | Loop iteration count, starting from 1                        |

  - Nested sub-workflow fields:

    | Field        | Type   | Description                                                                 |
    |--------------|--------|-----------------------------------------------------------------------------|
    | parentNodeId | str    | If the component is inside a sub-workflow, the invokeId of that sub-workflow; otherwise "" |

**Examples**:

- Example 1: Output from a basic workflow using [BaseStreamMode.TRACE](#class-openjiuwencorestreambasebasestreammode).

  ```python
  import datetime
  from openjiuwen.core.stream.base import TraceSchema
  # Below is an excerpt of the trace information for component `a`. You will see two frames: a start event and an end event.
  # The `traceId` identifies the trace. The start event includes `startTime` with status "start".
  # The end event fills `endTime` and has status "finish".
  # `parentInvokeId` is the `invokeId` of the previously executed component `start`.

  # Start event frame for component a
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': '86b76988-5549-482b-8401-444b2621641e',
      'startTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 678133),
      'endTime': None,
      'inputs': {
          'a_num': 1,
      },
      'outputs': None,
      'error': None,
      'invokeId': 'a',
      'parentInvokeId': 'start',
      'executionId': '86b76988-5549-482b-8401-444b2621641e',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'a',
      'loopNodeId': None,
      'loopIndex': None,
      'status': 'start',
      'parentNodeId': ''
  })
  # End event frame for component a
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': '86b76988-5549-482b-8401-444b2621641e',
      'startTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 678133),
      'endTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 679167),
      'inputs': {
          'a_num': 1,
      },
      'outputs': {
          'a_num': 1,
      },
      'error': None,
      'invokeId': 'a',
      'parentInvokeId': 'start',
      'executionId': '86b76988-5549-482b-8401-444b2621641e',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'a',
      'loopNodeId': None,
      'loopIndex': None,
      'status': 'finish',
      'parentNodeId': ''
  })
  ```

- Example 2: Output from a looped workflow using [BaseStreamMode.TRACE](#class-openjiuwencorestreambasebasestreammode).

  ```python
  import datetime
  from openjiuwen.core.stream.base import TraceSchema
  # Below is an excerpt of the trace information for component `a` inside a loop. You will see two frames: a start event and an end event.
  # `loopIndex` indicates that the component is inside the loop component `loop` and its value is 3, meaning this is the 3rd iteration.
  # At the same time, the component `a` inside the loop has `invokeId` = `loop.a`, and `parentInvokeId` = `loop.c`,
  # which indicates that the previously executed component was component `c` inside the loop body in the previous iteration.

  # Start frame of the 3rd run of component a inside the loop
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': 'dad9cd8c-ac77-484f-90ae-20b263276e3f',
      'startTime': datetime.datetime(2025, 8, 25, 19, 31, 48, 361042),
      'endTime': None,
      'inputs': {
          'value': 3
      },
      'outputs': None,
      'error': None,
      'invokeId': 'loop.a',
      'parentInvokeId': 'loop.c',
      'executionId': 'dad9cd8c-ac77-484f-90ae-20b263276e3f',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'loop.c',
      'loopNodeId': 'loop',
      'loopIndex': 3,
      'status': 'start',
      'parentNodeId': ''
    })
  # End frame of the 3rd run of component a inside the loop
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': 'dad9cd8c-ac77-484f-90ae-20b263276e3f',
      'startTime': datetime.datetime(2025, 8, 25, 19, 31, 48, 361042),
      'endTime': datetime.datetime(2025, 8, 25, 19, 31, 48, 361042),
      'inputs': {
          'value': 3
      },
      'outputs': {
          'output': 3
      },
      'error': None,
      'invokeId': 'loop.a',
      'parentInvokeId': 'loop.c',
      'executionId': 'dad9cd8c-ac77-484f-90ae-20b263276e3f',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'loop.a',
      'loopNodeId': 'loop',
      'loopIndex': 3,
      'status': 'finish',
      'parentNodeId': ''
    })
  ...
  ```

- Example 3: Output from a nested workflow using [BaseStreamMode.TRACE](#class-openjiuwencorestreambasebasestreammode).

  ```python
  import datetime
  from openjiuwen.core.stream.base import TraceSchema
  # Below is an excerpt of the trace information for component `sub_a` inside a sub-workflow.
  # You will see two frames: a start event and an end event.
  # The `parentNodeId` field records the `invokeId` of the sub-workflow it belongs to, i.e., "a".
  # This field is used in nested sub-workflow scenarios to clarify hierarchy and ownership.
  # Since `sub_a` is inside sub-workflow component `a`, its `invokeId` is "a.sub_a", which identifies this component within the entire workflow.

  # Start frame for the sub_a component in the sub-workflow
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': '416c45dd-12f1-427e-943f-e16c2171c69d',
      'startTime': datetime.datetime(2025, 8, 22, 17, 38, 13, 535141),
      'endTime': None,
      'inputs': {
        'a_num': 1
      },
      'outputs': None,
      'error': None,
      'invokeId': 'a.sub_a',
      'parentInvokeId': 'a.sub_start',
      'executionId': '416c45dd-12f1-427e-943f-e16c2171c69d',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'a.sub_a',
      'loopNodeId': None,
      'loopIndex': None,
      'status': 'start',
      'parentNodeId': 'a'
  }), 
  # End frame for the sub_a component in the sub-workflow
  TraceSchema(type = 'tracer_workflow', payload = {
      'traceId': '416c45dd-12f1-427e-943f-e16c2171c69d',
      'startTime': datetime.datetime(2025, 8, 22, 17, 38, 13, 535141),
      'endTime': datetime.datetime(2025, 8, 22, 17, 38, 13, 535141),
      'inputs': {
        'a_num': 1
      },
      'outputs': {
        'a_num': 1,
      },
      'error': None,
      'invokeId': 'a.sub_a',
      'parentInvokeId': 'a.sub_start',
      'executionId': '416c45dd-12f1-427e-943f-e16c2171c69d',
      'onInvokeData': None,
      'componentId': '',
      'componentName': '',
      'componentType': 'a.sub_a',
      'loopNodeId': None,
      'loopIndex': None,
      'status': 'finish',
      'parentNodeId': 'a'
  })
  ...
  ```