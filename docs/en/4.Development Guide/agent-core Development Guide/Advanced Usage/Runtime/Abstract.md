Runtime is the core execution engine and management framework for agents (Agent) and workflows (Workflow), providing an isolated, stable runtime environment for executing tasks. By abstracting the complexity of underlying infrastructure, Runtime enables unified scheduling and governance across the full lifecycle of tasks.

The core advantages of Runtime include:

* **Stateful session management**: Maintains the complete runtime and intermediate state throughout task execution, supports transactional operations and checkpoint resume, ensuring the consistency and reliability of complex tasks.
* **Dynamic configuration management**: Centrally manages Agent configuration parameters and Workflow configuration parameters, ensuring tasks can read configurations at any time during execution.
* **Structured message streams**: Natively supports real-time streaming of text and structured intermediate results (such as reasoning steps and tool invocation events), providing an immersive interactive experience for the frontend.
* **Controlled execution flow**: Offers standardized mechanisms for interrupt, pause, rollback, and resume, giving developers and systems unprecedented fine-grained control over long-running tasks.
* **Deep observability**: Automatically tracks and records end-to-end telemetry data from reasoning chains and tool calls to API requests, providing a single source of truth for performance profiling, cost auditing, and root cause analysis.
* **Unified resource governance**: As an abstraction layer for all dependent resources, it unifies the management of large models, tool functions, prompt templates, and more, implementing efficient connection pooling, lifecycle, and quota control.

## Basic Features

* **Configuration Management**: Runtime manages Agent and Workflow configuration information. During the creation of an Agent or Workflow, configuration information is stored in Runtime; during execution, Runtime allows reading all stored configuration information.
* **State Management**: Runtime manages execution state data. During the execution of an Agent or Workflow, data can be read and written through the interfaces provided by Runtime.
* **Resource Management**: Runtime implements high-performance resource pools to unify the management of heavyweight instances such as workflows, prompts, tools, and large models.
* **Diagnostics and Debugging**: Runtime has a built-in end-to-end diagnostics module that provides real-time, layered runtime insights for workflow execution. Through automated fine-grained event collection and open extension interfaces, it transparently presents internal system states to developers.
* **Streaming Output**: Runtime includes a high-performance structured streaming output module that streams data in real time to outside of the workflow or Agent, providing efficient, real-time data processing and delivery during workflow and Agent execution.
* **Interrupt Recovery**: Runtime has built-in interrupt recovery capabilities. When execution needs to resume, the system automatically loads saved snapshot data to achieve seamless continuation. During execution, if an interruption or exception occurs, Runtime immediately takes the following measures: first, snapshot the current state; second, notify the user in real time via streaming messages.