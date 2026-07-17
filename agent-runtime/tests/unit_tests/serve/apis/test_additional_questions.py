# tests/unit_tests/serve/apis/test_additional_questions.py
"""Additional questions schemas and service unit tests."""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from agent_runtime.additional_questions.conversation_reader import (
    ConversationReader,
)
from agent_runtime.additional_questions.model_invoker import (
    AdditionalQuestionsModelInvoker,
)
from agent_runtime.additional_questions.prompt_builder import (
    AdditionalQuestionsPromptBuilder,
)
from agent_runtime.additional_questions.service import (
    AdditionalQuestionsService,
)
from agent_runtime.schemas.additional_questions import (
    AdditionalQuestionsContext,
    AdditionalQuestionsRequest,
    AdditionalQuestionsResponse,
    AdditionalQuestionsModelConfig,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode


class TestAdditionalQuestionsRequest:
    """Request schema validation tests."""

    @staticmethod
    def test_valid_request_with_required_fields():
        req = AdditionalQuestionsRequest(name="my-agent")
        assert req.name == "my-agent"
        assert req.enable is True
        assert req.prompt == ""
        assert req.version_id == ""

    @staticmethod
    def test_valid_request_with_all_fields():
        req = AdditionalQuestionsRequest(
            name="my-agent",
            enable=False,
            prompt="custom prompt",
            version_id="v1",
        )
        assert req.name == "my-agent"
        assert req.enable is False
        assert req.prompt == "custom prompt"
        assert req.version_id == "v1"

    @staticmethod
    def test_name_is_required():
        with pytest.raises(ValidationError):
            AdditionalQuestionsRequest()

    @staticmethod
    def test_empty_name_fails():
        with pytest.raises(ValidationError):
            AdditionalQuestionsRequest(name="")

    @staticmethod
    def test_from_dict_with_aliases():
        req = AdditionalQuestionsRequest.model_validate({"name": "test", "enable": True})
        assert req.name == "test"


class TestAdditionalQuestionsResponse:
    """Response schema validation tests."""

    @staticmethod
    def test_default_questions_empty():
        resp = AdditionalQuestionsResponse()
        assert resp.questions == []

    @staticmethod
    def test_with_questions():
        resp = AdditionalQuestionsResponse(questions=["q1", "q2", "q3"])
        assert resp.questions == ["q1", "q2", "q3"]

    @staticmethod
    def test_serialization():
        resp = AdditionalQuestionsResponse(questions=["q1"])
        data = resp.model_dump()
        assert data == {"questions": ["q1"]}


class TestAdditionalQuestionsModelConfig:
    """Model config dataclass tests."""

    @staticmethod
    def test_creation():
        config = AdditionalQuestionsModelConfig(
            model_service_id="uuid-123",
            auth_id="auth-456",
        )
        assert config.model_service_id == "uuid-123"
        assert config.auth_id == "auth-456"

    @staticmethod
    def test_defaults():
        config = AdditionalQuestionsModelConfig(model_service_id="uuid")
        assert config.auth_id == ""


class TestAdditionalQuestionsPromptBuilder:
    """Prompt template rendering tests."""

    @pytest.fixture
    def builder(self):
        return AdditionalQuestionsPromptBuilder()

    @staticmethod
    def test_build_cn_template_contains_name(builder):
        result = builder.build(
            name="测试应用",
            history_messages="你好\n世界",
            user_prompt="",
            language="zh",
        )
        assert "测试应用" in result
        assert "你好\n世界" in result

    @staticmethod
    def test_build_en_template_contains_name(builder):
        result = builder.build(
            name="TestApp",
            history_messages="hello\nworld",
            user_prompt="",
            language="en",
        )
        assert "TestApp" in result
        assert "hello\nworld" in result

    @staticmethod
    def test_build_with_user_prompt(builder):
        result = builder.build(
            name="App",
            history_messages="msg",
            user_prompt="请生成与代码相关的问题",
            language="zh",
        )
        assert "请生成与代码相关的问题" in result

    @staticmethod
    def test_build_defaults_to_cn_when_language_is_zh(builder):
        result = builder.build(
            name="应用",
            history_messages="历史",
            user_prompt="",
            language="zh",
        )
        assert "追加问题" in result

    @staticmethod
    def test_build_en_template_has_english_keywords(builder):
        result = builder.build(
            name="App",
            history_messages="history",
            user_prompt="",
            language="en",
        )
        assert "additional questions" in result.lower()


class TestConversationReader:  # pylint: disable=protected-access
    """Redis conversation history reader tests."""

    @pytest.fixture
    def reader(self):
        return ConversationReader()

    @staticmethod
    def test_build_key_without_version(reader):
        key = reader.build_key(
            conversation_id="conv-1",
            resource_id="agent-1",
            version_id="",
            user_id="user-1",
        )
        assert key == "conv-1_agent-1_user-1"

    @staticmethod
    def test_build_key_with_version(reader):
        key = reader.build_key(
            conversation_id="conv-1",
            resource_id="agent-1",
            version_id="v2",
            user_id="user-1",
        )
        assert key == "conv-1_agent-1_user-1_v2"

    @pytest.mark.asyncio
    async def test_get_history_returns_sorted_messages(self, reader):
        conversation_data = {
            "messageList": [
                {"role": "user", "content": "hi", "createTime": 100},
                {"role": "assistant", "content": "hello", "createTime": 200},
                {"role": "user", "content": "how are you", "createTime": 300},
            ]
        }
        raw_bytes = json.dumps(conversation_data).encode("utf-8")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=raw_bytes)

        with patch(
            "agent_runtime.additional_questions.conversation_reader.get_redis_client",
            return_value=mock_redis,
        ), patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(user_id="user-1")
            messages = await reader.get_history("agent-1", "conv-1")

        assert len(messages) == 3
        assert messages[0]["content"] == "hi"
        assert messages[2]["content"] == "how are you"

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_when_key_not_found(self, reader):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch(
            "agent_runtime.additional_questions.conversation_reader.get_redis_client",
            return_value=mock_redis,
        ), patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(user_id="user-1")
            messages = await reader.get_history("agent-1", "conv-1")

        assert messages == []

    @pytest.mark.asyncio
    async def test_get_history_returns_empty_when_no_messagelist(self, reader):
        conversation_data = {}
        raw_bytes = json.dumps(conversation_data).encode("utf-8")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=raw_bytes)

        with patch(
            "agent_runtime.additional_questions.conversation_reader.get_redis_client",
            return_value=mock_redis,
        ), patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(user_id="user-1")
            messages = await reader.get_history("agent-1", "conv-1")

        assert messages == []

    @staticmethod
    def test_get_user_id_from_ctx_user_id(reader):
        """优先从 ctx.user_id 取。"""
        with patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(
                user_id="user-from-body", headers={}
            )
            assert reader._get_user_id() == "user-from-body"

    @staticmethod
    def test_get_user_id_from_x_user_id_header(reader):
        """ctx.user_id 为空时，从 x-user-id 请求头取。"""
        with patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(
                user_id="",
                headers={"x-user-id": "user-from-header"},
            )
            assert reader._get_user_id() == "user-from-header"

    @staticmethod
    def test_get_user_id_from_agent_sid_cookie(reader):
        """ctx.user_id 和 x-user-id 都为空时，从 AGENT_SID cookie 解析。"""
        with patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(
                user_id="",
                headers={},
            )
            mock_ctx.get.return_value.headers = {
                "Cookie": "AGENT_SID=testUser|0; other=value",
            }
            assert reader._get_user_id() == "testUser"

    @staticmethod
    def test_get_user_id_from_agent_sid_cookie_no_pipe(reader):
        """AGENT_SID cookie 没有 | 分隔符时，整体作为 userId。"""
        with patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(
                user_id="",
                headers={"Cookie": "AGENT_SID=simpleUser"},
            )
            assert reader._get_user_id() == "simpleUser"

    @staticmethod
    def test_get_user_id_returns_empty_when_no_source(reader):
        """所有来源都为空时返回空字符串。"""
        with patch(
            "agent_runtime.additional_questions.conversation_reader._request_ctx"
        ) as mock_ctx:
            mock_ctx.get.return_value = MagicMock(
                user_id="",
                headers={},
            )
            assert reader._get_user_id() == ""


class TestAdditionalQuestionsModelInvoker:
    """LLM model invocation tests."""

    @pytest.fixture
    def invoker(self):
        return AdditionalQuestionsModelInvoker()

    @pytest.fixture
    def model_config(self):
        return AdditionalQuestionsModelConfig(
            model_service_id="test-service-id",
            auth_id="test-auth-id",
        )

    @pytest.mark.asyncio
    async def test_invoke_returns_content(self, invoker, model_config):
        mock_result = MagicMock()
        mock_result.content = '["问题1？", "问题2？", "问题3？"]'

        with patch(
            "agent_runtime.additional_questions.model_invoker.Model"
        ) as mock_model, patch(
            "agent_runtime.additional_questions.model_invoker.ModelClientConfig"
        ), patch(
            "agent_runtime.additional_questions.model_invoker.ModelRequestConfig"
        ):
            instance = AsyncMock()
            instance.invoke = AsyncMock(return_value=mock_result)
            mock_model.return_value = instance

            result = await invoker.invoke(model_config, "test query", {})

        assert result == '["问题1？", "问题2？", "问题3？"]'
        instance.invoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invoke_raises_on_model_error(self, invoker, model_config):
        with patch(
            "agent_runtime.additional_questions.model_invoker.Model"
        ) as mock_model, patch(
            "agent_runtime.additional_questions.model_invoker.ModelClientConfig"
        ), patch(
            "agent_runtime.additional_questions.model_invoker.ModelRequestConfig"
        ):
            instance = AsyncMock()
            instance.invoke = AsyncMock(side_effect=RuntimeError("model error"))
            mock_model.return_value = instance

            with pytest.raises(RuntimeError, match="model error"):
                await invoker.invoke(model_config, "test query", {})


class TestAdditionalQuestionsService:  # pylint: disable=protected-access
    """Service orchestration tests — all collaborators mocked."""

    _DEFAULT_CTX = AdditionalQuestionsContext(
        resource_type="agent",
        resource_id="agent-1",
        project_id="proj-1",
        conversation_id="conv-1",
        workspace_id="ws-1",
    )

    @pytest.fixture
    def service(self):
        return AdditionalQuestionsService()

    @pytest.mark.asyncio
    async def test_generate_returns_questions(self, service):
        req = AdditionalQuestionsRequest(name="测试应用", enable=True)
        history = [
            {"role": "user", "content": "你好", "createTime": 100},
            {"role": "assistant", "content": "你好！有什么可以帮你的？", "createTime": 200},
        ]
        model_config = AdditionalQuestionsModelConfig(
            model_service_id="ms-id", auth_id="auth-id",
        )

        with patch.object(
            service.conversation_reader, "get_history", return_value=history
        ), patch.object(
            service, "_resolve_model_config", return_value=model_config
        ), patch.object(
            service.model_invoker,
            "invoke",
            return_value='["问题1？", "问题2？", "问题3？"]',
        ):
            result = await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

        assert result.questions == ["问题1？", "问题2？", "问题3？"]

    @pytest.mark.asyncio
    async def test_generate_returns_empty_when_history_too_short(self, service):
        req = AdditionalQuestionsRequest(name="测试应用", enable=True)
        history = [{"role": "user", "content": "hi", "createTime": 100}]

        with patch.object(
            service.conversation_reader, "get_history", return_value=history
        ):
            result = await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

        assert result.questions == []

    @pytest.mark.asyncio
    async def test_generate_raises_when_name_empty(self, service):
        req = AdditionalQuestionsRequest(name="test", enable=True)
        req.name = ""  # bypass Pydantic validation

        with pytest.raises(JiuWenBaseException) as exc_info:
            await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )
        assert exc_info.value.error_code == StatusCode.PARAM_CHECK_FAILED_ERROR.code

    @pytest.mark.asyncio
    async def test_generate_raises_when_enable_false(self, service):
        req = AdditionalQuestionsRequest(name="test", enable=True)
        req.enable = False

        with pytest.raises(JiuWenBaseException):
            await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

    @pytest.mark.asyncio
    async def test_generate_truncates_to_max_questions(self, service):
        req = AdditionalQuestionsRequest(name="测试应用", enable=True)
        history = [
            {"role": "user", "content": "hi", "createTime": 100},
            {"role": "assistant", "content": "hello", "createTime": 200},
        ]
        model_config = AdditionalQuestionsModelConfig(
            model_service_id="ms-id", auth_id="auth-id",
        )

        with patch.object(
            service.conversation_reader, "get_history", return_value=history
        ), patch.object(
            service, "_resolve_model_config", return_value=model_config
        ), patch.object(
            service.model_invoker,
            "invoke",
            return_value='["q1", "q2", "q3", "q4", "q5"]',
        ):
            result = await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

        assert len(result.questions) == 3
        assert result.questions == ["q1", "q2", "q3"]

    @pytest.mark.asyncio
    async def test_generate_returns_empty_on_llm_failure(self, service):
        req = AdditionalQuestionsRequest(name="测试应用", enable=True)
        history = [
            {"role": "user", "content": "hi", "createTime": 100},
            {"role": "assistant", "content": "hello", "createTime": 200},
        ]
        model_config = AdditionalQuestionsModelConfig(
            model_service_id="ms-id", auth_id="auth-id",
        )

        with patch.object(
            service.conversation_reader, "get_history", return_value=history
        ), patch.object(
            service, "_resolve_model_config", return_value=model_config
        ), patch.object(
            service.model_invoker,
            "invoke",
            side_effect=RuntimeError("model error"),
        ):
            result = await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

        assert result.questions == []

    @pytest.mark.asyncio
    async def test_generate_retries_on_empty_parse(self, service):
        req = AdditionalQuestionsRequest(name="测试应用", enable=True)
        history = [
            {"role": "user", "content": "hi", "createTime": 100},
            {"role": "assistant", "content": "hello", "createTime": 200},
        ]
        model_config = AdditionalQuestionsModelConfig(
            model_service_id="ms-id", auth_id="auth-id",
        )

        with patch.object(
            service.conversation_reader, "get_history", return_value=history
        ), patch.object(
            service, "_resolve_model_config", return_value=model_config
        ), patch.object(
            service.model_invoker,
            "invoke",
            side_effect=["not json", '["问题1？"]'],
        ):
            result = await service.generate(
                ctx=self._DEFAULT_CTX,
                request=req,
                headers={},
            )

        assert result.questions == ["问题1？"]

    @pytest.mark.asyncio
    async def test_resolve_model_config_agent(self, service):
        ir_data = {
            "configs": {
                "modelConfig": {
                    "modelName": "service-uuid",
                    "extension": {"authId": "auth-uuid"},
                }
            }
        }
        with patch.object(service, "_load_ir", return_value=ir_data):
            config = await service._resolve_model_config("agent", "agent-1", {})
        assert config.model_service_id == "service-uuid"
        assert config.auth_id == "auth-uuid"

    @pytest.mark.asyncio
    async def test_resolve_model_config_workflow(self, service):
        ir_data = {
            "configs": {
                "model": {
                    "modelName": "service-uuid",
                    "extension": {"authId": "auth-uuid"},
                }
            }
        }
        with patch.object(service, "_load_ir", return_value=ir_data):
            config = await service._resolve_model_config("workflow", "wf-1", {})
        assert config.model_service_id == "service-uuid"
        assert config.auth_id == "auth-uuid"

    @staticmethod
    def test_parse_response_valid_json_array(service):
        assert service._parse_response('["q1", "q2"]') == ["q1", "q2"]

    @staticmethod
    def test_parse_response_invalid_json(service):
        assert service._parse_response("not json") == []

    @staticmethod
    def test_parse_response_not_array(service):
        assert service._parse_response('{"key": "val"}') == []

    @staticmethod
    def test_parse_response_markdown_fenced(service):
        """LLM 返回 markdown 代码块包裹的 JSON 也能正确解析。"""
        content = '```json\n["问题1？", "问题2？"]\n```'
        assert service._parse_response(content) == ["问题1？", "问题2？"]

    @staticmethod
    def test_format_history(service):
        messages = [
            {"role": "user", "content": "你好", "createTime": 100},
            {"role": "assistant", "content": "你好！", "createTime": 200},
            {"role": "user", "content": "怎么样", "createTime": 300},
        ]
        result = service._format_history(messages)
        assert "你好！" in result
        assert "怎么样" in result


class TestAdditionalQuestionsAPIRoutes:
    """FastAPI route integration tests — TestClient against the app."""

    @staticmethod
    def _get_client():
        """Create a TestClient with just the execution_app router."""
        from fastapi import FastAPI
        from agent_runtime.serve.apis.orchestration import execution_app

        app = FastAPI()
        app.include_router(execution_app)
        return TestClient(app)

    def test_agent_route_returns_400_on_invalid_body(self):
        client = self._get_client()
        response = client.post(
            "/v1/proj-1/agents/agent-1/conversations/conv-1/additional-questions",
            params={"workspace_id": "ws-1"},
            json={"enable": True},  # missing required "name"
        )
        assert response.status_code == 400

    def test_workflow_route_returns_400_on_invalid_body(self):
        client = self._get_client()
        response = client.post(
            "/v1/proj-1/workflows/wf-1/conversations/conv-1/additional-questions",
            params={"workspace_id": "ws-1"},
            json={"enable": True},  # missing required "name"
        )
        assert response.status_code == 400

    def test_agent_route_returns_422_when_workspace_id_missing(self):
        client = self._get_client()
        response = client.post(
            "/v1/proj-1/agents/agent-1/conversations/conv-1/additional-questions",
            json={"name": "test", "enable": True},
        )
        assert response.status_code == 422

    def test_agent_route_accepts_valid_body(self):
        """Valid body should reach the service layer (mocked)."""
        client = self._get_client()
        mock_generate = AsyncMock(
            return_value=AdditionalQuestionsResponse(questions=["q1"]),
        )
        with patch.object(
            AdditionalQuestionsService, "generate", mock_generate,
        ):
            response = client.post(
                "/v1/proj-1/agents/agent-1/conversations/conv-1/additional-questions",
                params={"workspace_id": "ws-1"},
                json={"name": "test", "enable": True},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["questions"] == ["q1"]

    def test_workflow_route_accepts_valid_body(self):
        client = self._get_client()
        mock_generate = AsyncMock(
            return_value=AdditionalQuestionsResponse(questions=["q1", "q2"]),
        )
        with patch.object(
            AdditionalQuestionsService, "generate", mock_generate,
        ):
            response = client.post(
                "/v1/proj-1/workflows/wf-1/conversations/conv-1/additional-questions",
                params={"workspace_id": "ws-1"},
                json={"name": "test", "enable": True},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["questions"] == ["q1", "q2"]
