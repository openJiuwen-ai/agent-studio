#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""plugin transformer"""

import json
from typing import Union
from urllib.parse import urljoin

from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import load_json
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.plugin.common import constant
from jiuwen.plugin.common import exception
from jiuwen.plugin.common.constant import Status
from jiuwen.plugin.common.exception import ErrorCode
from jiuwen.plugin.common.exception import PluginParamException
from jiuwen.plugin.common.utils.db_mapper import FuncitonInMemory
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.param import Param
from jiuwen.plugin.models.plugin import RestFulAPIPlugin, FunctionPlugin
from jiuwen.plugin.models.restfulapi import RestFulAPI


def from_yaml(yaml_files):
    """
    generate RestfulAPIPlugin list from yaml file list

    Args:
        yaml_files: one yaml file path or yaml file path list with restfulAPI plugin meta information
    Returns:
        List[RestfulAPIPlugin]
    """
    results = []
    return results


def from_json(json_str):
    """
    generate FunctionPlugin list from json format string

    Args:
        json_str: the json format string with function plugin meta information

    Returns:
        List[FunctionPlugin]
    """
    if isinstance(json_str, (str, dict)):
        function_plugin = Transform.get_batch_plugins_from_json_str(json_str)
        return function_plugin
    if isinstance(json_str, list):
        return [Transform.get_batch_plugins_from_json_str(x) for x in json_str]
    logger.error("json_str type error!")
    raise PluginParamException(message="json_str type error")


def convert_openapi3_to_swagger2(openapi_dict):
    """convert openapi 3.* to swagger 2.*"""
    if openapi_dict.get("openapi"):
        openapi_dict["swagger"] = "2.0"
        openapi_dict.pop("openapi")

    if openapi_dict.get(constant.COMPONENTS):
        openapi_dict[constant.DEFINITIONS] = openapi_dict.get(constant.COMPONENTS).get(
            "schemas"
        )
        openapi_dict.pop(constant.COMPONENTS)

    if openapi_dict.get(constant.SERVERS):
        servers = openapi_dict.get(constant.SERVERS)
        if len(servers) > 0:
            openapi_dict["basePath"] = openapi_dict.get(constant.SERVERS)[0].get("url")
        openapi_dict.pop(constant.SERVERS)

    for _, path_content in openapi_dict.get("paths", {}).items():
        for _, method_content in path_content.items():
            if method_content.get(constant.REQUEST_BODY):
                if constant.CONTENT in method_content.get(constant.REQUEST_BODY, {}):
                    method_content["consumes"] = []
                    method_content["parameters"] = []
                    for idx, (media_type, params) in enumerate(
                        method_content.get(constant.REQUEST_BODY, {})
                        .get(constant.CONTENT, {})
                        .items()
                    ):
                        method_content["consumes"].append(media_type)
                        schema = params.get(constant.SCHEMA, {})
                        for k in schema.keys():
                            if k == "$ref":
                                schema[k] = schema[k].replace(
                                    "#/components/schemas", "#/definitions"
                                )
                        method_content["parameters"].append(
                            {
                                constant.NAME: params.get(constant.NAME)
                                if params.get(constant.NAME)
                                else f"name_{idx}",
                                "in": "body",
                                constant.SCHEMA: schema,
                            }
                        )
                method_content.pop(constant.REQUEST_BODY)

            if method_content.get(constant.RESPONSES):
                for _, response_content in method_content.get(
                    constant.RESPONSES, {}
                ).items():
                    if response_content.get(constant.CONTENT):
                        method_content["produces"] = []
                        for media_type, params in response_content.get(
                            constant.CONTENT, {}
                        ).items():
                            method_content["produces"].append(media_type)
                            schema = params.get(constant.SCHEMA, {})
                            for k in schema.keys():
                                if k == "$ref":
                                    schema[k] = schema[k].replace(
                                        "#/components/schemas", "#/definitions"
                                    )
                            response_content[constant.SCHEMA] = schema
                        response_content.pop(constant.CONTENT)


class Transform:
    """Class contains transform operations for plugin"""

    def __init__(self):
        self.attributes = {}

    @staticmethod
    def get_batch_plugins_from_json_str(json_str: Union[dict, str]):
        """get batch plugins from json or json format string"""
        if not isinstance(json_str, (str, dict)):
            logger.error("json str type is error!")
            raise PluginParamException(message="json_str type error")
        plugin = load_json(json_str) if isinstance(json_str, str) else json_str
        if not plugin:
            raise PluginParamException(message="json.loads(json_str) failed")
        if plugin.get("url"):
            return Transform._restful_info_to_plugin(plugin)
        plugin_name = plugin.get(constant.PLUGIN_NAME)
        plugin_description = plugin.get(constant.PLUGIN_DESCRIPTION)
        plugin_dependency = plugin.get("plugin_dependency")
        label = plugin.get("label")
        status = plugin.get("status", Status.private.value)
        function_dict_list = plugin.get("functions") or []
        if not function_dict_list:
            function_dict_list = [plugin]
        function_list = []
        for function_dict in function_dict_list:
            function_dict[constant.PLUGIN_NAME] = plugin_name
            function_dict[constant.PLUGIN_DESCRIPTION] = plugin_description
            function_dict["label"] = label
            function_dict[constant.PLUGIN_ARGUMENTS] = json.dumps(
                function_dict[constant.PLUGIN_ARGUMENTS], ensure_ascii=False
            )
            function_dict["status"] = status
            function = Transform.dict_to_function(function_dict)
            function_list.append(function)
        function_plugin = Transform.format_to_function_plugin(
            functiont_list=function_list,
            name=plugin_name,
            description=plugin_description,
            dependency=plugin_dependency,
        )
        return function_plugin

    @staticmethod
    def dict_to_function(function_dict):
        """convert data (dict) to function"""
        if not isinstance(function_dict, dict):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        params = []
        arguments_list = load_json(function_dict.get("arguments") or "[]")
        for argument in arguments_list:
            argument = {
                field: value
                for field, value in argument.items()
                if value or value is False
            }
            argument.update({"param_type": argument.get("type")})
            params.append(Param(**argument))
        necessary_field = {
            field: value
            for field, value in function_dict.items()
            if value or value is False
        }
        func = function_dict.get("callable_function")
        func_call = FuncitonInMemory().get(func)
        necessary_field.update(
            {
                "plugin_desc": function_dict.get("plugin_description"),
                "name": function_dict.get("func_name"),
                "description": function_dict.get("func_description"),
                "params": params,
                # 去掉cloudpickle以后，可运行程序将从当前运行的缓存中获取，如果缓存不一致将无法运行
                # 因此注解方式的插件每次使用都要重新注册或更新
                "func": func_call if func_call else None,
                "status": function_dict.get("status", Status.private.value),
            }
        )
        return Function(**necessary_field)

    @staticmethod
    def dict_to_restfulapi(plugin):
        """convert data (dict) to restfulapi"""
        if not isinstance(plugin, dict):
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                message=exception.ExceptionsMessage.TypeError,
            )
        params = []
        response = []
        if isinstance(plugin.get(constant.PLUGIN_ARGUMENTS), str):
            arguments_list = load_json(plugin.get(constant.PLUGIN_ARGUMENTS) or "[]")
        else:
            arguments_list = plugin.get(constant.PLUGIN_ARGUMENTS) or []
        for argument in arguments_list:
            necessary_field = {
                field: value
                for field, value in argument.items()
                if value or value is False
            }
            necessary_field.update({"param_type": argument.get("type")})
            params.append(Param(**necessary_field))
        if isinstance(plugin.get(constant.PLUGIN_RESULT), str):
            result_list = load_json(plugin.get(constant.PLUGIN_RESULT) or "[]")
        else:
            result_list = plugin.get(constant.PLUGIN_RESULT) or []
        for result in result_list:
            necessary_field = {
                field: value
                for field, value in result.items()
                if value or value is False
            }
            necessary_field.update({"param_type": result.get("type")})
            response.append(Param(**necessary_field))
        necessary_field = {
            field: value for field, value in plugin.items() if value or value is False
        }
        necessary_field.update(
            {
                "path": plugin.get(constant.PLUGIN_URL),
                "params": params,
                "response": response,
                "name": plugin.get(constant.FUNCTION_NAME),
                "label": plugin.get("label"),
                "description": plugin.get(constant.FUNCTION_DESCRIPTION),
                "plugin_desc": plugin.get(constant.PLUGIN_DESCRIPTION),
                "related_info": plugin.get(constant.PLUGIN_RELATED_INFO),
                "status": plugin.get("status", Status.private.value),
            }
        )
        default_dict_val = "{}"
        if isinstance(plugin.get(constant.PLUGIN_AUTH), str):
            necessary_field[constant.PLUGIN_AUTH] = load_json(
                plugin.get(constant.PLUGIN_AUTH) or default_dict_val
            )
        else:
            necessary_field[constant.PLUGIN_AUTH] = (
                plugin.get(constant.PLUGIN_AUTH) or {}
            )
        if isinstance(plugin.get(constant.PLUGIN_HEADERS), str):
            necessary_field[constant.PLUGIN_HEADERS] = load_json(
                plugin.get(constant.PLUGIN_HEADERS) or default_dict_val
            )
        else:
            necessary_field[constant.PLUGIN_HEADERS] = (
                plugin.get(constant.PLUGIN_HEADERS) or {}
            )
        if isinstance(plugin.get(constant.PLUGIN_DEPENDENCY), str):
            necessary_field[constant.PLUGIN_DEPENDENCY] = load_json(
                plugin.get(constant.PLUGIN_DEPENDENCY) or default_dict_val
            )
        else:
            necessary_field[constant.PLUGIN_DEPENDENCY] = (
                plugin.get(constant.PLUGIN_DEPENDENCY) or {}
            )
        return RestFulAPI(**necessary_field)

    @staticmethod
    def format_to_function_plugin(
        functiont_list: list, name: str, description: str, dependency: str = ""
    ) -> FunctionPlugin:
        """instance FunctionPlugin"""
        function_plugin = FunctionPlugin(
            name=name,
            description=description,
            dependency=dependency,
            native_function_list=functiont_list,
        )
        return function_plugin

    @staticmethod
    def format_to_restful_api_plugin(all_format_api_info):
        """convert format info to restfulapi plugin"""
        ret_plugin = RestFulAPIPlugin(
            name=all_format_api_info[0].get("plugin_name"),
            description=all_format_api_info[0].get("plugin_description"),
        )
        for format_api_info in all_format_api_info:
            restful_api = Transform.dict_to_restfulapi(format_api_info)
            ret_plugin.api_list.append(restful_api)
            ret_plugin.api_map[restful_api.name] = restful_api
        return ret_plugin

    @staticmethod
    def _restful_info_to_plugin(api_info: dict):
        default_val = "default"
        api_info.update(
            {
                constant.PLUGIN_NAME: api_info.get(constant.PLUGIN_NAME, default_val),
                constant.FUNCTION_NAME: api_info.get(
                    constant.FUNCTION_NAME,
                    api_info.get(constant.PLUGIN_NAME, default_val),
                ),
                constant.PLUGIN_DESCRIPTION: api_info.get(
                    constant.PLUGIN_DESCRIPTION, default_val
                ),
                constant.FUNCTION_DESCRIPTION: api_info.get(
                    constant.FUNCTION_DESCRIPTION,
                    api_info.get(constant.PLUGIN_DESCRIPTION, default_val),
                ),
                # 修正，这里应该是headers
                constant.PLUGIN_HEADERS: json.dumps(
                    api_info.get(constant.PLUGIN_HEADERS, {}), ensure_ascii=False
                ),
                constant.PLUGIN_AUTH: json.dumps(
                    api_info.get(constant.PLUGIN_AUTH, {}), ensure_ascii=False
                ),
            }
        )
        if isinstance(api_info.get(constant.PLUGIN_ARGUMENTS), list):
            api_info.update(
                {
                    constant.PLUGIN_ARGUMENTS: json.dumps(
                        api_info.get(constant.PLUGIN_ARGUMENTS) or [],
                        ensure_ascii=False,
                    )
                }
            )
        api = Transform.dict_to_restfulapi(api_info)
        return RestFulAPIPlugin(
            name=api_info.get(constant.PLUGIN_NAME),
            description=api_info.get(constant.PLUGIN_DESCRIPTION),
            api_list=[api],
        )

    @staticmethod
    def _get_api_name_desc(all_api_info, field):
        info = all_api_info.get("info")
        if field not in info:
            logger.error(field + " not in api_info")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: ""}
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: info.get(field)}

    @staticmethod
    def _get_input_path_and_query(parameter):
        """
        requried field
        :param all_api_info:
        :return:
        """
        if constant.NAME not in parameter:
            logger.error("name field is not in input parameter")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        parameter_name = parameter[constant.NAME]
        parameter.pop(constant.NAME)
        parameter.pop("in")
        return {
            constant.RET_CODE: ErrorCode.SUCCESS,
            constant.RESULT: {parameter_name: parameter},
        }

    @staticmethod
    def _format_input(input_info):
        """format input info"""
        format_input = []
        for key, value in input_info["in_body"].items():
            one_input = {"name": key}
            for attr, attr_value in value.items():
                one_input[attr] = attr_value
            format_input.append(one_input)
        return json.dumps(format_input, ensure_ascii=False)

    @staticmethod
    def _format_output(output):
        """format output info"""
        format_output = []
        for key, value in output.items():
            one_output = {"name": key}
            for attr, attr_value in value.items():
                one_output[attr] = attr_value
            if key == "status":
                one_output["default_value"] = 200
            format_output.append(one_output)
        return json.dumps(format_output, ensure_ascii=False)

    @staticmethod
    def _get_headers(all_api_info):
        """get header from all_api_info"""
        info = all_api_info.get("info")
        if "consumes" not in info:
            logger.error("consumes field is not in api_info")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        consumes = info.get("consumes")
        if not (isinstance(consumes, list) and len(consumes) > 0):
            logger.error("consumes field is empty")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        headers = json.dumps({"Content-Type": consumes[0]})
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: headers}

    @staticmethod
    def _get_input_body(parameter):
        """
        requried field
        :param all_api_info:
        :return:
        """
        if "schema" not in parameter:
            logger.error("schema field is not in input parameter")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: None}

    def extract_api_info(self, paths, definitions, base_path):
        """extract api info from yaml"""
        execute_dict = {
            constant.PLUGIN_NAME: self._get_plugin_name,
            constant.PLUGIN_DESCRIPTION: self._get_plugin_description,
            constant.FUNCTION_NAME: self._get_api_name,
            constant.FUNCTION_DESCRIPTION: self._get_api_description,
            constant.PLUGIN_ARGUMENTS: self._get_input,
            constant.PLUGIN_RESULT: self._get_output,
            constant.PLUGIN_HEADERS: self._get_headers,
            constant.PLUGIN_AUTH: self._get_auth,
        }
        all_format_api_info = []
        error_format_api_info = []
        for url, restful_info in paths.items():
            for method, info in restful_info.items():
                format_api_info = {
                    "url": urljoin(base_path, url),
                    "method": method,
                    "label": info.get("label", "common"),
                    "principle": "unknow",
                }
                for name, func in execute_dict.items():
                    res = func(
                        {
                            "url": urljoin(base_path, url),
                            "method": method,
                            "info": info,
                            "definitions": definitions,
                        }
                    )
                    if res.get(constant.RET_CODE) == ErrorCode.UNEXPECTED_ERROR:
                        logger.info("%s get error", name)
                        error_format_api_info.append(
                            {constant.PLUGIN_URL: url, constant.PLUGIN_METHOD: method}
                        )
                        format_api_info.clear()
                        break
                    format_api_info[name] = res.get(constant.RESULT)
                if format_api_info:
                    all_format_api_info.append(format_api_info)
        return all_format_api_info, error_format_api_info

    def _get_plugin_name_desc(self, field):
        if "info" not in self.attributes:
            logger.error("info not in attributes")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: ""}
        info = self.attributes.get("info")
        if field not in info:
            logger.error(field + " not in info")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: ""}
        res = info.get(field)
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: res}

    def _get_plugin_name(self, all_api_info):
        """
        required
        :param all_api_info:
        :return:
        """
        return self._get_plugin_name_desc("title")

    def _get_plugin_description(self, all_api_info):
        """
        required
        :param all_api_info:
        :return:
        """
        return self._get_plugin_name_desc("description")

    def _get_api_name(self, all_api_info):
        """
        required
        :param all_api_info: api_info
        :return:
        """
        return self._get_api_name_desc(all_api_info, "operationId")

    def _get_api_description(self, all_api_info):
        """
        required
        :param all_api_info: api_info
        :return:
        """
        return self._get_api_name_desc(all_api_info, "description")

    def _get_input(self, all_api_info):
        """
        requried
        :param all_api_info:
        :return:
        """
        info = all_api_info.get("info")
        parameters = info.get("parameters", [])
        in_path = {}
        in_query = {}
        in_body = {}
        param_in = "in"
        for parameter in parameters:
            if parameter.get(param_in, "") == "path":
                res = self._get_input_path_and_query(parameter)
                if res.get(constant.RET_CODE) == ErrorCode.UNEXPECTED_ERROR:
                    return {
                        constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR,
                        constant.RESULT: {},
                    }
                in_path.update(res.get(constant.RESULT))
            if parameter.get(param_in, "") == "query":
                res = self._get_input_path_and_query(parameter)
                if res.get(constant.RET_CODE) == ErrorCode.UNEXPECTED_ERROR:
                    return {
                        constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR,
                        constant.RESULT: {},
                    }
                in_path.update(res.get(constant.RESULT))
            if parameter.get(param_in, "") == "body":
                res = self._get_input_body(parameter)
                if res.get(constant.RET_CODE) == ErrorCode.UNEXPECTED_ERROR:
                    return {
                        constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR,
                        constant.RESULT: {},
                    }
                in_body.update(res.get(constant.RESULT))
        input_info = {"in_path": in_path, "in_query": in_query, "in_body": in_body}
        format_input = self._format_input(input_info)

        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: format_input}

    def _get_output(self, all_api_info):
        """
        requried
        :param all_api_info:
        :return:
        """
        info = all_api_info.get("info")
        if "responses" not in info:
            logger.error("responses field is not in api_info")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        responses = info.get("responses")
        if 200 not in responses and "200" not in responses:
            logger.error("'200' field is not in responses")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        if responses.get(200):
            success_responses = responses.get(200)
        else:
            success_responses = responses.get("200")
        if "schema" not in success_responses:
            logger.error("schema field is not in success_responses")
            return {constant.RET_CODE: ErrorCode.UNEXPECTED_ERROR, constant.RESULT: {}}
        success_responses_schema = success_responses.get("schema")
        format_output = self._format_output(success_responses_schema)
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: format_output}

    def _get_auth(self, all_api_info):
        if "auth" not in self.attributes:
            logger.info("auth not in info")
            return {
                constant.RET_CODE: ErrorCode.SUCCESS,
                constant.RESULT: json.dumps({}),
            }
        auth = self.attributes.get("auth")
        return {constant.RET_CODE: ErrorCode.SUCCESS, constant.RESULT: json.dumps(auth)}
