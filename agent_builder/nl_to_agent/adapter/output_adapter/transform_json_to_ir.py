# 永久性覆盖重写九问agent_builder代码中DSL模型相关内容
# 增加了多个函数参数，将请求体的模型信息传入框架内的modelConfig实现模型配置运行时修改
# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import json
import random
import string
from dataclasses import asdict

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.adapter.exception_bridge import JiuWenBaseException

from .transform_ir_for_cloud import ConvertToEicloud


class TransformJsonToIr:
    """用于将输入的 JSON 数据转换为 eicloud IR（中间表示）格式的工具类。

    该类提供静态方法，主要用于调用转换器 `ConvertToEicloud` 对原始
    JSON 数据进行结构化处理，并返回符合 eicloud 规范的 IR 字符串。

    Note:
        这是一个工具类，不需要实例化，直接通过静态方法调用即可。
    """

    @staticmethod
    def transform_cloud_ir(input_json, plugin_dict, workflow_dict, model_dict):
        """将输入的 JSON 转换为 cloud IR 格式。

        内部会调用 `ConvertToEiCloud` 执行数据转换，并将结果对象
        转换为 JSON 字符串输出。

        Args:
            input_json (dict): 输入的原始 JSON 数据。
            plugin_dict: 插件信息字典

        Returns:
            str: 转换后的 cloud IR 字符串。
        """
        try:
            con = ConvertToEicloud(
                original_data=input_json,
                plugin_dict=plugin_dict,
                workflow_dict=workflow_dict,
                model_dict=model_dict,
            )
            con.convert()
            return json.dumps(asdict(con.convert_res), ensure_ascii=False)
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.NL2AGENT_TRANSFORM_IR_TO_EICLOUD_ERROR.code,
                StatusCode.NL2AGENT_TRANSFORM_IR_TO_EICLOUD_ERROR.errmsg.format(
                    error_msg=f"IR conversion failed：{str(e)}"
                ),
            ) from e

    @staticmethod
    def build_agent_json(name, name_en, description, ir):
        """构建包含中英文名称与描述的 JSON。

        Args:
            name (dict): 中文名称。
            name_en (dict): 英文名称。
            description (dict): 描述。
            ir (str): Cloud IR 字符串。

        Returns:
            str: 转换后的 json 字符串。
        """
        return json.dumps(
            {
                "name": f"{name}_{TransformJsonToIr._random_8()}",
                "name_en": f"{name_en}_{TransformJsonToIr._random_8()}",
                "description": description,
                "ir": ir,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _random_8():
        chars = string.ascii_lowercase + string.digits
        return random.choice(string.ascii_lowercase) + "".join(
            random.choices(chars, k=7)
        )
