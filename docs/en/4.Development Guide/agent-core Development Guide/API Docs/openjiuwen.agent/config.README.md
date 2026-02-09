## `openjiuwen.agent.config`

`openjiuwen.agent.config` is the core configuration module in **openJiuwen** used to define various Agent runtime parameters, model configurations, invocation templates, and constraint policies.

**Classes**:

| CLASS                   | DESCRIPTION                                                                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AgentConfig`           | The base class for all Agent configurations, defining the fundamental properties of an Agent.                                                        |
| `ConstrainConfig`       | Used to configure constraint and limitation parameters when creating an Agent.                                                                       |
| `IntentDetectionConfig` | A reserved class for configuring parameters related to intent detection. It is currently only an interface definition and not yet supported for use. |
| `ReActAgentConfig`      | Used to configure all parameters of a ReActAgent.                                                                                                    |
| `WorkflowAgentConfig`   | Used to configure all parameters of a WorkflowAgent.                                                                                                 |
