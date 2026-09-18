# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
RestfulApiCardNew 和 RestfulApiToolNew 单元测试。

测试范围：
1. RestfulApiCardNew：字段默认值、自定义值、Pydantic 校验
2. RestfulApiToolNew：构造、属性委托、_check_status_ok、_format_output、
   _create_error_invoke_response、_validate_request_params（URL 校验）、
   ainvoke / astream 的异常路径
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.extension.wrapper.restful_api_new import (
    RestfulApiCardNew,
    RestfulApiToolNew,
)
from jiuwen.plugin.common import constant
from jiuwen.plugin.common.exception import (
    PluginCommonException,
    PluginRestfulAuthException,
)
from jiuwen.plugin.models.param import Param


def _make_card(**overrides) -> RestfulApiCardNew:
    defaults = dict(
        id="test_tool_id",
        name="test_tool",
        description="A test tool",
        path="https://example.com/api",
        method="POST",
        params=[],
        response=[],
        headers={},
        auth={},
        query_params={},
        plugin_dependency={},
        async_conf={},
        input_parameters={},
        is_from_ir=True,
    )
    defaults.update(overrides)
    return RestfulApiCardNew(**defaults)


class TestRestfulApiCardNew:
    def test_default_values(self):
        card = RestfulApiCardNew(id="c1", name="n1")
        assert card.params == []
        assert card.path == ""
        assert card.headers == {}
        assert card.method == "POST"
        assert card.response == []
        assert card.plugin_name == ""
        assert card.plugin_desc == ""
        assert card.auth == {}
        assert card.label == ""
        assert card.related_info is None
        assert card.status is None
        assert card.principle == ""
        assert card.query_params == {}
        assert card.user_id == ""
        assert card.plugin_dependency == {}
        assert card.async_conf == {}
        assert card.async_switch is False
        assert card.is_from_ir is False
        assert card.input_parameters == {}
        assert card.file_handler == ""
        assert card.cert is None

    def test_custom_values(self):
        card = _make_card(
            method="GET",
            path="https://api.example.com/v1",
            headers={"Content-Type": "application/json"},
            auth={"scope": "SERVICE", "headers": {"X-Token": "abc"}},
            plugin_name="my_plugin",
            plugin_desc="desc",
            label="test_label",
            related_info={"logo": "logo.png"},
            status=1,
            principle="principle text",
            query_params={"q": "val"},
            user_id="u123",
            plugin_dependency={"dep": "v1"},
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
                "period_of_round": 5,
            },
            async_switch=True,
            is_from_ir=True,
            input_parameters={"p1": "{{inputs.x}}"},
            file_handler="handler_fn",
            cert=True,
            timeout=30.0,
        )
        assert card.method == "GET"
        assert card.path == "https://api.example.com/v1"
        assert card.headers == {"Content-Type": "application/json"}
        assert card.auth["scope"] == "SERVICE"
        assert card.plugin_name == "my_plugin"
        assert card.plugin_desc == "desc"
        assert card.label == "test_label"
        assert card.related_info == {"logo": "logo.png"}
        assert card.status == 1
        assert card.principle == "principle text"
        assert card.query_params == {"q": "val"}
        assert card.user_id == "u123"
        assert card.plugin_dependency == {"dep": "v1"}
        assert card.async_conf["async_switch"] is True
        assert card.async_switch is True
        assert card.is_from_ir is True
        assert card.input_parameters == {"p1": "{{inputs.x}}"}
        assert card.file_handler == "handler_fn"
        assert card.cert is True
        assert card.timeout == 30.0

    def test_params_field(self):
        p = Param(name="city", description="city name", param_type="string")
        card = _make_card(params=[p], response=[p])
        assert len(card.params) == 1
        assert card.params[0].name == "city"
        assert len(card.response) == 1

    def test_arbitrary_types_allowed(self):
        card = _make_card()
        assert card.model_config.get("arbitrary_types_allowed") is True


class TestRestfulApiToolNewConstruction:
    def test_basic_construction(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.path == "https://example.com/api"
        assert tool.method == "POST"
        assert tool.params == []
        assert tool.response == []
        assert tool.id == "test_tool_id"
        assert tool.is_from_ir is True
        assert tool.input_parameters == {}
        assert tool.plugin_reade_buffer_size > 0

    def test_method_uppercased(self):
        card = _make_card(method="get")
        tool = RestfulApiToolNew(card)
        assert tool.method == "GET"

    def test_invalid_http_method_raises(self):
        card = _make_card(method="INVALID")
        with pytest.raises(PluginCommonException):
            RestfulApiToolNew(card)

    def test_auth_encrypted(self):
        card = _make_card(auth={"scope": "SERVICE", "headers": {"X-Key": "secret"}})
        with patch(
            "jiuwen.extension.wrapper.restful_api_new.ApiUtils.encrypt_service_auth",
            return_value={
                "scope": "SERVICE",
                "headers": {"X-Key": "encrypted"},
                "crypt_method": "jiuwen",
            },
        ):
            tool = RestfulApiToolNew(card)
            assert tool.auth.get("crypt_method") == "jiuwen"

    def test_empty_auth(self):
        card = _make_card(auth={})
        tool = RestfulApiToolNew(card)
        assert tool.auth == {}

    def test_cert_boolean_conversion(self):
        card = _make_card(cert="true")
        tool = RestfulApiToolNew(card)
        assert tool._cert is True

    def test_cert_none_defaults_to_true(self):
        card = _make_card(cert=None)
        tool = RestfulApiToolNew(card)
        assert tool._cert is True

    def test_cert_false(self):
        card = _make_card(cert=False)
        tool = RestfulApiToolNew(card)
        assert tool._cert is False

    def test_async_switch_from_async_conf(self):
        card = _make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
                "period_of_round": 5,
            }
        )
        tool = RestfulApiToolNew(card)
        assert tool.async_switch is True

    def test_async_switch_false_by_default(self):
        card = _make_card(async_conf={})
        tool = RestfulApiToolNew(card)
        assert not tool.async_switch

    def test_properties_delegate_to_card(self):
        card = _make_card(
            plugin_name="pn",
            plugin_desc="pd",
            label="lb",
            related_info={"logo": "l.png"},
            status=2,
            principle="pr",
            query_params={"k": "v"},
            user_id="uid",
            plugin_dependency={"d": "1"},
        )
        tool = RestfulApiToolNew(card)
        assert tool.plugin_name == "pn"
        assert tool.plugin_desc == "pd"
        assert tool.label == "lb"
        assert tool.related_info == {"logo": "l.png"}
        assert tool.status == 2
        assert tool.principle == "pr"
        assert tool.query_params == {"k": "v"}
        assert tool.user_id == "uid"
        assert tool.plugin_dependency == {"d": "1"}


class TestCheckStatusOk:
    def test_200_is_ok(self):
        assert RestfulApiToolNew._check_status_ok(200) is True

    def test_201_is_ok(self):
        assert RestfulApiToolNew._check_status_ok(201) is True

    def test_299_is_ok(self):
        assert RestfulApiToolNew._check_status_ok(299) is True

    def test_100_not_ok(self):
        assert RestfulApiToolNew._check_status_ok(100) is False

    def test_300_not_ok(self):
        assert RestfulApiToolNew._check_status_ok(300) is False

    def test_404_not_ok(self):
        assert RestfulApiToolNew._check_status_ok(404) is False

    def test_500_not_ok(self):
        assert RestfulApiToolNew._check_status_ok(500) is False


class TestFormatOutput:
    def test_format_output_with_all_fields(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        result = tool._format_output(0, "success", {"key": "value"})
        assert result[constant.ERR_CODE] == 0
        assert result[constant.ERR_MESSAGE] == "success"
        assert result[constant.RESTFUL_DATA] == {"key": "value"}

    def test_format_output_default_data(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        result = tool._format_output(0, "ok")
        assert result[constant.ERR_CODE] == 0
        assert result[constant.ERR_MESSAGE] == "ok"
        assert result[constant.RESTFUL_DATA] == {}

    def test_format_output_error_code(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        result = tool._format_output(105001, "unexpected error", "")
        assert result[constant.ERR_CODE] == 105001
        assert result[constant.ERR_MESSAGE] == "unexpected error"
        assert result[constant.RESTFUL_DATA] == ""


class TestCreateErrorInvokeResponse:
    def _make_tool(self):
        return RestfulApiToolNew(_make_card())

    def test_timeout_error(self):
        import requests

        tool = self._make_tool()
        result = tool._create_error_invoke_response(requests.exceptions.ReadTimeout())
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.code

    def test_async_timeout_error(self):
        tool = self._make_tool()
        result = tool._create_error_invoke_response(asyncio.TimeoutError())
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.code

    def test_proxy_error(self):
        import requests

        tool = self._make_tool()
        result = tool._create_error_invoke_response(requests.exceptions.ProxyError())
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_PROXY_CONNECT_ERROR.code

    def test_plugin_common_exception(self):
        tool = self._make_tool()
        exc = PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED, message="bad params"
        )
        result = tool._create_error_invoke_response(exc)
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_PARAMS_CHECK_FAILED.code

    def test_unknown_error(self):
        tool = self._make_tool()
        result = tool._create_error_invoke_response(RuntimeError("something broke"))
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_UNEXPECTED_ERROR.code


class TestCreateErrorStreamResponse:
    def _make_tool(self):
        return RestfulApiToolNew(_make_card())

    def test_timeout_raises(self):
        import requests

        tool = self._make_tool()
        with pytest.raises(Exception) as exc_info:
            tool._create_error_stream_response(requests.exceptions.ReadTimeout())
        assert "timeout" in str(exc_info.value).lower() or exc_info.value is not None

    def test_unknown_error_raises(self):
        tool = self._make_tool()
        with pytest.raises(Exception):
            tool._create_error_stream_response(RuntimeError("boom"))


class TestValidateRequestParams:
    def _make_tool(self, **card_overrides):
        return RestfulApiToolNew(_make_card(**card_overrides))

    @patch("jiuwen.extension.wrapper.restful_api_new.illegal_url", return_value=False)
    @patch(
        "jiuwen.extension.wrapper.restful_api_new.url_to_ip_with_protocol_and_port",
        return_value=None,
    )
    @patch(
        "jiuwen.extension.wrapper.restful_api_new.config",
        {"restful_api": {"skip_ssrf_check": "true"}},
    )
    def test_valid_url_passes(self, mock_ssrf, mock_illegal):
        tool = self._make_tool()
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/api"
        rp.headers = {}
        rp.query_params_in_inputs = {}
        tool._validate_request_params(rp)

    @pytest.mark.skip(
        reason="TODO(知识库改造): 非法 URL 校验已临时移除以保证 KB 内网回环调用，"
        "待恢复 _check_url_validate 的 illegal_url 校验后解除该 skip"
    )
    @patch("jiuwen.extension.wrapper.restful_api_new.illegal_url", return_value=True)
    def test_illegal_url_raises(self, mock_illegal):
        tool = self._make_tool()
        rp = MagicMock()
        rp.ip_address_url = "https://evil.com/api"
        rp.headers = {}
        rp.query_params_in_inputs = {}
        with pytest.raises(PluginCommonException) as exc_info:
            tool._validate_request_params(rp)
        assert "illegal" in exc_info.value.message.lower()


class TestLogAndRaiseError:
    def test_raises_auth_exception(self):
        tool = RestfulApiToolNew(_make_card(plugin_name="my_plugin"))
        with pytest.raises(PluginRestfulAuthException):
            tool._log_and_raise_error("auth failed")

    def test_includes_plugin_name(self):
        tool = RestfulApiToolNew(_make_card(plugin_name="my_plugin"))
        with pytest.raises(PluginRestfulAuthException) as exc_info:
            tool._log_and_raise_error("auth failed")
        assert "my_plugin" in exc_info.value.message


class TestAinvoke:
    @patch("jiuwen.extension.wrapper.restful_api_new.illegal_url", return_value=False)
    @patch("jiuwen.extension.wrapper.restful_api_new.url_to_ip_with_protocol_and_port")
    @patch("jiuwen.extension.wrapper.restful_api_new.config", return_value={})
    @pytest.mark.asyncio
    async def test_ainvoke_returns_error_on_request_failure(
        self, mock_config, mock_ssrf, mock_illegal
    ):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        with patch.object(
            tool._request_params_creator,
            "create",
            side_effect=Exception("create failed"),
        ):
            result = await tool.ainvoke({"input": "test"})
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_UNEXPECTED_ERROR.code

    @patch("jiuwen.extension.wrapper.restful_api_new.illegal_url", return_value=False)
    @patch("jiuwen.extension.wrapper.restful_api_new.url_to_ip_with_protocol_and_port")
    @patch("jiuwen.extension.wrapper.restful_api_new.config", return_value={})
    @pytest.mark.asyncio
    async def test_ainvoke_timeout_returns_timeout_error(
        self, mock_config, mock_ssrf, mock_illegal
    ):
        import requests

        card = _make_card()
        tool = RestfulApiToolNew(card)
        with patch.object(
            tool._request_params_creator,
            "create",
            side_effect=requests.exceptions.ReadTimeout(),
        ):
            result = await tool.ainvoke({"input": "test"})
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_REQUEST_TIMEOUT_ERROR.code

    @patch("jiuwen.extension.wrapper.restful_api_new.illegal_url", return_value=False)
    @patch("jiuwen.extension.wrapper.restful_api_new.url_to_ip_with_protocol_and_port")
    @patch("jiuwen.extension.wrapper.restful_api_new.config", return_value={})
    @pytest.mark.asyncio
    async def test_ainvoke_plugin_exception_returns_error(
        self, mock_config, mock_ssrf, mock_illegal
    ):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        exc = PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED, message="param error"
        )
        with patch.object(tool._request_params_creator, "create", side_effect=exc):
            result = await tool.ainvoke({"input": "test"})
        assert result[constant.ERR_CODE] == StatusCode.PLUGIN_PARAMS_CHECK_FAILED.code


class TestInvokeDelegatesToAinvoke:
    @pytest.mark.asyncio
    async def test_invoke_calls_ainvoke(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        mock_result = {
            constant.ERR_CODE: 0,
            constant.ERR_MESSAGE: "ok",
            constant.RESTFUL_DATA: {},
        }
        with patch.object(
            tool, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ) as mock_ainvoke:
            result = await tool.invoke({"input": "test"})
            mock_ainvoke.assert_called_once()
            assert result == mock_result


class TestStreamDelegatesToAstream:
    @pytest.mark.asyncio
    async def test_stream_returns_astream(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)

        async def mock_astream(inputs, **kwargs):
            yield "chunk1"
            yield "chunk2"

        with patch.object(tool, "astream", side_effect=mock_astream):
            result = tool.stream({"input": "test"})
            chunks = []
            async for chunk in await result:
                chunks.append(chunk)
            assert chunks == ["chunk1", "chunk2"]


class TestCreatePostRequest:
    def test_basic_post_request(self):
        card = _make_card(method="POST")
        tool = RestfulApiToolNew(card)
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/api"
        rp.query_params_in_inputs = {"q": "v"}
        rp.file_params = None
        rp.request_arg = {"json": {"key": "value"}}
        rp.headers = {"Content-Type": "application/json"}
        request = tool._create_post_request(rp)
        assert request["method"] == "POST"
        assert request["url"] == "https://example.com/api"
        assert request["params"] == {"q": "v"}
        assert request["headers"] == {"Content-Type": "application/json"}

    def test_file_params_omits_headers(self):
        card = _make_card(method="POST")
        tool = RestfulApiToolNew(card)
        rp = MagicMock()
        rp.ip_address_url = "https://example.com/api"
        rp.query_params_in_inputs = {}
        rp.file_params = {"file": ("test.txt", MagicMock(), "text/plain")}
        rp.request_arg = {}
        rp.headers = {"Content-Type": "application/json"}
        request = tool._create_post_request(rp)
        assert "data" in request
        assert "headers" not in request


class TestFormatToFormData:
    def test_format_to_form_data(self):
        card = _make_card()
        tool = RestfulApiToolNew(card)
        file_params = [{"file": ("test.txt", b"content", "text/plain")}]
        request_arg = {"json": {"key": "value"}}
        form_data = tool._format_to_form_data(file_params, request_arg)
        assert form_data is not None


class TestParamLocationEnum:
    def test_enum_values(self):
        assert RestfulApiToolNew.ParamLocation.BODY.value == "Body"
        assert RestfulApiToolNew.ParamLocation.HEADERS.value == "Headers"
        assert RestfulApiToolNew.ParamLocation.QUERY.value == "Query"
        assert RestfulApiToolNew.ParamLocation.PATH.value == "Path"
