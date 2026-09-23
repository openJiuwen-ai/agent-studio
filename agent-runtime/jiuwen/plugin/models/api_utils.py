#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import importlib
import os

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.security.cryptor import Crypt
from jiuwen.plugin.common import constant


def transform_type(value, expected_type, key):
    """转换数据类型"""
    if expected_type.lower() == "string":
        try:
            str_res = str(value)
        except ValueError as e:
            base_err_msg = StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.errmsg
            message = f"{base_err_msg},expected_type is {expected_type}"
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.code,
                message=message,
            ) from e
        return str_res
    if expected_type.lower() == "boolean":
        try:
            bool_res = bool(value)
        except ValueError as e:
            base_err_msg = StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.errmsg
            message = f"{base_err_msg},expected_type is {expected_type}"
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.code,
                message=message,
            ) from e
        return bool_res
    if expected_type.lower() == "integer":
        try:
            int_res = int(value)
        except (
            TypeError,
            ValueError,
        ) as e:  # expected_type为integer或者number时，如果value为复杂类型则可能报TypeError
            base_err_msg = StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.errmsg
            message = f"{base_err_msg},expected_type is {expected_type}"
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.code,
                message=message,
            ) from e
        return int_res
    if expected_type.lower() == "number":
        try:
            float_res = float(value)
        except (
            TypeError,
            ValueError,
        ) as e:  # expected_type为integer或者number时，如果value为复杂类型则可能报TypeError
            base_err_msg = StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.errmsg
            message = f"{base_err_msg},expected_type is {expected_type}"
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_API_PARAMS_CHECK_ERROR.code,
                message=message,
            ) from e
        return float_res
    return value


class ApiUtils:
    @staticmethod
    def encrypt_service_auth(auth: dict):
        """针对Service级鉴权中的str value 进行加密"""
        if not auth:
            return {}
        # 已经做过加密
        if auth.get(constant.AUTH_CRYPT_METHOD, None):
            return auth
        # 当前只针对AUTH_SERVICE进行加解密
        if auth.get(constant.AUTH_SCOPE, "") != constant.AUTH_SERVICE:
            return auth
        curr_work_api = Crypt()
        crypt_auth = ApiUtils.crypt_dict(auth, curr_work_api.encrypt)
        crypt_auth.update({"crypt_method": "jiuwen"})
        return crypt_auth

    @staticmethod
    def decrypt_service_auth(auth: dict):
        """针对Service级鉴权中的str value 进行解密"""
        # 没有加密的直接返回
        if not auth.get(constant.AUTH_CRYPT_METHOD, None):
            return auth
        # 当前只针对AUTH_SERVICE进行加解密
        if auth.get(constant.AUTH_SCOPE, "") != constant.AUTH_SERVICE:
            return auth
        curr_work_api = Crypt()
        crypt_auth = ApiUtils.crypt_dict(auth, curr_work_api.decrypt)
        # 解密完成删除标识字段
        crypt_auth.pop(constant.AUTH_CRYPT_METHOD, None)
        return crypt_auth

    @staticmethod
    def crypt_dict(auth, function):
        """对dict中的第二层级中的str value做加解密"""
        crypt_auth = {}
        for key, item in auth.items():
            if not isinstance(item, dict):
                crypt_auth[key] = item
                continue
            new_data = {}
            for token_key, token in item.items():
                if not isinstance(token, str):
                    new_data[token_key] = token
                else:
                    data = function(token)
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    new_data[token_key] = data
            crypt_auth[key] = new_data
        return crypt_auth

    @classmethod
    def get_hook_func(cls, plugin_hook_function):
        """
        获取钩子函数
        """
        file_path, function_name = plugin_hook_function.rsplit(":", 1)
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        hook_provider = getattr(module, function_name)
        return hook_provider
