## react_agent

`openjiuwen.agent.react_agent` is an Agent module in openJiuwen that provides capabilities for creating and executing a ReactAgent.

---

### **Classes**

| CLASS          | DESCRIPTION                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ReActAgent** | ReActAgent is an intelligent agent that follows the ReAct (Reasoning + Action) framework, adopting an iterative loop of “Think (Thought) → Act (Action) → Observe (Observation)” to complete user tasks. In each iteration, the model first performs logical reasoning to plan and decide which tools to use (such as retrieval systems, databases, third-party APIs, or code execution). It then executes the selected actions and observes the returned results, using this feedback to dynamically adjust its strategy and refine its reasoning path until the task is completed or a final answer is produced. With strong multi-step reasoning and self-correction capabilities, ReActAgent demonstrates excellent dynamic decision-making and adaptability, making it well suited for diverse task scenarios that require complex reasoning and strategic adjustments. |

---

### **Functions**

| FUNCTION                      | DESCRIPTION                                |
| ----------------------------- | ------------------------------------------ |
| **create_react_agent_config** | Creates a ReActAgent configuration object. |
