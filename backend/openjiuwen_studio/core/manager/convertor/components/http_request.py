#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.schemas.node import Node, BaseValue
from openjiuwen_studio.core.manager.convertor.components.common import (
    input_params_convert,
    exception_config_convert,
    base_value_convert,
)
from openjiuwen_studio.core.common.dsl import ComponentType


def _http_request_params_convert(params_dict) -> List[dsl.HttpRequestParamConfig]:
    """Convert frontend key-value params dict to list of param configs"""
    if not params_dict:
        return []

    params = []
    for key, value in params_dict.items():
        # Handle BaseValue conversion
        param_value = base_value_convert(value) if isinstance(value, BaseValue) else value
        params.append(dsl.HttpRequestParamConfig(key=key, value=param_value))

    return params


def _http_request_config_convert(node: Node) -> dsl.HttpRequestConfig:
    """Convert node data to HTTP request config"""
    data = node.data
    inputs = data.inputs
    exception_conf = data.exception_config

    if inputs is None:
        raise TypeError("inputs is none")

    if inputs.input_parameters is None:
        raise TypeError("input_parameters is none")

    if exception_conf is None:
        raise TypeError("exception config is none")

    input_params = inputs.input_parameters

    # Extract method from inputs (separate from inputParameters)
    # Method is stored as inputs.method, not in inputParameters
    method_param = getattr(inputs, 'method', None)
    logger.info(f"HTTP Request Converter - method_param: {method_param}")
    if method_param is None:
        raise TypeError("method parameter is missing")

    # Extract values from inputParameters (each is a BaseValue)
    url_param = input_params.get("url")
    headers_param = input_params.get("headers")
    query_params_param = input_params.get("query")
    body_param = input_params.get("body")
    auth_param = input_params.get("auth")

    logger.info(f"HTTP Request Converter - url_param: {url_param}")
    if url_param is None:
        raise TypeError("url parameter is missing")

    # Convert BaseValue to actual values
    url = base_value_convert(url_param)
    method = base_value_convert(method_param)
    logger.info(f"HTTP Request Converter - converted URL: {url}, Method: {method}")
    headers = base_value_convert(headers_param) if headers_param else {}
    query_params = base_value_convert(query_params_param) if query_params_param else {}
    body = base_value_convert(body_param) if body_param else None
    auth = base_value_convert(auth_param) if auth_param else {"type": "none"}

    # Convert headers and query_params from dict to list of HttpRequestParamConfig
    headers_list = _http_request_params_convert(headers)
    query_params_list = _http_request_params_convert(query_params)

    # Create auth config from dict
    auth_config = dsl.HttpAuthConfig(
        auth_type=dsl.HttpAuthType(auth.get("type", "none")),
        username=auth.get("username", ""),
        password=auth.get("password", ""),
        token=auth.get("token", ""),
        api_key=auth.get("api_key", ""),
        api_key_location=auth.get("api_key_location", "header"),
        api_key_param_name=auth.get("api_key_param_name", "X-API-Key"),
    )

    # Create body config if body exists
    body_config = None
    if body is not None:
        # Body can be a dict with content_type and content, or just the content itself
        if isinstance(body, dict) and "content_type" in body:
            body_config = dsl.HttpRequestBodyConfig(
                content_type=dsl.HttpContentType(body.get("content_type", "application/json")),
                content=body.get("content"),
            )
        else:
            # Default to JSON content type
            body_config = dsl.HttpRequestBodyConfig(
                content_type=dsl.HttpContentType("application/json"),
                content=body,
            )

    # Use default values for response handling, retry, rate limit, and advanced options
    # These can be extended later if needed in the UI
    response_handling = dsl.HttpResponseHandlingConfig(
        response_format=dsl.HttpResponseFormat(dsl.HttpResponseFormat.AUTO),
        success_status_codes=[200, 201, 202, 204],
        failure_status_codes=[],
        response_mode="full",
        data_property=None,
    )

    retry_config = dsl.HttpRetryConfig(
        enabled=False,
        max_retries=3,
        retry_on_status_codes=[429, 500, 502, 503, 504],
        retry_delay_ms=1000,
        backoff_type=dsl.BackoffType("exponential"),
    )

    rate_limit_config = dsl.HttpRateLimitConfig(
        enabled=False,
        requests_per_unit=10,
        unit="minute",
    )

    advanced_config = dsl.HttpAdvancedOptionsConfig(
        follow_redirects=True,
        ignore_ssl_issues=False,
        proxy_url=None,
        timeout=60,
    )

    return dsl.HttpRequestConfig(
        url=url,
        method=dsl.HttpMethod(method),
        headers=headers_list,
        query_params=query_params_list,
        body=body_config,
        auth=auth_config,
        response_handling=response_handling,
        retry=retry_config,
        rate_limit=rate_limit_config,
        advanced=advanced_config,
        exception_config=exception_config_convert(exception_conf),
    )


def http_request_convert(node: Node) -> dsl.Component:
    """Convert HTTP request node to DSL Component"""
    try:
        logger.info(f"HTTP Request Converter - Starting conversion for node: {node.id}")
        data = node.data
        inputs = data.inputs

        if inputs is None:
            raise TypeError("inputs is none")

        input_parameters = inputs.input_parameters
        if input_parameters is None:
            input_parameters = {}

        convert_inputs = input_params_convert(input_parameters)

        component = dsl.Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_HTTP_REQUEST,
            type_version="1.0.0",
            description="",
            inputs=convert_inputs,
            configs=_http_request_config_convert(node).model_dump(),
            name=data.title,
        )
        logger.info(f"HTTP Request Converter - Successfully converted node: {node.id}")
        return component
    except Exception as e:
        logger.error(f"HTTP Request Converter - Failed to convert node {node.id}: {str(e)}")
        raise RuntimeError(f"Failed to convert HTTP request node: {str(e)}") from e
