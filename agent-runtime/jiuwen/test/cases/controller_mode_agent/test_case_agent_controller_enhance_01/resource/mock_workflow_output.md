## 调用意图识别工作流的mock输出

意图识别工作流的workflow_id：966cbaa3-e693-4cd4-be18-44747329df9e

```text
StreamData(code=3000, msg=success, data={'workflow_id': '966cbaa3-e693-4cd4-be18-44747329df9e'}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '0', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=2,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '0', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'outputs': {'user_fields': {'intent_id': 0}}, 'enable_history': True}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='assistant', content='0', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '0', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '0', 'node_id': 'node_end', 'user_fields': {'intent_id': 0}, 'node_type': 'jiuwen.end'}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
```

## 调用智能外呼工作流的mock输出

智能外呼工作流workflow_id：5ffdcfdc-0afe-4e08-b8e8-c6206c01115e

```text
StreamData(code=3000, msg=success, data={'workflow_id': '5ffdcfdc-0afe-4e08-b8e8-c6206c01115e'}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': "本次来电是邀请您体验我行闲钱管理服务'大天盈'的。收益每日计算，1分起购，赎回最快实时到账，让您的闲钱不闲置，详情给您发条短信，您有空的时候了解下，可以吗", 'node_id': 'node_1743424323024', 'node_name': '产品介绍', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': "本次来电是邀请您体验我行闲钱管理服务'大天盈'的。收益每日计算，1分起购，赎回最快实时到账，让您的闲钱不闲置，详情给您发条短信，您有空的时候了解下，可以吗", 'node_id': 'node_1743424323024', 'node_name': '产品介绍', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='理财是什么', files=None, name=None, tool_call_id=None, function_call=[], intent=['RemoteBankingIntelligentOutboundCalling_subflow'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content="本次来电是邀请您体验我行闲钱管理服务'大天盈'的。收益每日计算，1分起购，赎回最快实时到账，让您的闲钱不闲置，详情给您发条短信，您有空的时候了解下，可以吗", files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '【理财】工作流执行结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '【理财】工作流执行结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='理财是什么', files=None, name=None, tool_call_id=None, function_call=[], intent=['RemoteBankingIntelligentOutboundCalling_subflow'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content="本次来电是邀请您体验我行闲钱管理服务'大天盈'的。收益每日计算，1分起购，赎回最快实时到账，让您的闲钱不闲置，详情给您发条短信，您有空的时候了解下，可以吗", files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='【理财】工作流执行结束', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '【理财】工作流执行结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '【理财】工作流执行结束', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=cae2c07b-2a13-4107-8c2b-d75e9af55b5f, is_struct_message=False)
```
