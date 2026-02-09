# openjiuwen.core.component.branch_router

## class openjiuwen.core.component.branch_router.BranchRouter

```python
class openjiuwen.core.component.branch_router.BranchRouter(report_trace: bool = False)
```

`BranchRouter` is the core class that implements a branch router. It provides the ability to manage and switch between different execution branches, and is used to design branching flows in a workflow. It is typically used together with the workflow method [add_conditional_connection](../workflow/base.md#add_conditional_connection). After the source component finishes execution, the workflow invokes the `BranchRouter` (as a callable) and uses its return value to determine the next step in the workflow. If none of the branches managed by the router satisfies the preset conditions, a `JiuWenBaseException` is raised with error code **101102** and the message `"Branch meeting the condition was not found."`.

**Parameters**:

* **report_trace** (bool, optional): Diagnostic trace recording flag. `True` means the workflow will record and report the execution status of each branch; `False` means it will not. Default: `False`.

### add_branch

```python
add_branch(self, condition: Union[str, Callable[[], bool], Condition], target: Union[str, list[str]], branch_id: str = None)
```

The `add_branch` method adds a branch rule to the router, including the preset condition, target component(s), and the branch identifier.

**Parameters**:

* **condition** (Union[str, Callable[[], bool], Condition]): The preset condition for this branch. Must not be `None`. `condition` supports the following three types:

  * If `str`, it is a boolean expression in string form. The expression rules are described in [ExpressionCondition](./condition/expression.md#class-openjiuwencorecomponentconditionexpressionexpressioncondition).
  * If `Callable[[], bool]`, it is a function that returns a boolean indicating whether the condition is satisfied. Example:

    ```python
    def branch_function() -> bool:
        return True
    ```

  * If `Condition`, it is a predefined callable `openjiuwen.core.component.condition.condition.Condition` object.

* **target** (Union[str, list[str]]): The target component ID (single) or list of target component IDs to jump to when the condition is satisfied. Must not be `None`. `target` supports the following two types:

  * If `str`, it is the component ID of a single target component.
  * If `list[str]`, it is a list of component IDs for multiple target components.

* **branch_id** (str, optional): Identifier for this conditional branch. Default: `None`.

**Exceptions**:

* **JiuWenBaseException**: Base exception class for openJiuwen. For details and resolution methods, see [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**:

This example introduces branch router usage by adding conditional edges in a workflow. The workflow input is a number, and different conditional branches are added using `add_conditional_connection` based on the number’s value:

* Branch `pos_branch`: If the number is positive, execute the end component directly.
* Branch `neg_branch`: If the number is negative, execute a custom absolute-value component, then execute the end component.
* Branch `zero_branch`: If the number is zero, route based on the user-defined environment variable `ALLOW_ZERO`. If `ALLOW_ZERO` is `true`, execute the absolute-value component and then the end component; otherwise, no branch matches, the workflow fails, and an exception is raised.

```python
>>> import asyncio
>>> import os
>>> 
>>> from openjiuwen.core.common.exception.exception import JiuWenBaseException
>>> from openjiuwen.core.component.branch_router import BranchRouter
>>> from openjiuwen.core.component.condition.expression import ExpressionCondition
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow, WorkflowOutput
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
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
...     # Build the workflow and initialise the workflow runtime
...     workflow = Workflow()
...     runtime = WorkflowRuntime()
... 
...     # Add start and end components
...     workflow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"raw": "${start.query}", "updated": "${abs.result}"})
... 
...     # Add a custom component that computes absolute value
...     abs_comp = AbsComponent()
...     workflow.add_workflow_comp("abs", abs_comp, inputs_schema={"num": "${start.query}"})
... 
...     # Define the branch router and add branches
...     router = BranchRouter()
... 
...     # 1. pos_branch: condition is a str
...     expression_str = "${start.query} > 0"
...     router.add_branch(expression_str, ["end"], "pos_branch")
... 
...     # 2. neg_branch: condition is a Condition
...     expression_condition = ExpressionCondition("${start.query} < 0")
...     router.add_branch(expression_condition, ["abs"], "neg_branch")
... 
...     # 3. zero_branch: condition is a Callable[[], bool]
...     def expression_callable() -> bool:
...         return str(os.environ.get("ALLOW_ZERO", "false")).lower() == "true"
... 
...     router.add_branch(expression_callable, ["abs"], "zero_branch")
... 
...     # Define node connections
...     workflow.add_conditional_connection("start", router=router)
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
...     # When input is 10, pos_branch is selected: start -> branch -> end
...     workflow_output, run_success = await run_workflow(num=10)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == 10
...     assert result.get("output", {}).get("updated") is None
...     print(result)
... 
...     # When input is -10, neg_branch is selected: start -> branch -> abs -> end
...     workflow_output, run_success = await run_workflow(num=-10)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == -10
...     assert result.get("output", {}).get("updated") == 10
...     print(result)
... 
...     # When input is 0 and ALLOW_ZERO=true, zero_branch is selected: start -> branch -> abs -> end
...     os.environ["ALLOW_ZERO"] = "true"
...     workflow_output, run_success = await run_workflow(num=0)
...     assert run_success is True
...     assert workflow_output is not None
...     result = workflow_output.result
...     assert result.get("output", {}).get("raw") == 0
...     assert result.get("output", {}).get("updated") == 0
...     print(result)
... 
...     # When input is 0 and ALLOW_ZERO=false, no branch matches; the workflow fails and raises an exception.
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
