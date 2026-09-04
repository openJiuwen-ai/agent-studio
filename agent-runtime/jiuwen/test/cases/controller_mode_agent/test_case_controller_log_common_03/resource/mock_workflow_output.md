## test_1：调用开始工作流的mock输出

开始工作流的workflow_id：`START_WF_ID = "dfac616f-95d5-425a-aa52-e5432f24624a"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': 'dfac616f-95d5-425a-aa52-e5432f24624a'}, index=0,execution_id=9472bb80-5ec9-4d2c-8c77-fe5806e0821a, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '您好，这里是银行，请问你是tom先生吗？', 'node_id': 'node_1747663017657', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True}, index=0,execution_id=9472bb80-5ec9-4d2c-8c77-fe5806e0821a, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '您好，这里是银行，请问你是tom先生吗？', 'node_id': 'node_1747663017657', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True, 'enable_history': True}, index=1,execution_id=9472bb80-5ec9-4d2c-8c77-fe5806e0821a, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='你好', files=None, name=None, tool_call_id=None, function_call=[], intent=['开始工作流'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='您好，这里是银行，请问你是tom先生吗？', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=9472bb80-5ec9-4d2c-8c77-fe5806e0821a, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_1747663017657', 'user_fields': {'name': 'tom', 'continue': True, 'age': 25}, 'node_type': 'jiuwen.questioner'}, index=0,execution_id=9472bb80-5ec9-4d2c-8c77-fe5806e0821a, is_struct_message=False)
```

## test_2：调用利率是多少工作流和结束工作流的mock输出

利率是多少工作流workflow_id：`INTEREST_QUERY_WF_ID = "aacb7592-31ff-4741-a079-cfc187cabff8"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': 'aacb7592-31ff-4741-a079-cfc187cabff8'}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '低至 3.35%', 'node_id': 'node_1747039591166', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '低至 3.35%', 'node_id': 'node_1747039591166', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='开始跳', files=None, name=None, tool_call_id=None, function_call=[], intent=['利率是多少', 'faq_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='低至 3.35%', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='开始跳', files=None, name=None, tool_call_id=None, function_call=[], intent=['利率是多少', 'faq_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='低至 3.35%', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=4000, msg=, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
```

结束工作流workflow_id：`END_WF_ID = "8f9ac059-0b15-4b11-baf2-18d10665c38c"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '8f9ac059-0b15-4b11-baf2-18d10665c38c'}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='开始跳', files=None, name=None, tool_call_id=None, function_call=[], intent=['利率是多少', 'faq_1', '结束工作流'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='## 流程结束', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '## 流程结束', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=762bb089-435c-49a7-97b4-64f03c21fa34, is_struct_message=False)
```
