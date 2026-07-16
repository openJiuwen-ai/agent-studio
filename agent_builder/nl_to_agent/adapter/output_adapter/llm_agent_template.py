# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


# LLM Agent模板
CLOUD_LLMAGENT_TEMPLATE = {
    "agent_id": "",
    "project_id": "5236296cb4c44cec867a42644ea6aa3a",
    "name": "",
    "type": "agent",
    "description": "",
    "instructions": "",
    "model_deployment_id": "180",
    "model_name": "DeepSeek-V3",
    "model_type": "LLM",
    "model_config": {
        "top_p": 1.0,
        "temperature": 0.0,
        "history_size": 20,
        "output_format": "text",
        "max_tokens": 4096,
        "frequency_penalty": 0.0,
    },
    "tools": [],
    "workflows": [],
    "mcp_servers": [],
    "knowledge_repos": [],
    "knowledge_retrieve_policy": {
        "search_mode": "doc",
        "top_k": 3,
        "recall_threshold": 0.1,
        "faq_threshold": 0.9,
    },
    "additional_questions_config": {
        "enable": True,
        "rounds": 1,
        "prompt": "- 问题应该与你最后一轮的回复紧密相关\n- 问题不要与上文已经提问或者回答过的内容重复\n- 每句话只包含一个问题，但也可以不是问句而是一句指令\n- 推荐你有能力回答的问题",
    },
    "voice_interaction": {
        "language": "chinese",
        "timbre": "huaxiaohe",
        "domain": "common",
    },
    "creator": "",
    "creator_id": "",
    "create_time": "",
    "update_time": "",
    "workflow_switch_enabled": False,
    "scheduling_mode": "ReAct",
}
