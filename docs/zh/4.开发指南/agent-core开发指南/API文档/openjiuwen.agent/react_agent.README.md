# react_agent

`openjiuwen.agent.react_agent`是openJiuwen中的Agent模块，提供ReactAgent的创建和执行等能力。


**Classes**：

| CLASS                                                 | DESCRIPTION               |
|-------------------------------------------------------| ------------------------- |
| [ReActAgent](./react_agent.md#class-openjiuwenagentreact_agentreactagent)                             | ReActAgent是一种遵循ReAct（Reasoning + Action）框架的智能体，采用“思考（Thought）→ 行动（Action）→ 观察（Observe）”的循环机制来迭代完成用户任务。在每一轮迭代中，模型首先通过逻辑推理制定规划，选择并调用相应工具（如检索系统、数据库、第三方API或代码执行等）来执行操作，随后根据返回的结果进行观察与反馈，进而动态调整策略、优化推理路径，直至完成任务或得出最终答案。凭借其强大的多轮推理与自我修正能力，ReActAgent具备出色的动态决策与灵活应变特性，能够有效应对需要复杂推理和策略调整的多样化任务场景。        |

**Functions**：

| FUNCTION                                                                                                             | DESCRIPTION                                   |
| -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| [create_react_agent_config](./react_agent.md#create_react_agent_config)     | 创建ReActAgent配置对象。    |