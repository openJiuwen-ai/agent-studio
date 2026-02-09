# openjiuwen.core.component.branch_comp

## class openjiuwen.core.component.branch_comp.BranchComponent

`BranchComponent` is an openJiuwen built-in workflow branching component. It provides multi-branch conditional evaluation and the ability to dynamically route workflow execution to target components. It is used to design branching flows in a workflow and implement decision/conditional logic.

> **Notes**
> The branching component is optional. If you add this component to a workflow, you do **not** need to explicitly call the workflow’s [add_connection](../workflow/base.md) or [add_conditional_connection](../workflow/base.md#add_conditional_connection) methods to define edges between this component and its target component(s). You must follow these constraints:
>
> * Input: You can add multiple conditional branches. However, you must ensure that at least one branch will satisfy its preset condition at runtime so that the workflow can continue executing. Branch condition evaluation follows these rules:
>   * The component evaluates branch conditions **in order**, checking whether the current workflow data/state satisfies each branch’s preset condition. Once it finds a branch whose condition is met, it immediately jumps to that branch’s target component(s) and stops evaluating the remaining branches.
>   * If **none** of the branches match, the workflow execution fails and throws a `JiuWenBaseException` with error code `101102` and error message `"Branch meeting the condition was not found."`.
> * Output: You can route the workflow to one or more predefined target components via conditional branches. Note that the returned target component IDs are used to control workflow routing. To avoid invalid branches, all target component IDs must refer to components that have already been defined/registered in the workflow. If the branch logic returns a **single** target component, the workflow executes that component immediately after the branch component. If it returns **multiple** target components, the workflow schedules and executes those target components **in parallel** via the task scheduling mechanism.

### add_branch

```python
add_branch(condition: Union[str, Callable[[], bool], Condition], target: Union[str, list[str]], branch_id: str = None)
```

The `add_branch` function adds a branch rule to the branching component, including the branch condition, target component(s), and an optional branch identifier.

**Parameters**:

* **condition** (Union[str, Callable[[], bool], Condition]): The preset condition for this branch. `condition` must not be `None`. Supported types:
  
  * If `str`: a boolean expression in string form. The expression rules follow [ExpressionCondition](./condition/expression.md#class-openjiuwencorecomponentconditionexpressionexpressioncondition).
  * If `Callable[[], bool]`: a callable returning a `bool` indicating whether the condition is met. Example:

    ```python
    >>> def branch_function() -> bool:
    >>>     return True
    ```

  * If `Condition`: a predefined, callable `openjiuwen.core.component.condition.condition.Condition` object.
* **target** (Union[str, list[str]]): The target component ID (single) or a list of target component IDs to jump to when the condition is satisfied. `target` must not be `None`, `''`, or `[]`. Supported types:
  
  * If `str`: a single target component ID.
  * If `list[str]`: a list of target component IDs; items must not be `None` or `''`.
* **branch_id** (str, optional): An identifier/name for this branch. Default: `None`.

**Exceptions**:

* **JiuWenBaseException**: Base exception class in openJiuwen. For details and solutions, see [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

This example shows how to build a workflow with a branch component. The workflow input is a number, and the branch component routes execution based on its value:

* Branch `pos_branch`: if the number is positive, execute the End component directly.
* Branch `neg_branch`: if the number is negative, execute a custom absolute-value component, then execute the End component.
* Branch `zero_branch`: if the number is zero, route based on the environment variable `ALLOW_ZERO`. If `ALLOW_ZERO` is `true`, execute the absolute-value component and then End; otherwise, no branch matches, so the workflow fails and throws an exception.

```python
>>> import asyncio
>>> import os
>>> from openjiuwen.core.common.exception.exception import JiuWenBaseException
>>> from openjiuwen.core.component.condition.expression import ExpressionCondition
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow, WorkflowOutput
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> 
>>> 
>>> class AbsComponent(ComponentExecutable, WorkflowComponent):
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         num = inputs["num"]
...         if num < 0:
...             return {"result": -num}
...         return {"result": num}
>>> 
>>> 
>>> async def run_workflow(num: int) -> tuple[WorkflowOutput | str, bool]:
...     # Construct the workflow and initialise the workflow runtime
...     workflow = Workflow()
...     runtime = WorkflowRuntime()
... 
...     # Add Start and End components to the workflow
...     workflow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"raw": "${start.query}", "updated": "${abs.result}"})
... 
...     # Add a custom component that computes absolute value
...     abs_comp = AbsComponent()
...     workflow.add_workflow_comp("abs", abs_comp, inputs_schema={"num": "${start.query}"})
... 
...     # Add the Branch component
...     branch_comp = BranchComponent()
...     # 1. pos_branch: condition is a str
...     expression_str = "${start.query} > 0"
...     branch_comp.add_branch(expression_str, ["end"], "pos_branch")
... 
...     # 2. neg_branch: condition is a Condition
...     expression_condition = ExpressionCondition("${start.query} < 0")
...     branch_comp.add_branch(expression_condition, ["abs"], "neg_branch")
... 
...     # 3. zero_branch: condition is a Callable[[], bool]
...     def expression_callable() -> bool:
...         return str(os.environ.get("ALLOW_ZERO", "false")).lower() == "true"
... 
...     branch_comp.add_branch(expression_callable, ["abs"], "zero_branch")
...     workflow.add_workflow_comp("branch", branch_comp)
... 
...     # Define edges: conditional edges from the Branch component do not require explicit add_connection/add_conditional_connection
...     workflow.add_connection("start", "branch")
...     workflow.add_connection("abs", "end")
... 
...     # Build inputs and invoke the workflow
...     inputs = {"user_inputs": {"query": num}}
... 
...     try:
...         workflow_output = await workflow.invoke(inputs, runtime)
...         return workflow_output, True
...     except JiuWenBaseException as e:
...         print(f"workflow execute error: {e}")
...         return e.message, False
...
>>> async def main():
...     # Input 10: matches pos_branch; executes start -> branch -> end; succeeds.
...     workflow_output, run_success = await run_workflow(num=10)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == 10
...     assert result.get("output", {}).get("updated") is None
...     print(result)
... 
...     # Input -10: matches neg_branch; executes start -> branch -> abs -> end; succeeds.
...     workflow_output, run_success = await run_workflow(num=-10)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == -10
...     assert result.get("output", {}).get("updated") == 10
...     print(result)
... 
...     # Input 0, ALLOW_ZERO=true: matches zero_branch; executes start -> branch -> abs -> end; succeeds.
...     os.environ["ALLOW_ZERO"] = "true"
...     workflow_output, run_success = await run_workflow(num=0)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == 0
...     assert result.get("output", {}).get("updated") == 0
...     print(result)
... 
...     # Input 0, ALLOW_ZERO=false: no branch matches; workflow fails and throws an exception.
...     os.environ["ALLOW_ZERO"] = "false"
...     workflow_output, run_success = await run_workflow(num=0)
...     assert run_success is False
...     assert workflow_output == "Branch meeting the condition was not found."
...     print(workflow_output)
...
>>> asyncio.run(main())
{'output': {'raw': 10}}
{'output': {'raw': -10, 'updated': 10}}
{'output': {'raw': 0, 'updated': 0}}
workflow execute error: [101102] Branch meeting the condition was not found.
Branch meeting the condition was not found.
```
