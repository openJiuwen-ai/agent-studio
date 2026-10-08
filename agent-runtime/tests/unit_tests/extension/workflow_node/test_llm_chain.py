# tests/unit_tests/extension/workflow_node/test_llm_chain.py
# pylint: disable=protected-access  # 单测需直接调用内部方法 _process_thinking_stream 等

from unittest.mock import MagicMock

import pytest
from jiuwen.extension.workflow_node.llm_chain import LLMChain
from openjiuwen.core.common.exception.errors import BaseError


def _make_llm_chain_conf(
    thinking_type="enabled",
    template_content=None,
    history_size=None,
):
    """构造最小 LLMChain 配置 dict"""
    conf = {
        "model": {
            "modelName": "test-model",
            "modelType": "LLM",
            "hyperParameters": {"thinking": {"type": thinking_type}},
            "extension": {
                "deploymentId": "deploy-1",
                "authId": "auth-1",
                "safetyBarrier": False,
            },
        },
        "deployMode": "workflow",
        "templateContent": template_content
        or [{"content": "{{query}}", "role": "user"}],
        "responseFormat": {"type": "text"},
        "userFields": {
            "inputs": [
                {"sourceType": "ref", "id": "query", "type": "string", "required": True}
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "id": "raw_output",
                    "type": "string",
                    "required": True,
                }
            ],
        },
        "stream": True,
        "enableHistory": False,
        "memory": {"enable": False},
        "historySize": history_size if history_size is not None else 3,
        "vision": [],
    }
    return conf


class TestLLMChainThinkingStreamErrorPropagation:
    """验证 thinking stream 路径中 LLM 异常能正确向上传播"""

    @pytest.mark.asyncio
    async def test_process_thinking_stream_raises_on_llm_error(self):
        """当 LLM stream 抛出 BadRequestError 时，_process_thinking_stream 应抛出 JiuWenBaseException"""

        conf = _make_llm_chain_conf(thinking_type="enabled")

        # 构造一个会抛异常的 async generator
        async def failing_stream(**kwargs):
            raise Exception("模型接入URL无效")

        chain = LLMChain(conf=conf)
        chain._llm = MagicMock()
        chain._llm.stream = MagicMock(return_value=failing_stream())
        chain._session = None
        chain._context = None

        with pytest.raises(BaseError, match="LLM stream failed"):
            await chain._process_thinking_stream(
                chain._llm.stream(messages=[]),
                {},
            )

    @pytest.mark.asyncio
    async def test_stream_method_raises_on_thinking_llm_error(self):
        """当 thinking 模式下 LLM stream 抛异常时，stream() 方法应抛出 JiuWenBaseException"""

        conf = _make_llm_chain_conf(thinking_type="enabled")

        async def failing_stream(**kwargs):
            raise Exception("模型接入URL无效")

        chain = LLMChain(conf=conf)
        # 跳过 _initialize_if_needed
        chain._initialized = True
        chain._llm = MagicMock()
        chain._llm.stream = MagicMock(return_value=failing_stream())
        chain._session = None
        chain._context = None
        chain._stream_final_output = None
        session = MagicMock()

        with pytest.raises(BaseError, match="LLM stream failed"):
            async for _ in chain.stream(
                inputs={"userFields": {"query": "你好"}}, session=session, context=None
            ):
                pass


class TestLLMChainThinkingStreamHappyPath:
    """验证 thinking stream 正常工作时的行为"""

    @pytest.mark.asyncio
    async def test_process_thinking_stream_returns_generator_on_success(self):
        """当 LLM stream 正常返回时，_process_thinking_stream 应返回 (generator, reasoning_content)"""
        conf = _make_llm_chain_conf(thinking_type="enabled")

        # 构造正常的 async generator — 返回带 content 的 chunk
        mock_chunk = MagicMock()
        mock_chunk.content = "你好世界"
        mock_chunk.reasoning_content = "思考中..."

        async def successful_stream(**kwargs):
            yield mock_chunk

        chain = LLMChain(conf=conf)
        chain._llm = MagicMock()
        chain._llm.stream = MagicMock(return_value=successful_stream())
        chain._session = None
        chain._context = None

        gen, reasoning_content, _ = await chain._process_thinking_stream(
            chain._llm.stream(messages=[]),
            {},
        )

        # reasoning_content 应被收集
        assert reasoning_content == "思考中..."

        # generator 应能产出内容
        chunks = []
        async for chunk_data in gen:
            chunks.append(chunk_data)
        assert len(chunks) > 0
        assert "raw_output" in chunks[0]


class TestNormalizeTemplatePlaceholders:
    """验证模板占位符空白归一化"""

    def test_no_whitespace(self):
        assert LLMChain._normalize_template_placeholders("{{query}}") == "{{query}}"

    def test_leading_trailing_whitespace(self):
        assert LLMChain._normalize_template_placeholders("{{ query }}") == "{{query}}"

    def test_excessive_whitespace(self):
        assert (
            LLMChain._normalize_template_placeholders("{{ query            }}")
            == "{{query}}"
        )

    def test_multiple_placeholders(self):
        assert (
            LLMChain._normalize_template_placeholders("{{ query }} and {{ context }}")
            == "{{query}} and {{context}}"
        )

    def test_mixed_whitespace_and_clean(self):
        assert (
            LLMChain._normalize_template_placeholders("{{query}} {{ name }}")
            == "{{query}} {{name}}"
        )

    def test_no_placeholders(self):
        assert LLMChain._normalize_template_placeholders("hello world") == "hello world"

    def test_dot_notation_preserved(self):
        assert (
            LLMChain._normalize_template_placeholders("{{ query.name }}")
            == "{{query.name}}"
        )


class TestGetHistory:
    """验证 _get_history / _get_chat_history / _process_inputs 在 enableHistory 开启时
    正确构建对话历史，不丢失最近一条 assistant 回复。

    根因: 原逻辑用 chat_history[:-1] 去掉"最后一条当前用户消息"，
    但 context.get_messages() 返回的 conversationHistory 不包含当前轮次
    的用户消息（query 通过 inputs → 模板渲染提供），导致 [:-1] 错误地
    去掉了最近一条 assistant 回复。修复后不再做 [:-1] 去尾。
    """

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_chain(enable_history=True, history_size=None):
        conf = _make_llm_chain_conf(history_size=history_size)
        conf["enableHistory"] = enable_history
        return LLMChain(conf=conf)

    @staticmethod
    def _mock_context(msg_list):
        """构造 mock context，get_messages(with_history=True) 返回 msg_list"""
        ctx = MagicMock()
        ctx.get_messages = MagicMock(return_value=msg_list)
        return ctx

    # ── _message_to_dict ─────────────────────────────────────────────

    @staticmethod
    def test_message_to_dict_user_message():
        """UserMessage(role=user) 应映射为 role=user"""
        from openjiuwen.core.foundation.llm import UserMessage
        msg = UserMessage(content="hello")
        result = LLMChain._message_to_dict(msg)
        assert result == {"role": "user", "content": "hello"}

    @staticmethod
    def test_message_to_dict_assistant_message():
        """AssistantMessage(role=assistant) 应映射为 role=assistant"""
        from openjiuwen.core.foundation.llm import AssistantMessage
        msg = AssistantMessage(content="hi there")
        result = LLMChain._message_to_dict(msg)
        assert result == {"role": "assistant", "content": "hi there"}

    @staticmethod
    def test_message_to_dict_dict_passthrough():
        """dict 直接透传"""
        d = {"role": "user", "content": "test"}
        assert LLMChain._message_to_dict(d) == d

    @staticmethod
    def test_message_to_dict_unknown_type_fallback():
        """type 不在 MESSAGE_TYPE_TO_ROLE 映射中时，原样保留"""
        msg = MagicMock(type="tool", content="tool result")
        msg.role = ""  # type 优先取到 "tool"，不在映射中，fallback 保留
        result = LLMChain._message_to_dict(msg)
        assert result["role"] == "tool"
        assert result["content"] == "tool result"

    # ── _get_chat_history ────────────────────────────────────────────

    def test_get_chat_history_no_context(self):
        """context 为 None 时返回空列表"""
        chain = self._make_chain()
        chain._context = None
        assert chain._get_chat_history() == []

    def test_get_chat_history_empty_messages(self):
        """context 返回空消息列表"""
        chain = self._make_chain()
        chain._context = self._mock_context([])
        assert chain._get_chat_history() == []

    def test_get_chat_history_with_messages(self):
        """正常从 context 获取消息并转换为 dict"""
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain()
        chain._context = self._mock_context([
            UserMessage(content="user1"),
            AssistantMessage(content="asst1"),
            UserMessage(content="user2"),
            AssistantMessage(content="asst2"),
        ])
        result = chain._get_chat_history()
        assert len(result) == 4
        assert result[0] == {"role": "user", "content": "user1"}
        assert result[1] == {"role": "assistant", "content": "asst1"}
        assert result[2] == {"role": "user", "content": "user2"}
        assert result[3] == {"role": "assistant", "content": "asst2"}

    def test_get_chat_history_exception_returns_empty(self):
        """context.get_messages 抛异常时返回空列表，不崩溃"""
        chain = self._make_chain()
        ctx = MagicMock()
        ctx.get_messages = MagicMock(side_effect=RuntimeError("boom"))
        chain._context = ctx
        assert chain._get_chat_history() == []

    # ── _get_history_size ────────────────────────────────────────────

    def test_get_history_size_from_conf(self):
        """historySize 应从 IR 配置中读取"""
        chain = self._make_chain(history_size=12)
        assert chain._get_history_size() == 12

    @staticmethod
    def test_get_history_size_default():
        """未配置 historySize 时应使用默认值 3"""
        from jiuwen.extension.workflow_node.llm_chain import CHAT_HISTORY_MAX_TURN_DEFAULT
        conf = _make_llm_chain_conf()
        del conf["historySize"]
        chain = LLMChain(conf=conf)
        assert chain._get_history_size() == CHAT_HISTORY_MAX_TURN_DEFAULT

    # ── _truncate_history_by_turn ────────────────────────────────────

    @staticmethod
    def test_truncate_by_turn_basic():
        """按轮数截取：2 轮取最近 2 条 user 及其对应回复"""
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a3"},
        ]
        result = LLMChain._truncate_history_by_turn(history, 2)
        # 2 轮 = 从第 2 个 user (u2) 开始
        assert result == [
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a3"},
        ]

    @staticmethod
    def test_truncate_by_turn_user_with_multiple_assistant():
        """1 条 user 后跟多条 assistant/tool 消息，同属 1 轮"""
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "tool", "content": "t1"},
            {"role": "assistant", "content": "a2"},
        ]
        result = LLMChain._truncate_history_by_turn(history, 1)
        # 1 轮 = 从最后一个 user 开始
        assert result == [
            {"role": "user", "content": "u2"},
            {"role": "tool", "content": "t1"},
            {"role": "assistant", "content": "a2"},
        ]

    @staticmethod
    def test_truncate_by_turn_exceeds_available():
        """请求轮数超过实际轮数时返回全部"""
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
        ]
        result = LLMChain._truncate_history_by_turn(history, 10)
        assert result == history

    @staticmethod
    def test_truncate_by_turn_empty():
        """空列表返回空"""
        assert LLMChain._truncate_history_by_turn([], 3) == []

    @staticmethod
    def test_truncate_by_turn_zero():
        """num_turns=0 返回空"""
        history = [{"role": "user", "content": "u1"}]
        assert LLMChain._truncate_history_by_turn(history, 0) == []

    # ── _get_history ─────────────────────────────────────────────────

    def test_get_history_preserves_latest_assistant_reply(self):
        """核心 bug 修复: 多轮对话时最近一条 assistant 回复不应被丢弃

        前端 conversationHistory: [user1, asst1, user2, asst2]
        当前 query 由模板渲染提供，不在 history 中。
        预期 messages 应包含 asst2。
        """
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="我叫张三"),
            AssistantMessage(content="你好，张三！"),
            UserMessage(content="我的工号是832132"),
            AssistantMessage(content="您好，张三！请问有什么我可以帮您的吗？"),
        ])
        messages = chain._get_history(user_prompt="我的工号是什么", system_prompt=None)

        assistant_contents = [m["content"] for m in messages if m["role"] == "assistant"]
        assert "您好，张三！请问有什么我可以帮您的吗？" in assistant_contents, \
            f"最新 assistant 回复被丢失! messages={messages}"
        assert messages[-1] == {"role": "user", "content": "我的工号是什么"}

    def test_get_history_no_duplicate_user_message(self):
        """conversationHistory 不含当前用户消息，不应出现重复 user

        history: [user1, asst1]
        query: "今天天气怎么样"
        预期: [user1, asst1, user(当前query)]  共 3 条
        """
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="你好"),
            AssistantMessage(content="你好！"),
        ])
        messages = chain._get_history(user_prompt="今天天气怎么样", system_prompt=None)

        assert len(messages) == 3
        assert messages[0] == {"role": "user", "content": "你好"}
        assert messages[1] == {"role": "assistant", "content": "你好！"}
        assert messages[2] == {"role": "user", "content": "今天天气怎么样"}

    def test_get_history_empty_chat_history(self):
        """无历史消息时，只有 system(可选) + user_prompt"""
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([])
        messages = chain._get_history(user_prompt="hello", system_prompt=None)
        assert messages == [{"role": "user", "content": "hello"}]

    def test_get_history_with_system_prompt(self):
        """system_prompt 应出现在消息列表开头"""
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="你好"),
            AssistantMessage(content="你好！"),
        ])
        messages = chain._get_history(user_prompt="问题", system_prompt="你是一个助手")
        assert messages[0] == {"role": "system", "content": "你是一个助手"}
        assert messages[-1] == {"role": "user", "content": "问题"}

    def test_get_history_respects_history_size_by_turn(self):
        """historySize 按轮数截断（非条数），1 轮 = 1 user + 其对应回复"""
        chain = self._make_chain(enable_history=True, history_size=2)
        history_msgs = []
        for i in range(10):
            history_msgs.append(MagicMock(type="human", content=f"user msg {i}"))
            history_msgs.append(MagicMock(type="ai", content=f"assistant reply {i}"))
        chain._context = self._mock_context(history_msgs)

        messages = chain._get_history(user_prompt="当前问题", system_prompt=None)
        history_part = messages[:-1]  # 去掉最后的 user_prompt
        # historySize=2 按轮数: 取最近 2 轮 user = 2 user + 2 assistant = 4 条
        assert len(history_part) == 4

    def test_get_history_filters_empty_content(self):
        """content 为空的消息应被过滤"""
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="你好"),
            AssistantMessage(content=""),       # 空 content — 应被过滤
            AssistantMessage(content="你好！"),
        ])
        messages = chain._get_history(user_prompt="test", system_prompt=None)
        # 所有 assistant 消息的 content 应非空
        assistant_contents = [m["content"] for m in messages if m["role"] == "assistant"]
        assert "" not in assistant_contents

    def test_get_history_single_user_message(self):
        """只有 1 条 user history 时不应丢失（修复前 [:-1] 会截掉它）"""
        from openjiuwen.core.foundation.llm import UserMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="之前的用户消息"),
        ])
        messages = chain._get_history(user_prompt="当前问题", system_prompt=None)
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "之前的用户消息"}
        assert messages[1] == {"role": "user", "content": "当前问题"}

    def test_get_history_uses_ir_history_size(self):
        """historySize 从 IR 配置读取，而非硬编码常量"""
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True, history_size=1)
        chain._context = self._mock_context([
            UserMessage(content="u1"),
            AssistantMessage(content="a1"),
            UserMessage(content="u2"),
            AssistantMessage(content="a2"),
            UserMessage(content="u3"),
            AssistantMessage(content="a3"),
        ])
        messages = chain._get_history(user_prompt="当前问题", system_prompt=None)
        # historySize=1: 只取最近 1 轮 (u3 + a3) + 当前 user_prompt
        assert len(messages) == 3
        assert messages[0] == {"role": "user", "content": "u3"}
        assert messages[1] == {"role": "assistant", "content": "a3"}
        assert messages[2] == {"role": "user", "content": "当前问题"}

    # ── _process_inputs ──────────────────────────────────────────────

    def test_process_inputs_disabled(self):
        """enableHistory=False 时 CHAT_HISTORY 为空字符串"""
        chain = self._make_chain(enable_history=False)
        chain._context = self._mock_context([
            MagicMock(type="human", content="你好"),
        ])
        inputs = {}
        chain._process_inputs(inputs)
        assert inputs.get("CHAT_HISTORY") == ""

    def test_process_inputs_preserves_latest_assistant(self):
        """CHAT_HISTORY 变量应包含所有历史消息，不丢失 assistant 回复"""
        from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([
            UserMessage(content="我叫张三"),
            AssistantMessage(content="你好，张三！"),
            UserMessage(content="我的工号是832132"),
            AssistantMessage(content="您好，张三！请问有什么我可以帮您的吗？"),
        ])
        inputs = {}
        chain._process_inputs(inputs)
        chat_history_str = inputs.get("CHAT_HISTORY", "")
        assert "您好，张三！请问有什么我可以帮您的吗？" in chat_history_str, \
            f"_process_inputs 丢失了最新 assistant 回复! CHAT_HISTORY={chat_history_str}"

    def test_process_inputs_respects_history_size_by_turn(self):
        """CHAT_HISTORY 变量按轮数截断，超出窗口的消息不应出现"""
        chain = self._make_chain(enable_history=True, history_size=2)
        history_msgs = []
        for i in range(10):
            history_msgs.append(MagicMock(type="human", content=f"用户{i}"))
            history_msgs.append(MagicMock(type="ai", content=f"助手{i}"))
        chain._context = self._mock_context(history_msgs)

        inputs = {}
        chain._process_inputs(inputs)
        chat_history_str = inputs.get("CHAT_HISTORY", "")
        # historySize=2 按轮数: 最近 2 轮 = 用户8+助手8+用户9+助手9
        assert "用户7" not in chat_history_str, "超出截断窗口的消息不应出现"
        assert "助手7" not in chat_history_str, "超出截断窗口的消息不应出现"
        assert "用户8" in chat_history_str
        assert "助手9" in chat_history_str

    def test_process_inputs_empty_history(self):
        """无历史消息时 CHAT_HISTORY 为空字符串"""
        chain = self._make_chain(enable_history=True)
        chain._context = self._mock_context([])
        inputs = {}
        chain._process_inputs(inputs)
        assert inputs.get("CHAT_HISTORY") == ""


class TestRenderPromptWithWhitespace:
    """验证 _render_prompt 在模板含空白占位符时能正确替换"""

    def test_render_with_whitespace_placeholder(self):
        chain = LLMChain(conf=_make_llm_chain_conf(
            template_content=[{"content": "{{ query            }}", "role": "user"}],
        ))
        result = chain._render_prompt("{{ query            }}", {"query": "你好"})
        assert result == "你好"

    def test_render_rejects_undefined_variable(self):
        from openjiuwen.core.common.exception.errors import ExecutionError

        chain = LLMChain(conf=_make_llm_chain_conf())
        with pytest.raises(ExecutionError, match="Error parsing the placeholder"):
            chain._render_prompt("{{query.aa}}", {"query": "你好"})


class TestResolveImageUrlTlsVerify:
    """_resolve_image_url 需按 MODEL_CFG_SSL_MODE / MODEL_CFG_SSL_CERT_PATH 决定 TLS 校验方式"""

    @staticmethod
    def _run_and_capture_verify(monkeypatch):
        import asyncio

        import httpx

        captured = {}

        class _FakeResponse:
            headers = {"content-type": "image/png"}
            content = b"abc"

            def raise_for_status(self):
                return None

        class _FakeClient:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                return False

            async def get(self, url):
                return _FakeResponse()

        monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
        result = asyncio.run(LLMChain._resolve_image_url("http://intranet.example/img.png"))
        assert result.startswith("data:image/png;base64,")
        return captured.get("verify")

    def test_default_enables_verification(self, monkeypatch):
        monkeypatch.delenv("MODEL_CFG_SSL_MODE", raising=False)
        monkeypatch.delenv("MODEL_CFG_SSL_CERT_PATH", raising=False)
        assert self._run_and_capture_verify(monkeypatch) is True

    def test_ssl_mode_false_disables_verification(self, monkeypatch):
        monkeypatch.setenv("MODEL_CFG_SSL_MODE", "false")
        monkeypatch.delenv("MODEL_CFG_SSL_CERT_PATH", raising=False)
        assert self._run_and_capture_verify(monkeypatch) is False

    def test_cert_path_is_used_for_intranet_ca(self, monkeypatch):
        monkeypatch.setenv("MODEL_CFG_SSL_MODE", "true")
        monkeypatch.setenv("MODEL_CFG_SSL_CERT_PATH", "/etc/ssl/certs/intranet-ca.pem")
        assert self._run_and_capture_verify(monkeypatch) == "/etc/ssl/certs/intranet-ca.pem"
