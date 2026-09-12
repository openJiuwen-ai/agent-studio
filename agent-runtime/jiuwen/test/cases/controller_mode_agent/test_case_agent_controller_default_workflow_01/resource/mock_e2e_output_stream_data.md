## test_1：首次调用的流式输出数据帧

```text
data: {"event":"start","data":{},"createdTime":1775733191629,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"task_start","data":{},"createdTime":1775733191631,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"83a951bc-27d7-4ccc-9131-268e93267365"},"createdTime":1775733557677,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？","node_id":"node_1747116170373","node_name":"提问器","node_type":"jiuwen.questioner","should_interrupt":true,"workflow_id":"83a951bc-27d7-4ccc-9131-268e93267365"},"createdTime":1775733557687,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？","node_id":"node_1747116170373","node_name":"提问器","node_type":"jiuwen.questioner","should_interrupt":true,"enable_history":true,"workflow_id":"83a951bc-27d7-4ccc-9131-268e93267365"},"createdTime":1775733557690,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"","node_id":"node_1747116170373","user_fields":{},"node_type":"jiuwen.questioner","workflow_id":"83a951bc-27d7-4ccc-9131-268e93267365"},"createdTime":1775733557693,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"workflow_blocked","data":{"node_id":"node_1747116170373","node_name":"提问器","node_type":"jiuwen.questioner","workflow_name":"YHFinanceProductSelect0607_1","workflow_id":"83a951bc-27d7-4ccc-9131-268e93267365","query":"给我推荐一个理财产品","intent_id":"YHFinanceProductSelect0607_1","intent_name":"YHFinanceProductSelect0607_1","time":1775733557695,"execution_id":"e7745b91-de11-4073-a2f9-39382e0d72d0"},"createdTime":1775733557695,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"intermediate_message","data":{"answer":[{"role":"user","content":"给我推荐一个理财产品","function_call":[],"intent":["YHFinanceProductSelect0607_1"],"enable_history":true},{"role":"assistant","content":"您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？","function_call":[],"intent":["YHFinanceProductSelect0607_1"],"enable_history":true}]},"createdTime":1775733564137,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}

data: {"event":"agent_interrupted","data":{"type":"controller_agent_interrupt","reason":"任务被中断","task_id":"e7745b91-de11-4073-a2f9-39382e0d72d0","message":"控制器任务执行被中断"},"createdTime":1775733564137,"executionId":"e7745b91-de11-4073-a2f9-39382e0d72d0","index":0,"isStructMessage":false}
```

## test_2：第二次调用的流式输出数据帧

```text
data: {"event":"start","data":{},"createdTime":1775733999954,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"task_start","data":{},"createdTime":1775733999956,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747303,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"","node_id":"node_1753769873590","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747314,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"珠穆朗玛峰","node_id":"node_1753769873590","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747317,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":1,"isStructMessage":false}

data: {"event":"message","data":{"answer":"","node_id":"node_1753769873590","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747321,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":2,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"珠穆朗玛峰","node_id":"node_1753769873590","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747323,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747326,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734747329,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"ef802b42-9f76-4fb3-bfbb-910e5c091ced"},"createdTime":1775734748832,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734754968,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"结束工作流","node_id":"node_1748098633016","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734754972,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"结束工作流","node_id":"node_1748098633016","node_name":"消息","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734754973,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734754977,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734754979,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67"},"createdTime":1775734756150,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"task_terminated","data":{"node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","workflow_name":"xxxtest_1_1_1","workflow_id":"6bcb3df8-0f29-41fd-a583-273414629b67","query":"世界上最高的山","intent_id":"xxxtest_1_1_1","intent_name":"xxxtest_1_1_1","time":1775734756152,"execution_id":"ffa9709f-13cc-4c0d-94d9-115d48ae0181"},"createdTime":1775734756152,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}

data: {"event":"task_end","data":{},"createdTime":1775734757503,"executionId":"ffa9709f-13cc-4c0d-94d9-115d48ae0181","index":0,"isStructMessage":false}
```