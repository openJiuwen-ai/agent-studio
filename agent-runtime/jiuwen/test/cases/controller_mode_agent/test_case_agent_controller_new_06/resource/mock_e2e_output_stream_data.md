## test_1：最后一次调用的流式输出数据帧（因为只需要校验这部分）

```text
data: {"event":"start","data":{},"createdTime":1775874450393,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"workflow_resume","data":{"node_id":"node_1747212899505","node_name":"开场白-提问器","node_type":"jiuwen.questioner","workflow_name":"ShengjinyouliAgent517_1_1_1","workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30","query":"升金感兴趣","intent_id":"ShengjinyouliAgent517_1_1_1","intent_name":"ShengjinyouliAgent517_1_1_1","time":1775874450393,"execution_id":"11fdd50a-dd8a-43de-934c-1b2661f80fde"},"createdTime":1775874450393,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":" ##系统插件，发短信##","node_id":"node_1747293876339","node_name":"发短息","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874517983,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":" ##系统插件，发短信##","node_id":"node_1747293876339","node_name":"发短息","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874517985,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！","node_id":"node_1747293794534","node_name":"成功结束","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874517989,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！","node_id":"node_1747293794534","node_name":"成功结束","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874517990,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"##升金结束continue: ","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523090,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"False","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523092,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":1,"isStructMessage":false}

data: {"event":"message","data":{"answer":"。action_after_completion：","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523093,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":2,"isStructMessage":false}

data: {"event":"message","data":{"answer":"Terminal","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523094,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":3,"isStructMessage":false}

data: {"event":"message","data":{"answer":"","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523094,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":4,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"##升金结束continue: False。action_after_completion：Terminal","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"outputs":{"user_fields":{"continue":false,"action_after_completion":"Terminal"}},"enable_history":true,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523097,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"##升金结束continue: False。action_after_completion：Terminal","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523099,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"##升金结束continue: False。action_after_completion：Terminal","node_id":"node_end","user_fields":{"continue":false,"action_after_completion":"Terminal"},"node_type":"jiuwen.end","workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30"},"createdTime":1775874523102,"executionId":"11fdd50a-dd8a-43de-934c-1b2661f80fde","index":0,"isStructMessage":false}

data: {"event":"task_terminated","data":{"node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","workflow_name":"ShengjinyouliAgent517_1_1_1","workflow_id":"875aeb56-1cd4-404c-9ef9-220c073f2e30","query":"升金感兴趣","intent_id":"ShengjinyouliAgent517_1_1_1","intent_name":"ShengjinyouliAgent517_1_1_1","time":1775874523102,"execution_id":"11fdd50a-dd8a-43de-934c-1b2661f80fde"},"createdTime":1775874523102,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775874523107,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775874523108,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775874523110,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"## 流程结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775874523111,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"## 流程结束","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c"},"createdTime":1775874523113,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"task_terminated","data":{"node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","workflow_name":"xxxstest_2","workflow_id":"8f9ac059-0b15-4b11-baf2-18d10665c38c","query":"升金感兴趣","intent_id":"xxxstest_2","intent_name":"xxxstest_2","time":1775874523113,"execution_id":"ea437b21-be2d-4dce-a25c-4b82662cda40"},"createdTime":1775874523113,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}

data: {"event":"task_end","data":{},"createdTime":1775874523114,"executionId":"ea437b21-be2d-4dce-a25c-4b82662cda40","index":0,"isStructMessage":false}
```