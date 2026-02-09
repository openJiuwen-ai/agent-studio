# openjiuwen.agent.common.enum

## class `openjiuwen.agent.common.enum.ControllerType`

Defines the types of controllers.

* **ReActController**: A controller of the ReAct type.
* **WorkflowController**: A controller of the Workflow type.
* **Undefined**: An undefined controller type.

---

## class `openjiuwen.agent.common.enum.TaskType`

Defines the types of sub-tasks.

* **PLUGIN**: A plugin-type sub-task.
* **WORKFLOW**: A workflow-type sub-task.
* **MCP**: An MCP-type sub-task.
* **UNDEFINED**: An undefined sub-task type.

---

## class `openjiuwen.agent.common.enum.TaskStatus`

Defines the execution status of a task.

* **PENDING**: Created but not yet started.
* **RUNNING**: Currently executing.
* **SUCCESS**: Successfully completed.
* **FAILED**: Ended with an exception.
* **CANCELLED**: Cancelled.
* **INTERRUPTED**: Interrupted and waiting for user input.

---

## class `openjiuwen.agent.common.enum.ReActControllerStatus`

Defines the status of a ReAct controller.

* **NORMAL**: Normal running state.
* **INTERRUPTED**: Interrupted state.
* **COMPLETED**: Completed state.
* **TIMEOUT**: Timeout state.

---
