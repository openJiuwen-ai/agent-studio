# -*- coding: UTF-8 -*-
"""OTel 载荷键一致性守护（issue #1583 第 7 节）。

llm_chain 为避免工作流节点模块背上 planner 的导入链（psycopg2 等原生
依赖），本地定义了 USAGE_METADATA / FINISH_REASON 常量；本测试守护其
取值与 planner 侧 stream_post_utils 的同名常量严格一致（handler 按这
两个键取用量/结束原因，漂移即载荷失效）。
"""

from jiuwen.extension.workflow_node import llm_chain as llm_chain_module
from jiuwen.planner.common.stream_post_utils import FINISH_REASON, USAGE_METADATA


class TestPayloadKeyParity:
    @staticmethod
    def test_llm_chain_keys_match_stream_post_utils():
        assert llm_chain_module.USAGE_METADATA == USAGE_METADATA == "usage_metadata"
        assert llm_chain_module.FINISH_REASON == FINISH_REASON == "finish_reason"
