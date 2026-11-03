#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2026

"""锁行为测试：开始节点 file 参数以 URL 方式录入后，run 侧解析行为不变。

背景: 特性「开始节点支持URL方式」仅在前端新增 URL 录入模式，前端将
file 参数值组织为与本地上传完全一致的值契约：
- 单文件（file/image、file/video 等）: 值 = URL 字符串，节点配置类型 string
- 多文件（array<file/image> 等）: 值 = URL 字符串数组，节点配置类型 array，
  经 HTTP 传输可能以 JSON 字符串形态到达

后端 FlowInputUtils.validate_inputs 无需感知 URL。本测试锁定其既有行为：
URL 值经过校验后原样透传，不被改写、不抛错；必填校验语义不变。

测试覆盖:
1. type=string: URL 字符串原样保留（含预签名 query、data: URI）。
2. type=array: 真实 list 形态的 URL 数组原样保留。
3. type=array: JSON 字符串形态被解析为 list（与旧上传路径行为一致）。
4. 必填校验仍生效: required 字段缺失/为空仍抛输入参数错误。
"""

import json

import pytest

from jiuwen.extension.workflow_node.flow_input import FlowInputUtils


def _config(inputs_config: list) -> dict:
    return {"userFields": {"inputs": inputs_config}}


URL_HTTPS = (
    "https://minio.example.com/bucket/%E6%8A%93%E6%8B%8D.png"
    "?X-Amz-Signature=abc123"
)
URL_DATA = "data:image/png;base64,iVBORw0KGgo="


class TestValidateInputsUrlPassthrough:
    """URL 值经 validate_inputs 后原样透传（锁行为）。"""

    @staticmethod
    def test_string_url_passthrough_unchanged():
        config = _config([{"id": "photo", "required": True, "type": "string"}])
        inputs = {"photo": URL_HTTPS}
        FlowInputUtils.validate_inputs(inputs, config)
        assert inputs["photo"] == URL_HTTPS

    @staticmethod
    def test_string_data_uri_passthrough_unchanged():
        config = _config([{"id": "photo", "required": False, "type": "string"}])
        inputs = {"photo": URL_DATA}
        FlowInputUtils.validate_inputs(inputs, config)
        assert inputs["photo"] == URL_DATA

    @staticmethod
    def test_array_real_list_passthrough_unchanged():
        config = _config([{"id": "photos", "required": True, "type": "array"}])
        urls = [URL_HTTPS, "http://example.com/a.mp4", URL_DATA]
        inputs = {"photos": list(urls)}
        FlowInputUtils.validate_inputs(inputs, config)
        assert inputs["photos"] == urls

    @staticmethod
    def test_array_json_string_form_parsed_to_list():
        config = _config([{"id": "photos", "required": True, "type": "array"}])
        urls = [URL_HTTPS, URL_DATA]
        inputs = {"photos": json.dumps(urls)}
        FlowInputUtils.validate_inputs(inputs, config)
        assert inputs["photos"] == urls


class TestValidateInputsRequiredSemanticsUnchanged:
    """必填校验语义不受 URL 录入影响（锁行为）。"""

    @staticmethod
    def test_required_missing_still_raises():
        config = _config([{"id": "photo", "required": True, "type": "string"}])
        with pytest.raises(Exception):
            FlowInputUtils.validate_inputs({}, config)

    @staticmethod
    def test_required_empty_still_raises():
        config = _config([{"id": "photo", "required": True, "type": "string"}])
        with pytest.raises(Exception):
            FlowInputUtils.validate_inputs({"photo": ""}, config)
