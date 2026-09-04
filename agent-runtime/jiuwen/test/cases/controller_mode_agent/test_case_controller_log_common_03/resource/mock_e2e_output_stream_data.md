## test_1：首次调用的流式输出数据帧

```text
data: {"event":"start","data":{},"createdTime":1775721961659,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"task_start","data":{},"createdTime":1775721961660,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"dfac616f-95d5-425a-aa52-e5432f24624a"},"createdTime":1775721961674,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"您好，这里是银行，请问你是tom先生吗？","node_id":"node_1747663017657","node_name":"提问器","node_type":"jiuwen.questioner","should_interrupt":true,"workflow_id":"dfac616f-95d5-425a-aa52-e5432f24624a"},"createdTime":1775721961677,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"您好，这里是银行，请问你是tom先生吗？","node_id":"node_1747663017657","node_name":"提问器","node_type":"jiuwen.questioner","should_interrupt":true,"enable_history":true,"workflow_id":"dfac616f-95d5-425a-aa52-e5432f24624a"},"createdTime":1775721961679,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"","node_id":"node_1747663017657","user_fields":{"name":"tom","continue":true,"age":25},"node_type":"jiuwen.questioner","workflow_id":"dfac616f-95d5-425a-aa52-e5432f24624a"},"createdTime":1775721961681,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"workflow_blocked","data":{"node_id":"node_1747663017657","node_name":"提问器","node_type":"jiuwen.questioner","workflow_name":"开始工作流","workflow_id":"dfac616f-95d5-425a-aa52-e5432f24624a","query":"你好","intent_id":"开始工作流","intent_name":"开始工作流","time":1775721961681,"execution_id":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a"},"createdTime":1775721961681,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"intermediate_message","data":{"answer":[{"role":"user","content":"你好","function_call":[],"intent":["开始工作流"],"enable_history":true},{"role":"assistant","content":"您好，这里是银行，请问你是tom先生吗？","function_call":[],"intent":["开始工作流"],"enable_history":true}]},"createdTime":1775721961682,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}

data: {"event":"agent_interrupted","data":{"type":"controller_agent_interrupt","reason":"任务被中断","task_id":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","message":"控制器任务执行被中断"},"createdTime":1775721961682,"executionId":"9472bb80-5ec9-4d2c-8c77-fe5806e0821a","index":0,"isStructMessage":false}
```

## test_2：第二次调用的流式输出数据帧

```text
data: {"event":"start","data":{},"createdTime":1775722003001,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003002,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"低至 3.35%","node_id":"node_1747039591166","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003005,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"低至 3.35%","node_id":"node_1747039591166","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003007,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003010,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003013,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8"},"createdTime":1775722003014,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"task_terminated","data":{"node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","workflow_name":"faq_1","workflow_id":"aacb7592-31ff-4741-a079-cfc187cabff8","query":"开始跳","intent_id":"faq_1","intent_name":"faq_1","time":1775722003014,"execution_id":"762bb089-435c-49a7-97b4-64f03c21fa34"},"createdTime":1775722003014,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775722003023,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775722003026,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775722003027,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775722003029,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"## 流程结束","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775722003032,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"task_terminated","data":{"node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","workflow_name":"结束工作流","workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c","query":"开始跳","intent_id":"结束工作流","intent_name":"结束工作流","time":1775722003033,"execution_id":"762bb089-435c-49a7-97b4-64f03c21fa34"},"createdTime":1775722003033,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}

data: {"event":"task_end","data":{},"createdTime":1775722003034,"executionId":"762bb089-435c-49a7-97b4-64f03c21fa34","index":0,"isStructMessage":false}
```
