## 首次调用的流式输出数据帧

```text
data: {"event":"start","data":{},"createdTime":1775635360153,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"task_start","data":{},"createdTime":1775635360154,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"workflow_start","data":{"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635436623,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"关注到您近期有用款需求，我行融e借个人信用贷款...不知道您是否感兴趣？\n【谁说用户没有其他意图】","node_id":"node_1754443804332","node_name":"消息_1_1_1","node_type":"jiuwen.message","should_interrupt":false,"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635545667,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"关注到您近期有用款需求，我行融e借个人信用贷款...不知道您是否感兴趣？\n【谁说用户没有其他意图】","node_id":"node_1754443804332","node_name":"消息_1_1_1","node_type":"jiuwen.message","should_interrupt":false,"enable_history":true,"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635545671,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"message","data":{"answer":"ssq_融e借产品推荐_1--结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635545677,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"message_end","data":{"answer":"ssq_融e借产品推荐_1--结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"enable_history":true,"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635545679,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"workflow_end","data":{"answer":"ssq_融e借产品推荐_1--结束","node_id":"node_end","node_name":"结束","node_type":"jiuwen.end","should_interrupt":false,"workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635545685,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":1,"isStructMessage":false}

data: {"event":"done","data":{"answer":"ssq_融e借产品推荐_1--结束","node_id":"node_end","user_fields":{},"node_type":"jiuwen.end","workflow_id":"666aea41-bec1-47a9-af29-590f19bc01dd"},"createdTime":1775635563857,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}

data: {"event":"task_end","data":{},"createdTime":1775635585498,"executionId":"2ada2d97-6517-45cf-a26b-508fd61ee1c7","index":0,"isStructMessage":false}
```