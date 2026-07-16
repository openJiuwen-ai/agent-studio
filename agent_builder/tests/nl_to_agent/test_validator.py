#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""validator 模块单元测试"""

import json
import os
from unittest.mock import patch

import pytest
from agent_builder.nl_to_agent.common.validator import (
    AgentModelInfoValidator,
    TaskParamsValidationException,
    validate_parameter,
)


class TestValidateParameter:
    """validate_parameter 函数测试"""

    @staticmethod
    def test_required_param_present():
        params = {"name": "test", "age": 10}
        result = validate_parameter(params, "name", str)
        assert result == "test"

    @staticmethod
    def test_required_param_present_int_type():
        params = {"age": 10}
        result = validate_parameter(params, "age", int)
        assert result == 10

    @staticmethod
    def test_required_param_missing_raises():
        params = {"name": "test"}
        with pytest.raises(TaskParamsValidationException):
            validate_parameter(params, "missing_key", str)

    @staticmethod
    def test_wrong_type_raises():
        params = {"age": "not_int"}
        with pytest.raises(TaskParamsValidationException):
            validate_parameter(params, "age", int)

    @staticmethod
    def test_optional_param_missing_returns_none():
        params = {"name": "test"}
        result = validate_parameter(params, "missing_key", str, required=False)
        assert result is None

    @staticmethod
    def test_optional_param_present_returns_value():
        params = {"name": "test"}
        result = validate_parameter(params, "name", str, required=False)
        assert result == "test"

    @staticmethod
    def test_empty_params_raises():
        with pytest.raises(TaskParamsValidationException):
            validate_parameter({}, "key", str)

    @staticmethod
    def test_none_params_raises():
        with pytest.raises(TaskParamsValidationException):
            validate_parameter(None, "key", str)

    @staticmethod
    def test_dict_type_param():
        params = {"config": {"a": 1}}
        result = validate_parameter(params, "config", dict)
        assert result == {"a": 1}

    @staticmethod
    def test_list_type_param():
        params = {"items": [1, 2, 3]}
        result = validate_parameter(params, "items", list)
        assert result == [1, 2, 3]


class TestAgentModelInfoValidator:
    """AgentModelInfoValidator 类测试"""

    @staticmethod
    def _make_default_models_env():
        return json.dumps({"nl2_agentBuilder_model": {"test-model": True}})

    @staticmethod
    def test_valid_model_info():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "test-model",
                    "model_source": "nl2_agentBuilder_model",
                }
            }
            AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_missing_model_field_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model_source": "nl2_agentBuilder_model",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_missing_model_source_field_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "test-model",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_empty_model_string_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "  ",
                    "model_source": "nl2_agentBuilder_model",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_empty_model_source_string_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "test-model",
                    "model_source": "  ",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_missing_model_info_field_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {}
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_wrong_model_source_value_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "test-model",
                    "model_source": "invalid_source",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_wrong_model_value_raises():
        with patch.dict(os.environ, {"DEFAULT_MODELS": TestAgentModelInfoValidator._make_default_models_env()}):
            params = {
                "modelInfo": {
                    "model": "nonexistent-model",
                    "model_source": "nl2_agentBuilder_model",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)

    @staticmethod
    def test_no_default_models_env():
        with patch.dict(os.environ, {"DEFAULT_MODELS": "{}"}, clear=False):
            params = {
                "modelInfo": {
                    "model": "test-model",
                    "model_source": "nl2_agentBuilder_model",
                }
            }
            with pytest.raises(TaskParamsValidationException):
                AgentModelInfoValidator.validate_model_info(params)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
