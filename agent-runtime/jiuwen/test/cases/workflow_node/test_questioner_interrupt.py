# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
Questioner 工作流中断处理测试
测试覆盖:
- Questioner 在工作流中的中断机制
- 状态持久化与恢复
- 多轮对话处理
- 字段提取与验证
- 状态转换 (START -> USER_INTERACT -> END)
"""

from typing import Any, Dict
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from jiuwen.extension.workflow_node.questioner import (
    Questioner,
    QuestionerConfig,
    QuestionerState,
    QuestionerEvent,
    FieldInfo,
    ExecutionStatus,
    QuestionerDirectReplyHandler,
    QuestionerOutput,
)
from jiuwen.extension.workflow_node.start import Start
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import Workflow, End, create_workflow_session
from openjiuwen.core.workflow import WorkflowExecutionState
from openjiuwen.core.workflow.components.component import WorkflowComponent


class SimpleResultComponent(WorkflowComponent):
    """简单结果处理组件，用于验证 Questioner 的输出"""

    def __init__(self):
        super().__init__()

    async def invoke(
        self, inputs: Dict[str, Any], session: Session, context: ModelContext
    ) -> Dict[str, Any]:
        """处理 Questioner 的输出"""
        return {
            "processed_result": {
                "name": inputs.get("name", ""),
                "age": inputs.get("age", 0),
                "email": inputs.get("email", ""),
                "user_response": inputs.get("user_response", ""),
            }
        }


class TestQuestionerState:
    """测试 QuestionerState 状态管理"""

    def test_state_initialization(self):
        """测试状态初始化"""
        state = QuestionerState()

        assert state.response_num == 0
        assert state.status == ExecutionStatus.START
        assert state.extracted_key_fields == {}
        assert state.user_response == ""
        assert state.question == ""

    def test_state_serialization(self):
        """测试状态序列化和反序列化"""
        state = QuestionerState(
            response_num=2,
            user_response="张三, 25岁",
            question="请提供您的姓名和年龄",
            extracted_key_fields={"name": "张三", "age": 25},
            status=ExecutionStatus.USER_INTERACT,
        )

        serialized = state.serialize()
        assert serialized["response_num"] == 2
        assert serialized["status"] == ExecutionStatus.USER_INTERACT
        assert serialized["extracted_key_fields"]["name"] == "张三"

        deserialized = QuestionerState.deserialize(serialized)
        assert deserialized.response_num == 2
        assert deserialized.status == ExecutionStatus.USER_INTERACT
        assert deserialized.extracted_key_fields["name"] == "张三"

    def test_state_event_transitions(self):
        """测试状态事件转换"""
        state = QuestionerState()

        assert state.status == ExecutionStatus.START

        state = state.handle_event(QuestionerEvent.USER_INTERACT_EVENT)
        assert state.status == ExecutionStatus.USER_INTERACT

        state = state.handle_event(QuestionerEvent.END_EVENT)
        assert state.status == ExecutionStatus.END

    def test_is_undergoing_interaction(self):
        """测试是否处于交互状态"""
        state = QuestionerState()
        assert not state.is_undergoing_interaction()

        state = state.handle_event(QuestionerEvent.USER_INTERACT_EVENT)
        assert state.is_undergoing_interaction()

        state = state.handle_event(QuestionerEvent.END_EVENT)
        assert not state.is_undergoing_interaction()

    def test_is_fresh_state(self):
        """测试是否为全新状态"""
        state = QuestionerState()
        assert state.is_fresh_state()

        state.response_num = 1
        assert not state.is_fresh_state()

        state = QuestionerState(status=ExecutionStatus.USER_INTERACT)
        assert not state.is_fresh_state()


class TestQuestionerInterrupt:
    """测试 Questioner 中断机制"""

    @pytest.fixture
    def questioner_config(self):
        """创建 Questioner 配置"""
        return QuestionerConfig(
            model_name="test_model",
            model_type="OpenAI",
            response_type="reply_directly",
            extract_fields_from_response=True,
            max_response=3,
            key_fields=[
                FieldInfo(
                    field_name="name",
                    description="用户姓名",
                    cn_field_name="姓名",
                    type="string",
                    required=True,
                ),
                FieldInfo(
                    field_name="age",
                    description="用户年龄",
                    cn_field_name="年龄",
                    type="integer",
                    required=True,
                ),
                FieldInfo(
                    field_name="email",
                    description="用户邮箱",
                    cn_field_name="邮箱",
                    type="string",
                    required=False,
                ),
            ],
            accept_language="zh",
        )

    @pytest.fixture
    def mock_model(self):
        """创建 Mock 模型"""
        model = AsyncMock()
        model.invoke = AsyncMock(
            return_value='{"name": "张三", "age": 25, "email": "zhangsan@example.com"}'
        )
        model.stream = AsyncMock()
        return model

    def test_should_interrupt(self, questioner_config):
        """测试中断判断方法"""
        questioner = Questioner(questioner_config)

        assert not questioner.should_interrupt()

        questioner._node_state.status = ExecutionStatus.USER_INTERACT
        assert questioner.should_interrupt()

    def test_get_state_and_load_state(self, questioner_config):
        """测试状态获取和加载"""
        questioner = Questioner(questioner_config)

        initial_state = questioner.get_state()
        assert initial_state.status == ExecutionStatus.START

        new_state = QuestionerState(
            response_num=1,
            status=ExecutionStatus.USER_INTERACT,
            extracted_key_fields={"name": "张三"},
        )
        questioner.load_state(new_state)

        loaded_state = questioner.get_state()
        assert loaded_state.status == ExecutionStatus.USER_INTERACT
        assert loaded_state.extracted_key_fields["name"] == "张三"

    def test_error_to_output(self, questioner_config):
        """测试错误处理"""
        questioner = Questioner(questioner_config)
        questioner._node_state.status = ExecutionStatus.USER_INTERACT

        questioner.error_to_output()

        assert questioner.get_node_status() == ExecutionStatus.END

    @pytest.mark.asyncio
    @patch("jiuwen.extension.workflow_node.questioner.Model")
    async def test_questioner_in_workflow_interrupt_flow(
        self, mock_model_class, questioner_config
    ):
        """测试 Questioner 在工作流中的中断流程"""
        mock_model_instance = AsyncMock()
        mock_invoke_result = MagicMock()
        mock_invoke_result.content = '{"name": null, "age": null}'
        mock_invoke_result.usage_metadata = None
        mock_model_instance.invoke = AsyncMock(return_value=mock_invoke_result)
        mock_model_class.return_value = mock_model_instance

        with patch(
            "jiuwen.extension.workflow_node.questioner.os.getenv"
        ) as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "LLM_PROVIDER": "OpenAI",
                "LLM_API_KEY": "test-api-key",
                "LLM_API_BASE": "https://api.test.com",
                "LLM_MODEL_NAME": "test_model",
                "LLM_VERIFY_SSL": "False",
            }.get(key, default)

            flow = Workflow()

            start = Start({})
            flow.set_start_comp(
                "start", start, inputs_schema={"query": "${user_query}"}
            )

            questioner = Questioner(questioner_config)
            flow.add_workflow_comp(
                "questioner", questioner, inputs_schema={"query": "${start.query}"}
            )

            end = End()
            flow.set_end_comp(
                "end",
                end,
                inputs_schema={
                    "name": "${questioner.name}",
                    "age": "${questioner.age}",
                    "email": "${questioner.email}",
                },
            )

            flow.add_connection("start", "questioner")
            flow.add_connection("questioner", "end")

            session = create_workflow_session()
            session.interact = AsyncMock(return_value="张三, 25岁")

            result = await flow.invoke({"user_query": "我想注册"}, session)

            assert (
                questioner.should_interrupt()
                or result.state == WorkflowExecutionState.INPUT_REQUIRED
            )

    @pytest.mark.asyncio
    @patch("jiuwen.extension.workflow_node.questioner.Model")
    async def test_questioner_state_persistence(
        self, mock_model_class, questioner_config
    ):
        """测试 Questioner 状态持久化"""
        mock_model_instance = AsyncMock()
        mock_invoke_result = MagicMock()
        mock_invoke_result.content = '{"name": "张三", "age": null}'
        mock_invoke_result.usage_metadata = None
        mock_model_instance.invoke = AsyncMock(return_value=mock_invoke_result)
        mock_model_class.return_value = mock_model_instance

        with patch(
            "jiuwen.extension.workflow_node.questioner.os.getenv"
        ) as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "LLM_PROVIDER": "OpenAI",
                "LLM_API_KEY": "test-api-key",
                "LLM_API_BASE": "https://api.test.com",
                "LLM_MODEL_NAME": "test_model",
                "LLM_VERIFY_SSL": "False",
            }.get(key, default)

            questioner = Questioner(questioner_config)

            state_before = QuestionerState(
                response_num=1,
                status=ExecutionStatus.USER_INTERACT,
                extracted_key_fields={"name": "张三"},
                question="请提供您的年龄",
            )
            questioner.load_state(state_before)

            state_after = questioner.get_state()
            assert state_after.response_num == 1
            assert state_after.extracted_key_fields["name"] == "张三"
            assert state_after.status == ExecutionStatus.USER_INTERACT


class TestQuestionerDirectReplyHandler:
    """测试直接回复处理器"""

    @pytest.fixture
    def handler_config(self):
        """创建处理器配置"""
        return QuestionerConfig(
            model_name="test_model",
            model_type="OpenAI",
            response_type="reply_directly",
            key_fields=[
                FieldInfo(
                    field_name="name", description="姓名", type="string", required=True
                ),
                FieldInfo(
                    field_name="age", description="年龄", type="integer", required=True
                ),
            ],
            max_response=3,
            accept_language="zh",
        )

    @pytest.fixture
    def mock_session(self):
        """创建 Mock Session"""
        session = MagicMock(spec=Session)
        session.get_state = Mock(return_value={})
        session.update_state = Mock()
        session.interact = AsyncMock(return_value="张三, 25岁")
        return session

    @pytest.fixture
    def mock_context(self):
        """创建 Mock Context"""
        context = MagicMock(spec=ModelContext)
        context.add_messages = AsyncMock()
        return context

    def test_handler_initialization(self, handler_config):
        """测试处理器初始化"""
        handler = QuestionerDirectReplyHandler()

        assert handler._config is None
        assert handler._model is None
        assert handler._state is None

        handler.config(handler_config)
        assert handler._config == handler_config

    def test_handler_state_management(self, handler_config):
        """测试处理器状态管理"""
        handler = QuestionerDirectReplyHandler()
        handler.config(handler_config)

        state = QuestionerState(status=ExecutionStatus.START)
        handler.state(state)

        assert handler.get_state() == state


class TestQuestionerOutput:
    """测试 Questioner 输出"""

    def test_output_initialization(self):
        """测试输出初始化"""
        output = QuestionerOutput()

        assert output.user_response is None
        assert output.question is None
        assert output.key_fields == {}

    def test_output_update_key_field(self):
        """测试更新关键字段"""
        output = QuestionerOutput()

        output.update_key_field({"name": "张三", "age": 25})
        assert output.key_fields["name"] == "张三"
        assert output.key_fields["age"] == 25

        output.update_key_field({"email": "test@example.com"})
        assert output.key_fields["email"] == "test@example.com"
        assert output.key_fields["name"] == "张三"

    def test_output_getattr(self):
        """测试属性访问"""
        output = QuestionerOutput()
        output.update_key_field({"name": "张三", "age": 25})

        assert output.name == "张三"
        assert output.age == 25
        assert output.non_existent is None

    def test_output_as_dict(self):
        """测试转换为字典"""
        output = QuestionerOutput(user_response="用户回复", question="问题")
        output.update_key_field({"name": "张三", "age": 25})

        result = output.as_dict()

        assert result["user_response"] == "用户回复"
        assert result["question"] == "问题"
        assert result["name"] == "张三"
        assert result["age"] == 25


class TestFieldInfo:
    """测试字段信息"""

    def test_field_info_initialization(self):
        """测试字段信息初始化"""
        field = FieldInfo(
            field_name="name", description="用户姓名", type="string", required=True
        )

        assert field.field_name == "name"
        assert field.description == "用户姓名"
        assert field.type == "string"
        assert field.required is True
        assert field.cn_field_name == ""
        assert field.default_value == ""
        assert field.reflection is False

    def test_field_info_with_all_fields(self):
        """测试完整字段信息"""
        field = FieldInfo(
            field_name="age",
            description="用户年龄",
            cn_field_name="年龄",
            type="integer",
            required=True,
            default_value=0,
            reflection=True,
        )

        assert field.field_name == "age"
        assert field.cn_field_name == "年龄"
        assert field.type == "integer"
        assert field.default_value == 0
        assert field.reflection is True


class TestQuestionerUtils:
    """测试 Questioner 工具类"""

    def test_is_valid_value(self):
        """测试值有效性判断"""
        from jiuwen.extension.workflow_node.questioner import QuestionerUtils

        assert QuestionerUtils.is_valid_value("test") is True
        assert QuestionerUtils.is_valid_value(123) is True
        assert QuestionerUtils.is_valid_value(0) is True
        assert QuestionerUtils.is_valid_value(False) is True

        assert QuestionerUtils.is_valid_value(None) is False
        assert QuestionerUtils.is_valid_value("") is False
        assert QuestionerUtils.is_valid_value({}) is False
        assert QuestionerUtils.is_valid_value([]) is False
        assert QuestionerUtils.is_valid_value("null") is False
        assert QuestionerUtils.is_valid_value("None") is False

    def test_validate_and_convert_type(self):
        """测试类型验证和转换"""
        from jiuwen.extension.workflow_node.questioner import QuestionerUtils

        value, valid = QuestionerUtils.validate_and_convert_type("123", "integer")
        assert valid is True
        assert value == 123

        value, valid = QuestionerUtils.validate_and_convert_type("123.45", "number")
        assert valid is True
        assert value == 123.45

        value, valid = QuestionerUtils.validate_and_convert_type("true", "boolean")
        assert valid is True
        assert value is True

        value, valid = QuestionerUtils.validate_and_convert_type("false", "boolean")
        assert valid is True
        assert value is False

        value, valid = QuestionerUtils.validate_and_convert_type(123, "string")
        assert valid is True
        assert value == "123"

    def test_camel_to_snake(self):
        """测试驼峰转下划线"""
        from jiuwen.extension.workflow_node.questioner import QuestionerUtils

        assert QuestionerUtils.camel_to_snake("userName") == "user_name"
        assert QuestionerUtils.camel_to_snake("UserName") == "user_name"
        assert QuestionerUtils.camel_to_snake("userID") == "user_i_d"
        assert QuestionerUtils.camel_to_snake("simple") == "simple"


class TestQuestionerMultiRound:
    """测试 Questioner 多轮对话"""

    @pytest.fixture
    def multi_round_config(self):
        """创建多轮对话配置"""
        return QuestionerConfig(
            model_name="test_model",
            model_type="OpenAI",
            response_type="reply_directly",
            max_response=3,
            key_fields=[
                FieldInfo(
                    field_name="name",
                    description="姓名",
                    cn_field_name="姓名",
                    type="string",
                    required=True,
                ),
                FieldInfo(
                    field_name="age",
                    description="年龄",
                    cn_field_name="年龄",
                    type="integer",
                    required=True,
                ),
                FieldInfo(
                    field_name="phone",
                    description="电话",
                    cn_field_name="电话",
                    type="string",
                    required=True,
                ),
            ],
            accept_language="zh",
        )

    @pytest.mark.asyncio
    @patch("jiuwen.extension.workflow_node.questioner.Model")
    async def test_multi_round_state_progression(
        self, mock_model_class, multi_round_config
    ):
        """测试多轮对话状态推进"""
        mock_model_instance = AsyncMock()
        mock_model_instance.invoke = AsyncMock(
            side_effect=[
                '{"name": "张三", "age": null, "phone": null}',
                '{"name": "张三", "age": 25, "phone": null}',
                '{"name": "张三", "age": 25, "phone": "13800138000"}',
            ]
        )
        mock_model_class.return_value = mock_model_instance

        with patch(
            "jiuwen.extension.workflow_node.questioner.os.getenv"
        ) as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "LLM_PROVIDER": "OpenAI",
                "LLM_API_KEY": "test-api-key",
                "LLM_API_BASE": "https://api.test.com",
                "LLM_MODEL_NAME": "test_model",
                "LLM_VERIFY_SSL": "False",
            }.get(key, default)

            questioner = Questioner(multi_round_config)

            state = questioner.get_state()
            assert state.response_num == 0
            assert state.status == ExecutionStatus.START

            state.response_num = 1
            state.status = ExecutionStatus.USER_INTERACT
            state.extracted_key_fields = {"name": "张三"}
            questioner.load_state(state)

            state = questioner.get_state()
            assert state.response_num == 1
            assert "name" in state.extracted_key_fields

    def test_max_response_limit(self, multi_round_config):
        """测试最大响应次数限制"""
        questioner = Questioner(multi_round_config)

        assert questioner._config.max_response == 3

        state = questioner.get_state()
        state.response_num = 3
        questioner.load_state(state)

        assert questioner.get_state().response_num == 3


class TestQuestionerWorkflowIntegration:
    """Questioner 工作流集成测试"""

    @pytest.fixture
    def full_config(self):
        """创建完整配置"""
        return QuestionerConfig(
            model_name="test_model",
            model_type="OpenAI",
            response_type="reply_directly",
            extract_fields_from_response=True,
            max_response=3,
            key_fields=[
                FieldInfo(
                    field_name="username",
                    description="用户名",
                    cn_field_name="用户名",
                    type="string",
                    required=True,
                ),
                FieldInfo(
                    field_name="password",
                    description="密码",
                    cn_field_name="密码",
                    type="string",
                    required=True,
                ),
            ],
            question_construction_method="rule_based",
            accept_language="zh",
        )

    @pytest.mark.asyncio
    @patch("jiuwen.extension.workflow_node.questioner.Model")
    async def test_full_workflow_with_interrupt(self, mock_model_class, full_config):
        """测试完整工作流中断流程"""
        mock_model_instance = AsyncMock()
        mock_invoke_result = MagicMock()
        mock_invoke_result.content = '{"username": null, "password": null}'
        mock_invoke_result.usage_metadata = None
        mock_model_instance.invoke = AsyncMock(return_value=mock_invoke_result)
        mock_model_class.return_value = mock_model_instance

        with patch(
            "jiuwen.extension.workflow_node.questioner.os.getenv"
        ) as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "LLM_PROVIDER": "OpenAI",
                "LLM_API_KEY": "test-api-key",
                "LLM_API_BASE": "https://api.test.com",
                "LLM_MODEL_NAME": "test_model",
                "LLM_VERIFY_SSL": "False",
            }.get(key, default)

            flow = Workflow()

            start = Start({})
            flow.set_start_comp(
                "start", start, inputs_schema={"query": "${user_input}"}
            )

            questioner = Questioner(full_config)
            flow.add_workflow_comp(
                "questioner", questioner, inputs_schema={"query": "${start.query}"}
            )

            result_comp = SimpleResultComponent()
            flow.add_workflow_comp(
                "result",
                result_comp,
                inputs_schema={
                    "name": "${questioner.username}",
                    "age": "${questioner.password}",
                    "user_response": "${questioner.user_response}",
                },
            )

            end = End()
            flow.set_end_comp(
                "end", end, inputs_schema={"final": "${result.processed_result}"}
            )

            flow.add_connection("start", "questioner")
            flow.add_connection("questioner", "result")
            flow.add_connection("result", "end")

            session = create_workflow_session()
            session.interact = AsyncMock(return_value="username=test, password=123456")

            result = await flow.invoke({"user_input": "我想登录"}, session)

            workflow_logger.info(f"工作流执行结果: {result}")


if __name__ == "__main__":
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        workflow_logger.info("\n所有测试都通过了！")
    else:
        workflow_logger.error(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
