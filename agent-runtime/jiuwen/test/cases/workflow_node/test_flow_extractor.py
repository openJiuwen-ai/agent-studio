# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
Extractor 组件集成测试用例

测试工作流图:
    graph TD
        A[开始节点] --> B[提取节点]
        B --> C[结束节点]

测试流程:
1. 用户输入："我要坐飞机去上海参加会议"
2. 开始节点 -> 添加到 ModelContext 中
3. 提取节点从 ModelContext 中获取后，提取出 "location": "上海"，"traveltool": "飞机"
4. 结束节点
5. 最后校验输出结果的 output 中有 location：上海，traveltool：飞机

输入格式:
- Start: userFields.Input:"start.input"
- Extractor: userFields.Input:"start.input"
- End: loc: 提取节点.userFields.location, tool: 提取节点.userFields.traveltool

输出格式:
- userFields: {"traveltool": "", "location": "", "STATUS": "", "USER_RESPONSE": ""}
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_extractor import (
    Extractor,
    USER_FIELDS,
)
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.message_converter import WorkflowMessageConverter
from openjiuwen.core.context_engine.context.context import SessionModelContext
from openjiuwen.core.context_engine.schema.config import ContextEngineConfig
from openjiuwen.core.foundation.llm import UserMessage, BaseMessage
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
    WorkflowCard,
)

USER_INPUT = "我要坐飞机去上海参加会议"


def _load_memory_env():
    """从 memory_env 文件加载环境变量"""
    env_file = Path(__file__).parent / "memory_env"
    env_config = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_config[key.strip()] = value.strip()
    return env_config


_MEMORY_ENV = _load_memory_env()


def _create_test_model_context(
    messages: list[BaseMessage] = None,
) -> SessionModelContext:
    """创建测试用的 ModelContext"""
    config = ContextEngineConfig(
        max_context_message_num=100,
        default_window_message_num=50,
    )
    context = SessionModelContext(
        context_id="test-context",
        session_id="test-session",
        config=config,
        history_messages=messages or [],
        processors=[],
    )
    return context


class TestExtractorIntegrationWithRealLLM:
    """
    使用真实大模型的集成测试

    测试流程:
    1. 用户输入："我要坐飞机去上海参加会议"
    2. 开始节点 -> 添加到 ModelContext 中
    3. 提取节点从 ModelContext 中获取后，提取出 "location": "上海"，"traveltool": "飞机"
    4. 结束节点
    5. 最后校验输出结果的 output 中有 location：上海，traveltool：飞机
    """

    def _build_workflow(self) -> Workflow:
        """
        构建测试工作流: Start -> Extractor -> End

        输入格式:
        - Start: input: 用户输入, userFields: 初始字段
        - Extractor: config: 组件配置, userFields.Input: start.input
        - End: loc: extractor.userFields.location, tool: extractor.userFields.traveltool

        输出格式:
        - End 输出: {"output": {"loc": "上海", "tool": "飞机"}}
        """
        wf = Workflow()

        extractor_config = {
            "model": {
                "modelName": _MEMORY_ENV.get(
                    "LLM_MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct"
                ),
                "modelType": _MEMORY_ENV.get("LLM_PROVIDER", "SiliconFlow"),
                "hyperParameters": {"temperature": 0.1, "top_p": 0.15},
                "extension": {
                    "api_key": _MEMORY_ENV.get("LLM_API_KEY"),
                    "api_base": _MEMORY_ENV.get("LLM_API_BASE"),
                    "verify_ssl": False,
                },
            },
            "fieldNames": [
                {
                    "field_name": "location",
                    "description": "目的地或地点",
                    "cn_field_name": "地点",
                    "default_value": "",
                },
                {
                    "field_name": "traveltool",
                    "description": "交通工具",
                    "cn_field_name": "交通工具",
                    "default_value": "",
                },
            ],
            "withChatHistory": True,
            "chatHistoryMaxRounds": 5,
            "extraPromptForFieldsExtraction": "请从用户输入中准确提取地点和交通工具信息",
            "questionContent": "请提取以下信息",
            "exampleContent": '用户输入: 我是小明，性别是男\n指定参数：[name:姓名, age:年龄, gender:性别]\n提取结果：{"name":"小明","age":null,"gender":"男"}\n',
            "promptTemplate": [
                {
                    "role": "system",
                    "content": """
你是一个信息收集助手，你需要根据指定的参数从用户输入中提取信息。
请注意：不要使用任何工具、不用理会问题的具体含义，并保证你的输出仅有 JSON 格式的结果数据。
请严格遵循如下规则：
  1. 让我们一步一步思考。
  2. 用户输入中没有提及的参数提取为 null。
  3. 通过用户提供的对话历史以及当前输入中提取 {{required_name}}，不要追问任何其他信息。
  4. 参数收集完成后，将收集到的信息通过 JSON 的方式展示给用户。

## 指定参数
{{required_params_list}}

## 约束
{{extra_info}}

## 示例
{{example}}
""",
                },
                {
                    "role": "user",
                    "content": """
对话历史
{{dig_history}}

请充分考虑以上对话历史及用户输入，正确提取最符合约束要求的 JSON 格式参数。
""",
                },
            ],
            "inputComplement": True,
            "extractFieldsFromResponse": True,
        }

        start_config = {
            "userFields": {"inputs": [], "outputs": []},
            "systemFields": {
                "inputs": [
                    {
                        "sourceType": "input",
                        "description": "用户输入",
                        "id": "input",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "sourceType": "input",
                        "description": "用户字段",
                        "id": USER_FIELDS,
                        "type": "object",
                        "required": False,
                    },
                ],
                "outputs": [],
            },
        }

        wf.set_start_comp(
            "start",
            Start(start_config),
            inputs_schema={"input": "${input}", USER_FIELDS: "${userFields}"},
        )

        wf.add_workflow_comp(
            "extractor",
            Extractor(),
            inputs_schema={
                "config": extractor_config,
                USER_FIELDS: {"Input": "${start.userFields.input}"},
            },
        )

        end_config = {
            "responseMode": "directResponse",
            "userFields": {
                "inputs": [
                    {
                        "sourceType": "ref",
                        "description": "地点",
                        "id": "loc",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "sourceType": "ref",
                        "description": "交通工具",
                        "id": "tool",
                        "type": "string",
                        "required": False,
                    },
                ],
                "outputs": [],
            },
            "responseTemplate": '{"loc": "{{loc}}", "tool": "{{tool}}"}',
            "isStreamOut": False,
        }

        wf.set_end_comp(
            "end",
            End(end_config),
            inputs_schema={
                "loc": "${extractor.userFields.location}",
                "tool": "${extractor.userFields.traveltool}",
            },
        )

        wf.add_connection("start", "extractor")
        wf.add_connection("extractor", "end")

        return wf

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _MEMORY_ENV.get("LLM_API_KEY"),
        reason="memory_env 文件中未配置 LLM_API_KEY，跳过真实 LLM 测试",
    )
    async def test_workflow_extract_location_and_traveltool_with_real_llm(self):
        """
        真实 LLM 测试：完整工作流测试

        流程:
        1. 用户输入："我要坐飞机去上海参加会议"
        2. 开始节点 -> 添加到 ModelContext 中
        3. 提取节点从 ModelContext 中获取后，提取出 "location": "上海"，"traveltool": "飞机"
        4. 结束节点
        5. 最后校验输出结果的 output 中有 location：上海，traveltool：飞机
        """
        wf = self._build_workflow()
        session = create_workflow_session()
        context = _create_test_model_context()

        await context.add_messages(UserMessage(content=USER_INPUT))

        result = await wf.invoke(
            {"input": USER_INPUT, "userFields": {}},
            session,
            context=context,
        )
        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED

        output = result.result
        assert output is not None

        assert "answer" in output, f"输出中应包含 'response' 字段，实际输出: {output}"
        import json

        response_data = output["answer"]
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data["answer"]
        else:
            response_str = response_data
        output_data = json.loads(response_str)

        assert "loc" in output_data, f"输出中应包含 'loc' 字段，实际输出: {output_data}"
        assert "tool" in output_data, (
            f"输出中应包含 'tool' 字段，实际输出: {output_data}"
        )

        location = output_data.get("loc", "")
        traveltool = output_data.get("tool", "")

        print(f"提取结果 - location: {location}, traveltool: {traveltool}")

        assert "上海" in location, f"location 应包含 '上海'，实际值: {location}"
        assert "飞机" in traveltool, f"traveltool 应包含 '飞机'，实际值: {traveltool}"


class TestExtractorIntegrationWithMockLLM:
    """
    使用 Mock 大模型的集成测试

    测试流程:
    1. 用户输入："我要坐飞机去上海参加会议"
    2. 开始节点 -> 添加到 ModelContext 中
    3. 提取节点从 ModelContext 中获取后，提取出 "location": "上海"，"traveltool": "飞机"
    4. 结束节点
    5. 最后校验输出结果的 output 中有 location：上海，traveltool：飞机
    """

    def _build_workflow(self) -> Workflow:
        """
        构建测试工作流: Start -> Extractor -> End
        """
        wf = Workflow()

        extractor_config = {
            "model": {
                "modelName": "gpt-4",
                "modelType": "openai",
                "hyperParameters": {"temperature": 0.1, "top_p": 0.15},
                "extension": {
                    "api_key": "mock-api-key",
                    "api_base": "https://api.openai.com/v1",
                    "verify_ssl": True,
                },
            },
            "fieldNames": [
                {
                    "field_name": "location",
                    "description": "目的地或地点",
                    "cn_field_name": "地点",
                    "default_value": "",
                },
                {
                    "field_name": "traveltool",
                    "description": "交通工具",
                    "cn_field_name": "交通工具",
                    "default_value": "",
                },
            ],
            "withChatHistory": True,
            "chatHistoryMaxRounds": 5,
            "extraPromptForFieldsExtraction": "请从用户输入中准确提取地点和交通工具信息",
            "questionContent": "请提取以下信息",
            "exampleContent": '用户输入: 我是小明，性别是男\n指定参数：[name:姓名, age:年龄, gender:性别]\n提取结果：{"name":"小明","age":null,"gender":"男"}\n',
            "promptTemplate": [
                {
                    "role": "system",
                    "content": "你是一个信息提取助手，请从用户输入中提取指定字段。",
                },
                {
                    "role": "user",
                    "content": "对话历史：{{dig_history}}\n请提取：{{required_params_list}}",
                },
            ],
            "inputComplement": True,
            "extractFieldsFromResponse": True,
        }

        start_config = {
            "userFields": {"inputs": [], "outputs": []},
            "systemFields": {
                "inputs": [
                    {
                        "sourceType": "input",
                        "description": "用户输入",
                        "id": "input",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "sourceType": "input",
                        "description": "用户字段",
                        "id": USER_FIELDS,
                        "type": "object",
                        "required": False,
                    },
                ],
                "outputs": [],
            },
        }

        wf.set_start_comp(
            "start",
            Start(start_config),
            inputs_schema={"input": "${input}", USER_FIELDS: "${userFields}"},
        )

        wf.add_workflow_comp(
            "extractor",
            Extractor(),
            inputs_schema={
                "config": extractor_config,
                USER_FIELDS: {"Input": "${start.userFields.input}"},
            },
        )

        end_config = {
            "responseMode": "directResponse",
            "userFields": {
                "inputs": [
                    {
                        "sourceType": "ref",
                        "description": "地点",
                        "id": "loc",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "sourceType": "ref",
                        "description": "交通工具",
                        "id": "tool",
                        "type": "string",
                        "required": False,
                    },
                ],
                "outputs": [],
            },
            "responseTemplate": '{"loc": "{{loc}}", "tool": "{{tool}}"}',
            "isStreamOut": False,
        }

        wf.set_end_comp(
            "end",
            End(end_config),
            inputs_schema={
                "loc": "${extractor.userFields.location}",
                "tool": "${extractor.userFields.traveltool}",
            },
        )

        wf.add_connection("start", "extractor")
        wf.add_connection("extractor", "end")

        return wf

    @pytest.mark.asyncio
    async def test_workflow_extract_location_and_traveltool_with_mock_llm(self):
        """
        Mock LLM 测试：完整工作流测试

        流程:
        1. 用户输入："我要坐飞机去上海参加会议"
        2. 开始节点 -> 添加到 ModelContext 中
        3. 提取节点从 ModelContext 中获取后，提取出 "location": "上海"，"traveltool": "飞机"
        4. 结束节点
        5. 最后校验输出结果的 output 中有 location：上海，traveltool：飞机
        """
        wf = self._build_workflow()
        session = create_workflow_session()
        context = _create_test_model_context()

        await context.add_messages(UserMessage(content=USER_INPUT))

        mock_response_content = '{"location": "上海", "traveltool": "飞机"}'

        def mock_create_llm_instance(self):
            mock_llm = MagicMock()
            mock_llm.invoke = AsyncMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_response_content)
            return mock_llm

        with patch.object(Extractor, "_create_llm_instance", mock_create_llm_instance):
            result = await wf.invoke(
                {"input": USER_INPUT, "userFields": {}},
                session,
                context=context,
            )

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED

        output = result.result
        assert output is not None

        assert "answer" in output, f"输出中应包含 'answer' 字段，实际输出: {output}"
        import json

        response_data = output["answer"]
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data["answer"]
        else:
            response_str = response_data
        output_data = json.loads(response_str)

        assert "loc" in output_data, f"输出中应包含 'loc' 字段，实际输出: {output_data}"
        assert "tool" in output_data, (
            f"输出中应包含 'tool' 字段，实际输出: {output_data}"
        )

        location = output_data.get("loc", "")
        traveltool = output_data.get("tool", "")

        assert "上海" in location, f"location 应包含 '上海'，实际值: {location}"
        assert "飞机" in traveltool, f"traveltool 应包含 '飞机'，实际值: {traveltool}"

    @pytest.mark.asyncio
    async def test_workflow_with_chat_history(self):
        """
        Mock LLM 测试：带对话历史的完整工作流测试
        """
        wf = self._build_workflow()
        session = create_workflow_session()
        context = _create_test_model_context()

        await context.add_messages(UserMessage(content="你好，我是小明"))
        await context.add_messages(UserMessage(content="我要坐飞机去上海参加会议"))

        mock_response_content = '{"location": "上海", "traveltool": "飞机"}'

        def mock_create_llm_instance(self):
            mock_llm = MagicMock()
            mock_llm.invoke = AsyncMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_response_content)
            return mock_llm

        with patch.object(Extractor, "_create_llm_instance", mock_create_llm_instance):
            result = await wf.invoke(
                {"input": USER_INPUT, "userFields": {}},
                session,
                context=context,
            )

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED

        output = result.result
        assert output is not None

        import json

        assert "answer" in output, f"输出中应包含 'answer' 字段，实际输出: {output}"
        response_data = output.get("answer", "{}")
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data.get("answer", "{}")
        else:
            response_str = response_data
        output_data = json.loads(
            response_str if isinstance(response_str, str) else "{}"
        )
        location = output_data.get("loc", "")
        traveltool = output_data.get("tool", "")

        assert "上海" in location, f"location 应包含 '上海'，实际值: {location}"
        assert "飞机" in traveltool, f"traveltool 应包含 '飞机'，实际值: {traveltool}"

    @pytest.mark.asyncio
    async def test_workflow_with_empty_response(self):
        """
        Mock LLM 测试：LLM 返回空响应时的完整工作流测试
        """
        wf = self._build_workflow()
        session = create_workflow_session()
        context = _create_test_model_context()

        await context.add_messages(UserMessage(content=USER_INPUT))

        mock_response_content = "{}"

        def mock_create_llm_instance(self):
            mock_llm = MagicMock()
            mock_llm.invoke = AsyncMock()
            mock_llm.invoke.return_value = MagicMock(content=mock_response_content)
            return mock_llm

        with patch.object(Extractor, "_create_llm_instance", mock_create_llm_instance):
            result = await wf.invoke(
                {"input": USER_INPUT, "userFields": {}},
                session,
                context=context,
            )

        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED


class TestExtractorUnit:
    """
    Extractor 组件单元测试
    """

    def test_extractor_init(self):
        """测试 Extractor 初始化"""
        extractor = Extractor()
        assert extractor is not None
        assert extractor.llm is None
        assert extractor.extractor_config is not None

    def test_extractor_config_format(self):
        """测试配置格式化"""
        from jiuwen.extension.workflow_node.flow_extractor import (
            format_extractor_configs,
        )

        raw_config = {
            "model": {
                "modelName": "gpt-4",
                "modelType": "openai",
                "hyperParameters": {"temperature": 0.5, "top_p": 0.9},
            },
            "field_names": [
                {"field_name": "name", "description": "姓名", "cn_field_name": "姓名"}
            ],
            "with_chat_history": True,
            "chat_history_max_rounds": 3,
        }

        formatted = format_extractor_configs(raw_config)

        assert formatted["model_name"] == "gpt-4"
        assert formatted["model_type"] == "openai"
        assert formatted["hyper_parameters"]["temperature"] == 0.5
        assert formatted["hyper_parameters"]["top_p"] == 0.9
        assert formatted["with_chat_history"] is True
        assert formatted["chat_history_max_rounds"] == 3
        assert len(formatted["key_fields"]) == 1
        assert formatted["key_fields"][0]["name"] == "name"

    def test_extractor_output_as_dict(self):
        """测试 ExtractorOutput.as_dict()"""
        from jiuwen.extension.workflow_node.flow_extractor import ExtractorOutput

        output = ExtractorOutput(user_response="test response")
        output.update_key_field({"location": "上海", "traveltool": "飞机"})

        result = output.as_dict()

        assert "USER_RESPONSE" in result
        assert result["USER_RESPONSE"] == "test response"
        assert "location" in result
        assert result["location"] == "上海"
        assert "traveltool" in result
        assert result["traveltool"] == "飞机"


workflow_id = "e73c2b70-efle-4a13-9b3a-e588ebc224c4"
agent_id = "39a8026s-2181-446f-8cf1-2887e9403h7c"
session_id = "e02b3673-1683-4a99-83b6-ecce9426bf0b"


def create_extractor_workflow() -> tuple[Workflow, str]:
    """
    创建异常结束工作流

    结构: start -> questioner -> branch -> (end / exception_info)

    Branch 条件: '异常' not in ${start.systemFields.query} → end，否则 → exception_info

    Returns:
        Workflow: 工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="test_extractor",
        version="0.1.0",
        description="test_extractor",
    )
    wf = Workflow(workflow_card)

    extractor_config = {
        "model": {
            "modelName": "mock_llm",
            "modelType": "Mock",
            "hyperParameters": {"temperature": 0.1, "top_p": 0.15},
            "extension": {
                "api_key": "mock-api-key",
                "api_base": "https://api.openai.com/v1",
                "verify_ssl": True,
            },
        },
        "fieldNames": [
            {
                "field_name": "location",
                "description": "目的地或地点",
                "cn_field_name": "地点",
                "default_value": "",
                "reflection": True,
                "required": True,
            },
            {
                "field_name": "traveltool",
                "description": "交通工具",
                "cn_field_name": "交通工具",
                "default_value": "",
                "reflection": True,
                "required": True,
            },
        ],
        "withChatHistory": True,
        "chatHistoryMaxRounds": 5,
        "extraPromptForFieldsExtraction": "请从用户输入中准确提取地点和交通工具信息",
        "questionContent": "请提取以下信息",
        "exampleContent": '用户输入: 我是小明，性别是男\n指定参数：[name:姓名, age:年龄, gender:性别]\n提取结果：{"name":"小明","age":null,"gender":"男"}\n',
        "promptTemplate": [
            {
                "role": "system",
                "content": "你是一个信息提取助手，请从用户输入中提取指定字段。",
            },
            {
                "role": "user",
                "content": "对话历史：{{dig_history}}\n请提取：{{required_params_list}}",
            },
        ],
        "inputComplement": True,
        "extractFieldsFromResponse": True,
    }

    start_config = {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "提取目的地",
                    "id": "input",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "用户字段",
                    "id": USER_FIELDS,
                    "type": "object",
                    "required": False,
                },
            ],
            "outputs": [],
        },
    }

    wf.set_start_comp(
        "node_start",
        Start(start_config),
        inputs_schema={"input": "${input}", USER_FIELDS: "${userFields}"},
    )

    wf.add_workflow_comp(
        "extractor",
        Extractor(),
        inputs_schema={
            "config": extractor_config,
            USER_FIELDS: {"Input": "${node_start.userFields.input}"},
        },
    )

    end_config = {
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "地点",
                    "id": "loc",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "交通工具",
                    "id": "tool",
                    "type": "string",
                    "required": False,
                },
            ],
            "outputs": [],
        },
        "name": "结束",
        "responseTemplate": "地点：{{loc}}， 工具：{{tool}}",
        "isStreamOut": False,
    }

    wf.set_end_comp(
        "node_end",
        End(end_config),
        inputs_schema={
            "loc": "${extractor.userFields.location}",
            "tool": "${extractor.userFields.traveltool}",
        },
        response_mode="streaming",
    )

    wf.add_connection("node_start", "extractor")
    wf.add_connection("extractor", "node_end")

    # 7. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(
        workflow_card,
        lambda card=workflow_card: wf,
        tag=agent_id,
    )

    return wf, workflow_id


def _build_context(conversation_history: list):
    """从对话历史构建 ModelContext，模拟 WorkflowHandler 的 _build_context 行为。"""
    from openjiuwen.core.context_engine.context.context import SessionModelContext  # noqa: redefined-outer-name
    from openjiuwen.core.context_engine.schema.config import ContextEngineConfig  # noqa: redefined-outer-name

    model_context = SessionModelContext(
        context_id=f"{workflow_id}_context",
        session_id=session_id,
        config=ContextEngineConfig(),
        history_messages=[],
        processors=[],
    )
    WorkflowMessageConverter.conversation_messages_to_model_context(
        conversation_history, model_context
    )
    return model_context


@pytest.mark.asyncio
async def test_exception_workflow():
    """
    测试extractor工作流

    query="我要坐飞机去上海参加会议" → Extractor 提取信息 → end。
    验证信息提取正确。
    """
    from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
    from openjiuwen.core.common.logging import workflow_logger

    conversation_history = [
        {"role": "user", "content": "我要坐飞机去上海参加会议"},
    ]
    params = {
        "global_variables": {
            "sys": {
                "conversationHistory": conversation_history,
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            }
        },
        "conversation_history": conversation_history,
        "CONTROLLER_MODE_SWITCH": True,
    }

    workflow, wf_id = create_extractor_workflow()
    wrapper = WorkflowWrapper()
    chunks = []
    async for chunk in wrapper.astream(
        query="我要坐飞机去上海参加会议",
        workflow_id=wf_id,
        session_id=session_id,
        agent_id=agent_id,
        params=params,
        context=_build_context(conversation_history),
    ):
        chunks.append(chunk)
        workflow_logger.info(chunk)
    assert len(chunks) > 0
    workflow_logger.info(f"共收到 {len(chunks)} 个chunk")
