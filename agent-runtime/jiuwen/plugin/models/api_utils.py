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


# 插件/MCP 参数松校验开关（PLUGIN_MCP_LOOSE_PARAM_VALIDATION，默认关闭）。
# 开启后对齐旧架构（lumina / 旧线 ei_patch 覆盖形态）的行为：调用入参出现
# 未定义参数名时不再抛错，仅记日志并静默跳过，插件/MCP 照常被调用——
# 用于旧架构现网向新架构迁移期间的兼容模式（旧架构现网对未知参数本就宽容）。
_LOOSE_PARAM_VALIDATION_ENV = "PLUGIN_MCP_LOOSE_PARAM_VALIDATION"


def is_loose_param_validation_enabled() -> bool:
    """插件/MCP 参数松校验是否开启。

    环境变量 ``PLUGIN_MCP_LOOSE_PARAM_VALIDATION`` 为 true（大小写不敏感、
    允许首尾空白）时开启；未设置或其他值一律关闭（默认严格校验：
    未定义参数名抛 WORKFLOW_API_INPUTS_ERROR / WORKFLOW_MCP_INPUTS_ERROR）。
    每次调用实时读取环境变量，改值即时生效（无需重启进程）——评审修订
    2026-11-04：删除与此矛盾的"须重启"表述。
    """
    return str(os.getenv(_LOOSE_PARAM_VALIDATION_ENV, "")).strip().lower() == "true"


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
