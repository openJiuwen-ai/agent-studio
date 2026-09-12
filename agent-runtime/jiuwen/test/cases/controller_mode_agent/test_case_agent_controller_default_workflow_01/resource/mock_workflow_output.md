## test_1：调用WaitUserInput配置的理财工作流的mock输出

理财工作流的workflow_id：`FINANCIAL_WF_ID = "83a951bc-27d7-4ccc-9131-268e93267365"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '83a951bc-27d7-4ccc-9131-268e93267365'}, index=0,execution_id=c6afe397-4acf-459d-b3cc-1696e35cc082, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？', 'node_id': 'node_1747116170373', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True}, index=0,execution_id=c6afe397-4acf-459d-b3cc-1696e35cc082, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？', 'node_id': 'node_1747116170373', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True, 'enable_history': True}, index=1,execution_id=c6afe397-4acf-459d-b3cc-1696e35cc082, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='给我推荐一个理财产品', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHFinanceProductSelect0607_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='您好，为了更好的为您推荐合适的理财产品，我需要了解一些信息。请问您对理财产品有什么要求，如理财风险等级，投资币种，收益率等？', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=c6afe397-4acf-459d-b3cc-1696e35cc082, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_1747116170373', 'user_fields': {}, 'node_type': 'jiuwen.questioner'}, index=0,execution_id=c6afe397-4acf-459d-b3cc-1696e35cc082, is_struct_message=False)
```

## test_2：调用默认工作流和结束工作流的mock输出

默认工作流的workflow_id：`DEFAULT_WF_ID = "ef802b42-9f76-4fb3-bfbb-910e5c091ced"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': 'ef802b42-9f76-4fb3-bfbb-910e5c091ced'}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '', 'node_id': 'node_1753769873590', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '珠穆朗玛峰', 'node_id': 'node_1753769873590', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=1,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '', 'node_id': 'node_1753769873590', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=2,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '珠穆朗玛峰', 'node_id': 'node_1753769873590', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='什么是理财', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2', 'YHFinanceProductSelect0607_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='世界上最高的山', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='珠穆朗玛峰', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='什么是理财', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2', 'YHFinanceProductSelect0607_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='世界上最高的山', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='珠穆朗玛峰', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=4000, msg=, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
```

结束工作流的workflow_id：`END_WF_ID = "6bcb3df8-0f29-41fd-a583-273414629b67"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '6bcb3df8-0f29-41fd-a583-273414629b67'}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '结束工作流', 'node_id': 'node_1748098633016', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '结束工作流', 'node_id': 'node_1748098633016', 'node_name': '消息', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='世界上最高的山', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2', 'xxxtest_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='结束工作流', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='世界上最高的山', files=None, name=None, tool_call_id=None, function_call=[], intent=['YHQAWorkFlow_2', 'xxxtest_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='结束工作流', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=4000, msg=, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=23915260-4b6d-4a94-b448-02bbfd37224e, is_struct_message=False)
```
