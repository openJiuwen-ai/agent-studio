## test_1中包含多轮请求交互，需要mock多次工作流调用

### 第一次请求：你好

#### 1. 调用开始工作流的mock输出

开始工作流的workflow_id：`START_WF_ID = "dfac616f-95d5-425a-aa52-e5432f24624a"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': 'dfac616f-95d5-425a-aa52-e5432f24624a'}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '您好，这里是银行，请问你是tom先生吗？', 'node_id': 'node_1747663017657', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '您好，这里是银行，请问你是tom先生吗？', 'node_id': 'node_1747663017657', 'node_name': '提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True, 'enable_history': True}, index=1,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='你好', files=None, name=None, tool_call_id=None, function_call=[], intent=['xxxtest_3_2_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='您好，这里是银行，请问你是tom先生吗？', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_1747663017657', 'user_fields': {'name': 'tom', 'continue': True, 'age': 25}, 'node_type': 'jiuwen.questioner'}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
```

---

### 第二次请求：是本人

#### 2. 再次调用开始工作流的mock输出

开始工作流的workflow_id：`START_WF_ID = "dfac616f-95d5-425a-aa52-e5432f24624a"`

```text
StreamData(code=1206, msg=success, data={'answer': '##开始工作流 continue：', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': 'True', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': ';age_temp: ', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=2,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '25', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=3,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '，age改为 10', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=4,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '##开始工作流 continue：True;age_temp: 25，age改为 10', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'outputs': {'user_fields': {'age': '10', 'continue': True}}, 'enable_history': True}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='你好', files=None, name=None, tool_call_id=None, function_call=[], intent=['xxxtest_3_2_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='您好，这里是银行，请问你是tom先生吗？', files=None, name=None, tool_call_id=None, function_call=[], intent=['xxxtest_3_2_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='是本人', files=None, name=None, tool_call_id=None, function_call=[], intent=['xxxtest_3_2_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##开始工作流 continue：True;age_temp: 25，age改为 10', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '##开始工作流 continue：True;age_temp: 25，age改为 10', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '##开始工作流 continue：True;age_temp: 25，age改为 10', 'node_id': 'node_end', 'user_fields': {'age': '10', 'continue': True}, 'node_type': 'jiuwen.end'}, index=0,execution_id=2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc, is_struct_message=False)
```

#### 3. 调用智能工作流的mock输出

智能工作流的workflow_id：`FIRST_WF_ID = "5710b24a-490f-419a-96d4-7eff0da204be"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '5710b24a-490f-419a-96d4-7eff0da204be'}, index=0,execution_id=3d29a10e-522c-4c74-a0cd-282160303328, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '#BDD#/本次致电，是邀请您体验我航”天天盈自动购买服务”,”天天盈”底层关联货币基金。您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。后续会有人工联系您介绍可以吗?', 'node_id': 'node_1747193680786', 'node_name': '开场白-提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True}, index=0,execution_id=3d29a10e-522c-4c74-a0cd-282160303328, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '#BDD#/本次致电，是邀请您体验我航”天天盈自动购买服务”,”天天盈”底层关联货币基金。您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。后续会有人工联系您介绍可以吗?', 'node_id': 'node_1747193680786', 'node_name': '开场白-提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True, 'enable_history': True}, index=1,execution_id=3d29a10e-522c-4c74-a0cd-282160303328, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='是本人', files=None, name=None, tool_call_id=None, function_call=[], intent=['xxxtest_3_2_1', 'tiantianyingAgent517_1_1_2'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='#BDD#/本次致电，是邀请您体验我航”天天盈自动购买服务”,”天天盈”底层关联货币基金。您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。后续会有人工联系您介绍可以吗?', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=3d29a10e-522c-4c74-a0cd-282160303328, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_1747193680786', 'user_fields': {}, 'node_type': 'jiuwen.questioner'}, index=0,execution_id=3d29a10e-522c-4c74-a0cd-282160303328, is_struct_message=False)
```

---

### 第三次请求：我要买升金

#### 4. 首次调用升金有礼工作流的mock输出

升金有礼工作流的workflow_id：`FINANCIAL_WF_ID = "875aeb56-1cd4-404c-9ef9-220c073f2e30"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '875aeb56-1cd4-404c-9ef9-220c073f2e30'}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出“升金有礼”积分回馈活动，即日起至', 'node_id': 'node_1747212048020', 'node_name': '开场白-首轮澄清', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '123', 'node_id': 'node_1747212048020', 'node_name': '开场白-首轮澄清', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=1,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？', 'node_id': 'node_1747212048020', 'node_name': '开场白-首轮澄清', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=2,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出“升金有礼”积分回馈活动，即日起至123，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？', 'node_id': 'node_1747212048020', 'node_name': '开场白-首轮澄清', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='我要买升金', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出“升金有礼”积分回馈活动，即日起至123，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '##', 'node_id': 'node_1747212899505', 'node_name': '开场白-提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '##', 'node_id': 'node_1747212899505', 'node_name': '开场白-提问器', 'node_type': 'jiuwen.questioner', 'should_interrupt': True, 'enable_history': True}, index=1,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='我要买升金', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='#BDD#/是这样的，为感谢您长久以来的支持与陪伴，我航推出“升金有礼”积分回馈活动，即日起至123，只要您报名参加，并且在我航的资产达到相应等级，即可抽取积分奖励，您可根据积分余额及相应条件兑换微信立减金、支付宝红包、话费等热门商品，我现在把活动短信发给您，好吗？', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '', 'node_id': 'node_1747212899505', 'user_fields': {}, 'node_type': 'jiuwen.questioner'}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
```

---

### 第四次请求：升金感兴趣

#### 5. 再次调用升金有礼工作流中断恢复后的mock输出

升金有礼工作流的workflow_id：`FINANCIAL_WF_ID = "875aeb56-1cd4-404c-9ef9-220c073f2e30"`

```text
StreamData(code=1206, msg=success, data={'answer': ' ##系统插件，发短信##', 'node_id': 'node_1747293876339', 'node_name': '发短息', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': ' ##系统插件，发短信##', 'node_id': 'node_1747293876339', 'node_name': '发短息', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='我要买升金', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='升金感兴趣', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content=' ##系统插件，发短信##', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！', 'node_id': 'node_1747293794534', 'node_name': '成功结束', 'node_type': 'jiuwen.message', 'should_interrupt': False}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！', 'node_id': 'node_1747293794534', 'node_name': '成功结束', 'node_type': 'jiuwen.message', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='我要买升金', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='升金感兴趣', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content=' ##系统插件，发短信##', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '##升金结束continue: ', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': 'False', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '。action_after_completion：', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=2,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': 'Terminal', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=3,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=4,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '##升金结束continue: False。action_after_completion：Terminal', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'outputs': {'user_fields': {'continue': False, 'action_after_completion': 'Terminal'}}, 'enable_history': True}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='我要买升金', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='user', content='升金感兴趣', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content=' ##系统插件，发短信##', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='#BDD#,#GD#/感谢您的支持，请留意查收95588短信并登录银行APP参与活动，祝您生活愉快，再见！', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='##升金结束continue: False。action_after_completion：Terminal', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '##升金结束continue: False。action_after_completion：Terminal', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '##升金结束continue: False。action_after_completion：Terminal', 'node_id': 'node_end', 'user_fields': {'continue': False, 'action_after_completion': 'Terminal'}, 'node_type': 'jiuwen.end'}, index=0,execution_id=11fdd50a-dd8a-43de-934c-1b2661f80fde, is_struct_message=False)
```

#### 6. 结束工作流的mock输出

结束工作流的workflow_id：`END_WF_ID = "8f9ac059-0b15-4b11-baf2-18d10665c38c"`

```text
StreamData(code=3000, msg=success, data={'workflow_id': '8f9ac059-0b15-4b11-baf2-18d10665c38c'}, index=0,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
StreamData(code=1206, msg=success, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=0,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
StreamData(code=5000, msg=message_end, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False, 'enable_history': True}, index=0,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
StreamData(code=7000, msg=intermediate message, data={'answer': [ConversationMessage(role='user', content='升金感兴趣', files=None, name=None, tool_call_id=None, function_call=[], intent=['ShengjinyouliAgent517_1_1_1', 'xxxstest_2'], enable_history=True, agent_id=None), ConversationMessage(role='assistant', content='## 流程结束', files=None, name=None, tool_call_id=None, function_call=None, intent=None, enable_history=True, agent_id=None)]}, index=0,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
StreamData(code=4000, msg=finish, data={'answer': '## 流程结束', 'node_id': 'node_end', 'node_name': '结束', 'node_type': 'jiuwen.end', 'should_interrupt': False}, index=1,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
StreamData(code=0, msg=finish, data={'answer': '## 流程结束', 'node_id': 'node_end', 'user_fields': {}, 'node_type': 'jiuwen.end'}, index=0,execution_id=ea437b21-be2d-4dce-a25c-4b82662cda40, is_struct_message=False)
```

---