# openjiuwen.core.component.break_comp

## class openjiuwen.core.component.break_comp.BreakComponent

A loop break component used to control loop termination. It provides workflows with a strong loop-interruption capability, allowing a loop to be proactively terminated under specific conditions. When execution reaches this component, the loop stops immediately.

> **Notes**
>
> - `BreakComponent` can be used together with [LoopComponent](./loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent) and `loop_type="always_true"` (infinite loop). By configuring an infinite loop, the loop continues executing until it encounters a break component, at which point it exits.
> - It can be combined with conditional components to implement more complex conditional break logic, such as breaking the loop only when specific conditions are met.
> - Within a loop body, the execution order of `BreakComponent` affects when the loop is interrupted, so its position inside the loop must be arranged carefully.

Example:

```python
import asyncio
from openjiuwen.core.component.branch_comp import BranchComponent
from openjiuwen.core.component.break_comp import BreakComponent
from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
from openjiuwen.core.component.set_variable_comp import SetVariableComponent
from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.runtime.base import ComponentExecutable
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.runtime import Runtime

# Custom component AddTenNode:
# On each invocation, add 10 to inputs["source"]
class AddTenNode(ComponentExecutable, WorkflowComponent):
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    async def invoke(self, inputs, runtime: Runtime, context: Context):
        return {"result": inputs["source"] + 10}

# Empty node used to mark the end of the loop body
class EmptyNode(ComponentExecutable, WorkflowComponent):
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id

    async def invoke(self, inputs, runtime: Runtime, context: Context):
        return inputs

# Execution test
# input_number = 2, loop_number = 2: execute the loop twice
async def run_workflow():
    flow = Workflow()
    flow.set_start_comp("s", Start({"inputs": []}))
    flow.set_end_comp(
        "e",
        End({}),
        inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"}
    )

    # Create the loop body
    loop_group = LoopGroup()

    # AddTenNode("1"):
    # Takes the current loop index l.index as input.
    # The loop index is automatically incremented on each iteration.
    #
    # Note:
    # "1" is the component identifier, used to reference its result in output_schema.
    loop_group.add_workflow_comp(
        "1",
        AddTenNode("1"),
        inputs_schema={"source": "${l.index}"}
    )

    # AddTenNode("2"):
    # Takes the intermediate variable l.user_var as input.
    loop_group.add_workflow_comp(
        "2",
        AddTenNode("2"),
        inputs_schema={"source": "${l.user_var}"}
    )

    # SetVariableComponent:
    # Updates the intermediate variable l.user_var using the result of AddTenNode("2").
    # This allows the intermediate variable to be updated based on the previous iteration.
    set_variable_component = SetVariableComponent({"${l.user_var}": "${2.result}"})
    loop_group.add_workflow_comp("3", set_variable_component)

    # Add a branch component to determine whether to continue looping.
    # BranchComponent selects different execution paths based on conditions.
    sw = BranchComponent()

    # First branch condition:
    # When the current loop index (l.index) is greater than or equal to (loop_number - 1),
    # execute the BreakComponent.
    #
    # Note:
    # The loop index starts from 0.
    # For 3 iterations, the index values are 0, 1, 2.
    # When index == 2, the loop should be interrupted.
    sw.add_branch("${l.index} >= ${loop_number} - 1", ["4"], "1")

    # Second branch condition:
    # When the current loop index is less than (loop_number - 1),
    # proceed to the loop end node and start the next iteration.
    #
    # Note:
    # Branch targets must be nodes inside the loop body;
    # otherwise, a "Channel not found" error will occur.
    sw.add_branch("${l.index} < ${loop_number} - 1", ["5"], "2")

    loop_group.add_workflow_comp("sw", sw)

    # Add the break component.
    # BreakComponent explicitly interrupts loop execution when conditions are met.
    #
    # This is the key component for controlling loop execution
    # when using the always_true loop type.
    break_node = BreakComponent()
    loop_group.add_workflow_comp("4", break_node)

    # Add an empty node as the loop end marker.
    empty_node = EmptyNode("5")
    loop_group.add_workflow_comp("5", empty_node)

    # Configure the start and end nodes of the loop body.
    loop_group.start_nodes(["1"])
    loop_group.end_nodes(["5"])

    # Define connections between components in the loop body.
    loop_group.add_connection("1", "2")
    loop_group.add_connection("2", "3")
    loop_group.add_connection("3", "sw")
    loop_group.add_connection("4", "5")

    # Create LoopComponent.
    #
    # Argument 1: loop_group
    #   The defined loop body.
    #
    # Argument 2: output_schema
    #   Defines the output structure of the loop component:
    #   - results: collects the result of AddTenNode("1") from each iteration into an array
    #   - user_var: preserves the final value of the intermediate variable after the loop ends
    loop_component = LoopComponent(
        loop_group,
        {"results": "${1.result}", "user_var": "${l.user_var}"}
    )

    # Add the loop component to the workflow.
    #
    # loop_type = "always_true":
    #   The loop runs continuously until interrupted by BreakComponent.
    #
    # intermediate_var:
    #   Initialises intermediate variables inside the loop.
    #   Here, user_var is initialised using input_number.
    #
    # In always_true loops, BreakComponent must be used
    # to control loop termination.
    flow.add_workflow_comp(
        "l",
        loop_component,
        inputs_schema={
            "loop_type": "always_true",
            "intermediate_var": {"user_var": "${input_number}"}
        }
    )

    flow.add_connection("s", "l")
    flow.add_connection("l", "e")

    return await flow.invoke(
        {"input_number": 2, "loop_number": 2},
        WorkflowRuntime()
    )

if __name__ == "__main__":
    result = asyncio.get_event_loop().run_until_complete(run_workflow())
    print(result.result)

# Expected result explanation:
#
# - array_result: [10, 11]
#   This is the array of results produced by AddTenNode("1") in each iteration:
#   index 0 + 10 = 10
#   index 1 + 10 = 11
#
# - user_var: 22
#   The final value of the intermediate variable after the loop ends.
#   Computation:
#   initial value 2 → 2 + 10 = 12 → 12 + 10 = 22
#
# In an always_true loop, the number of iterations is jointly controlled
# by the branch conditions and BreakComponent.
#
# In this example, the loop is interrupted when:
# l.index >= loop_number - 1
# (1 >= 2 - 1 = 1)

{'output': {'array_result': [10, 11], 'user_var': 22}}
```