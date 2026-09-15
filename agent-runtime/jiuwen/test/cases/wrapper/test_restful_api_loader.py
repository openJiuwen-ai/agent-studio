# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
restful_api_loader 单元测试。

测试范围：
1. convert_ir_to_card：IR 配置转换、驼峰转蛇形、参数反序列化、校验
2. param_deserialization：参数列表反序列化
3. check_valid_value：参数位置和 HTTP 方法校验
4. check_async_conf：异步配置校验
5. extend_auth：auth 扩展点
6. load_restful_api_from_ir：端到端注册流程（mock Runner）
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.extension.wrapper.restful_api_loader import (
    check_async_conf,
    check_valid_value,
    convert_ir_to_card,
    extend_auth,
    load_restful_api_from_ir,
    param_deserialization,
)
from jiuwen.extension.wrapper.restful_api_new import RestfulApiCardNew
from jiuwen.plugin.common.constant import (
    PLUGIN_MAX_PERIOD_ROUND,
    PLUGIN_MAX_TIME_OUT,
)
from jiuwen.plugin.common.exception import PluginCommonException
from jiuwen.plugin.models.param import Param


def _make_valid_ir_data(**overrides) -> dict:
    defaults = dict(
        name="test_api",
        description="A test API",
        url="https://example.com/api",
        method="POST",
        headers={"Content-Type": "application/json"},
        auth={},
        arguments=[
            {
                "name": "city",
                "description": "city name",
                "type": "string",
                "required": True,
                "method": "Body",
            },
        ],
        response=[
            {
                "name": "result",
                "description": "result data",
                "type": "string",
                "required": False,
                "method": "Body",
            },
        ],
        principle="test principle",
        logo="",
        pluginDependency={},
        id="test_api_id",
        asyncInvoke={},
        inputParameters={},
        fileHandler="",
    )
    defaults.update(overrides)
    return defaults


class TestConvertIrToCard:
    def test_basic_conversion(self):
        ir_data = _make_valid_ir_data()
        card = convert_ir_to_card(ir_data)
        assert isinstance(card, RestfulApiCardNew)
        assert card.name == "test_api"
        assert card.description == "A test API"
        assert card.path == "https://example.com/api"
        assert card.method == "POST"
        assert card.headers == {"Content-Type": "application/json"}
        assert card.is_from_ir is True
        assert len(card.params) == 1
        assert card.params[0].name == "city"
        assert len(card.response) == 1
        assert card.response[0].name == "result"
        assert card.principle == "test principle"
        assert card.plugin_dependency == {}
        assert card.input_parameters == {}
        assert card.file_handler == ""

    def test_camel_to_snake_conversion(self):
        ir_data = _make_valid_ir_data(
            asyncInvoke={"async_switch": False},
            inputParameters={"p1": "val"},
            fileHandler="handler",
        )
        card = convert_ir_to_card(ir_data)
        assert card.input_parameters == {"p1": "val"}
        assert card.file_handler == "handler"

    def test_headers_not_converted(self):
        ir_data = _make_valid_ir_data(headers={"X-Custom-Header": "value"})
        card = convert_ir_to_card(ir_data)
        assert card.headers == {"X-Custom-Header": "value"}

    def test_auth_not_converted(self):
        ir_data = _make_valid_ir_data(
            auth={"scope": "SERVICE", "headers": {"X-Key": "val"}}
        )
        card = convert_ir_to_card(ir_data)
        assert "scope" in card.auth

    def test_non_dict_raises(self):
        with pytest.raises(PluginCommonException) as exc_info:
            convert_ir_to_card("not a dict")
        assert "not dict type" in exc_info.value.message

    def test_missing_name_raises(self):
        ir_data = _make_valid_ir_data()
        del ir_data["name"]
        with pytest.raises(Exception):
            convert_ir_to_card(ir_data)

    def test_missing_url_raises(self):
        ir_data = _make_valid_ir_data()
        del ir_data["url"]
        with pytest.raises(Exception):
            convert_ir_to_card(ir_data)

    def test_id_uses_name_not_ir_id(self):
        ir_data = _make_valid_ir_data(id="different_id")
        card = convert_ir_to_card(ir_data)
        assert card.id == "test_api"

    def test_invalid_url_raises(self):
        ir_data = _make_valid_ir_data(url="ftp://invalid.com")
        with pytest.raises(Exception):
            convert_ir_to_card(ir_data)

    def test_id_uses_name_over_ir_id(self):
        ir_data = _make_valid_ir_data()
        card = convert_ir_to_card(ir_data)
        assert card.id == "test_api"

    def test_id_falls_back_to_ir_id_when_name_same_as_id(self):
        """当 name 与 id 相同时，card.id 等于 name（即等于 ir id）"""
        ir_data = _make_valid_ir_data(name="my_plugin", id="my_plugin")
        card = convert_ir_to_card(ir_data)
        assert card.id == "my_plugin"

    def test_method_defaults_to_post(self):
        ir_data = _make_valid_ir_data(method="GET")
        card = convert_ir_to_card(ir_data)
        assert card.method == "GET"

    def test_empty_arguments_and_response(self):
        ir_data = _make_valid_ir_data(arguments=[], response=[])
        card = convert_ir_to_card(ir_data)
        assert card.params == []
        assert card.response == []

    def test_plugin_dependency_preserved(self):
        ir_data = _make_valid_ir_data(pluginDependency={"dep_key": "dep_val"})
        card = convert_ir_to_card(ir_data)
        assert card.plugin_dependency == {"dep_key": "dep_val"}

    def test_cert_env_var(self):
        ir_data = _make_valid_ir_data()
        with patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}):
            card = convert_ir_to_card(ir_data)
            assert card.cert == "false"

    def test_timeout_env_var(self):
        ir_data = _make_valid_ir_data()
        with patch.dict(os.environ, {"PLUGIN_REQUEST_TIMEOUT_KEY": "99.5"}):
            card = convert_ir_to_card(ir_data)
            assert card.timeout == 99.5

    def test_buffer_size_env_var(self):
        ir_data = _make_valid_ir_data()
        with patch.dict(os.environ, {"STREAM_PLUGIN_BUFSIZE_KEY": "8192"}):
            card = convert_ir_to_card(ir_data)
            assert card.plugin_reade_buffer_size == 8192

    def test_full_config_camel_case(self):
        ir_data = _make_valid_ir_data(
            pluginDependency={"hook": "test"},
            asyncInvoke={"async_switch": True, "callback_url": "https://cb.com/"},
            inputParameters={"key": "value"},
            fileHandler="my_handler",
        )
        card = convert_ir_to_card(ir_data)
        assert card.plugin_dependency == {"hook": "test"}
        assert card.async_conf == {
            "async_switch": True,
            "callback_url": "https://cb.com/",
        }
        assert card.input_parameters == {"key": "value"}
        assert card.file_handler == "my_handler"


class TestParamDeserialization:
    def test_basic_params(self):
        args = [
            {
                "name": "p1",
                "description": "param 1",
                "type": "string",
                "required": True,
                "method": "Body",
            },
            {
                "name": "p2",
                "description": "param 2",
                "type": "integer",
                "required": False,
                "method": "Query",
            },
        ]
        params = param_deserialization(args)
        assert len(params) == 2
        assert params[0].name == "p1"
        assert params[1].name == "p2"
        assert params[1].method == "Query"

    def test_missing_name_raises(self):
        args = [{"description": "no name"}]
        with pytest.raises(PluginCommonException) as exc_info:
            param_deserialization(args)
        assert "name and description needed" in exc_info.value.message

    def test_missing_description_raises(self):
        args = [{"name": "p1"}]
        with pytest.raises(PluginCommonException) as exc_info:
            param_deserialization(args)
        assert "name and description needed" in exc_info.value.message

    def test_empty_arguments(self):
        params = param_deserialization([])
        assert params == []

    def test_level_string_to_int(self):
        args = [{"name": "p1", "description": "d", "level": "3"}]
        params = param_deserialization(args)
        assert params[0].level == 3

    def test_level_int_preserved(self):
        args = [{"name": "p1", "description": "d", "level": 5}]
        params = param_deserialization(args)
        assert params[0].level == 5

    def test_default_values(self):
        args = [{"name": "p1", "description": "d"}]
        params = param_deserialization(args)
        assert params[0].required is False
        assert params[0].visible is True
        assert params[0].method == "Body"
        assert params[0].schema == []

    def test_allow_schema_is_empty(self):
        args = [{"name": "p1", "description": "d", "type": "object", "schema": []}]
        params = param_deserialization(args, allow_schema_is_empty=True)
        assert len(params) == 1

    def test_actual_type_preserved(self):
        args = [{"name": "p1", "description": "d", "actual_type": "List[str]"}]
        params = param_deserialization(args)
        assert params[0].actual_type == "List[str]"


class TestCheckValidValue:
    def _make_card(self, method="POST", param_methods=None) -> RestfulApiCardNew:
        params = []
        if param_methods:
            for m in param_methods:
                params.append(
                    Param(name="p", description="d", param_type="string", method=m)
                )
        return RestfulApiCardNew(
            id="test",
            name="test",
            method=method,
            path="https://example.com",
            params=params,
        )

    def test_valid_body_param(self):
        card = self._make_card(param_methods=["Body"])
        check_valid_value(card)

    def test_valid_headers_param(self):
        card = self._make_card(param_methods=["Headers"])
        check_valid_value(card)

    def test_valid_query_param(self):
        card = self._make_card(param_methods=["Query"])
        check_valid_value(card)

    def test_valid_path_param(self):
        card = self._make_card(param_methods=["Path"])
        check_valid_value(card)

    def test_invalid_param_location_raises(self):
        card = self._make_card(param_methods=["Cookie"])
        with pytest.raises(PluginCommonException) as exc_info:
            check_valid_value(card)
        assert "only supports" in exc_info.value.message

    def test_valid_post_method(self):
        card = self._make_card(method="POST")
        check_valid_value(card)

    def test_valid_get_method(self):
        card = self._make_card(method="GET")
        check_valid_value(card)

    def test_invalid_method_raises(self):
        card = self._make_card(method="DELETE")
        with pytest.raises(PluginCommonException) as exc_info:
            check_valid_value(card)
        assert "only supports post and get" in exc_info.value.message

    def test_case_insensitive_method(self):
        card = self._make_card(method="post")
        check_valid_value(card)

    def test_case_insensitive_get(self):
        card = self._make_card(method="get")
        check_valid_value(card)


class TestCheckAsyncConf:
    def _make_card(self, async_conf=None) -> RestfulApiCardNew:
        return RestfulApiCardNew(
            id="test",
            name="test",
            path="https://example.com",
            async_conf=async_conf if async_conf is not None else {},
        )

    def test_empty_async_conf_passes(self):
        card = self._make_card(async_conf={})
        check_async_conf(card)

    def test_async_switch_false_passes(self):
        card = self._make_card(async_conf={"async_switch": False})
        check_async_conf(card)

    def test_valid_async_conf(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.example.com/",
                "max_timeout": 300,
                "period_of_round": 5,
            }
        )
        check_async_conf(card)

    def test_non_dict_async_conf_falsy_passes(self):
        card = self._make_card(async_conf=None)
        check_async_conf(card)

    def test_non_dict_async_conf_truthy_raises(self):
        card = self._make_card(async_conf={"async_switch": "yes"})
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be bool" in exc_info.value.message

    def test_async_switch_non_bool_raises(self):
        card = self._make_card(async_conf={"async_switch": "yes"})
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be bool" in exc_info.value.message

    def test_missing_callback_url_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "max_timeout": 300,
                "period_of_round": 5,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be str" in exc_info.value.message

    def test_callback_url_not_str_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": 123,
                "max_timeout": 300,
                "period_of_round": 5,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be str" in exc_info.value.message

    def test_max_timeout_not_int_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": "300",
                "period_of_round": 5,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be int" in exc_info.value.message

    def test_max_timeout_zero_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 0,
                "period_of_round": 5,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be int" in exc_info.value.message

    def test_max_timeout_exceeds_limit_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": PLUGIN_MAX_TIME_OUT + 1,
                "period_of_round": 5,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "between" in exc_info.value.message.lower()

    def test_period_of_round_not_int_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
                "period_of_round": "5",
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be int" in exc_info.value.message

    def test_period_of_round_zero_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
                "period_of_round": 0,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "should be int" in exc_info.value.message

    def test_period_of_round_exceeds_limit_raises(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
                "period_of_round": PLUGIN_MAX_PERIOD_ROUND + 1,
            }
        )
        with pytest.raises(PluginCommonException) as exc_info:
            check_async_conf(card)
        assert "between" in exc_info.value.message.lower()

    def test_default_max_timeout_uses_default(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "period_of_round": 5,
            }
        )
        check_async_conf(card)

    def test_default_period_of_round_uses_default(self):
        card = self._make_card(
            async_conf={
                "async_switch": True,
                "callback_url": "https://cb.com/",
                "max_timeout": 300,
            }
        )
        check_async_conf(card)


class TestExtendAuth:
    def test_returns_auth_unchanged(self):
        auth = {"scope": "SERVICE", "headers": {"X-Key": "val"}}
        result = extend_auth(auth, {})
        assert result == auth

    def test_empty_auth(self):
        result = extend_auth({}, {})
        assert result == {}

    def test_ir_data_not_used(self):
        auth = {"scope": "USER"}
        result = extend_auth(auth, {"extra_key": "extra_val"})
        assert result == auth


class TestLoadRestfulApiFromIr:
    @pytest.mark.asyncio
    async def test_successful_registration(self):
        ir_data = _make_valid_ir_data()
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_resource_mgr = MagicMock()
        mock_resource_mgr.add_tool.return_value = mock_result

        with (
            patch("openjiuwen.core.runner.Runner") as mock_runner,
            patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}),
        ):
            mock_runner.resource_mgr = mock_resource_mgr
            tool_id = load_restful_api_from_ir(ir_data)
            assert tool_id is not None
            mock_resource_mgr.add_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_registration_failure_raises(self):
        ir_data = _make_valid_ir_data()
        mock_result = MagicMock()
        mock_result.is_ok.return_value = False
        mock_result.error.return_value = PluginCommonException(
            code=StatusCode.PLUGIN_ALREADY_EXISTS, message="already exists"
        )
        mock_resource_mgr = MagicMock()
        mock_resource_mgr.add_tool.return_value = mock_result

        with (
            patch("openjiuwen.core.runner.Runner") as mock_runner,
            patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}),
        ):
            mock_runner.resource_mgr = mock_resource_mgr
            with pytest.raises(PluginCommonException):
                load_restful_api_from_ir(ir_data)

    @pytest.mark.asyncio
    async def test_invalid_ir_data_raises(self):
        with pytest.raises(PluginCommonException):
            load_restful_api_from_ir("not a dict")

    @pytest.mark.asyncio
    async def test_registration_with_tag(self):
        ir_data = _make_valid_ir_data()
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_resource_mgr = MagicMock()
        mock_resource_mgr.add_tool.return_value = mock_result

        with (
            patch("openjiuwen.core.runner.Runner") as mock_runner,
            patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}),
        ):
            mock_runner.resource_mgr = mock_resource_mgr
            tool_id = load_restful_api_from_ir(ir_data, tag="agent_test_123")
            assert tool_id is not None
            call_args = mock_resource_mgr.add_tool.call_args
            tag = call_args.kwargs.get("tag")
            assert tag == "agent_test_123"

    @pytest.mark.asyncio
    async def test_registration_without_tag(self):
        ir_data = _make_valid_ir_data()
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_resource_mgr = MagicMock()
        mock_resource_mgr.add_tool.return_value = mock_result

        with (
            patch("openjiuwen.core.runner.Runner") as mock_runner,
            patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}),
        ):
            mock_runner.resource_mgr = mock_resource_mgr
            tool_id = load_restful_api_from_ir(ir_data)
            assert tool_id is not None
            call_args = mock_resource_mgr.add_tool.call_args
            tag = call_args.kwargs.get("tag")
            assert tag is None

    @pytest.mark.asyncio
    async def test_registration_camel_case_input(self):
        ir_data = _make_valid_ir_data(
            pluginDependency={"hook": "test"},
            asyncInvoke={"async_switch": False},
            inputParameters={"key": "value"},
            fileHandler="handler",
        )
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_resource_mgr = MagicMock()
        mock_resource_mgr.add_tool.return_value = mock_result

        with (
            patch("openjiuwen.core.runner.Runner") as mock_runner,
            patch.dict(os.environ, {"PLUGIN_SSL_API_CERT_KEY": "false"}),
        ):
            mock_runner.resource_mgr = mock_resource_mgr
            tool_id = load_restful_api_from_ir(ir_data, tag="agent_camel")
            assert tool_id is not None
            call_args = mock_resource_mgr.add_tool.call_args
            tool = call_args[0][0]
            tag = call_args.kwargs.get("tag")
            assert tool.card.plugin_dependency == {"hook": "test"}
            assert tool.card.input_parameters == {"key": "value"}
            assert tool.card.file_handler == "handler"
            assert tag == "agent_camel"
