#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: s60041331
# @Time: 2025/5/8 10:30
# @FILE: test_case_agent_controller_add_01.py
# 版权所有 (c) 华为技术有限公司 2012-2020
"""
指定工作流顺序，全局意图 handler 是 Workflow，action_after_completion=Continue
"""

__all__ = ["TestCaseAgentControllerAdd01"]

import json
import os
import unittest

import pytest
from common.aw.jiuwen_server_aw import TestJiuWenServer
from common.utils_aw.obs_upload import obs_upload
from common.utils_aw.update_ir import update_controller_ir_path


class TestCaseAgentControllerAdd01(TestJiuWenServer):
    @classmethod
    def setUpClass(cls, case_name=None, case_path=None) -> None:
        super().setUpClass(
            case_name=cls().__class__.__name__,
            case_path=os.path.dirname(os.path.abspath(__file__)),
        )

    def setUp(self):
        super().setUp()

    @pytest.mark.level0
    @pytest.mark.huaweicloud
    @pytest.mark.python
    @pytest.mark.flaky(reruns=5, reruns_delay=2)
    @pytest.mark.s60041331
    def test_run(self):
        """
        #!+================================================================
        # @level: level 0
        # @CaseID: test_case_agent_controller_add_01.py
        # @Description: 指定工作流顺序，全局意图 handler 是 Workflow，action_after_completion=Continue
        # @Step:
            测试方法：
            1.流程控制模式下，添加开始工作流和结束工作流，以及一条业务工作流，添加的业务工作流中要包含意图识别组件；
            2. 配置 1 条全局意图，全局意图的 handlerType 是 Workflow，action_after_completion是Continue；
            3.对话要能引导在执行到意图识别组件时跳转到全局意图；
        # @Result:
          1. 按如下顺序执行工作流：开始工作流-天天盈工作流-触发全局意图工作流-天天盈工作流-结束工作流。
        #!!================================================================
        """

        # 读取agent和workflow路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fp = os.path.basename(__file__).split(".py")[0]
        agent = os.listdir(os.path.join(current_dir, fp, "agent"))[0]
        workflows = [
            f
            for f in os.listdir(os.path.join(current_dir, fp, "workflow"))
            if os.path.isfile(
                os.path.join(os.path.join(current_dir, fp, "workflow"), f)
            )
        ]

        # 读取并上传workflow
        workflow_ir_dict = {}
        for workflow in workflows:
            ir_path = f"workflow/ir/{fp}/{workflow}"
            with open(f"{current_dir}/{fp}/workflow/{workflow}", encoding="utf-8") as f:
                ir_json = json.load(f)
            obs_upload(
                ir_path,
                json.dumps(ir_json, ensure_ascii=False, indent=4),
                self.obs_dict,
            )
            workflow_ir_dict[workflow.split(".json")[0]] = (
                ir_path  # 用于更新agentIR中的workflow路径
            )

        # 修改并上传agent
        ir_path = f"agent/ir/{fp}/{fp}.json"
        with open(f"{current_dir}/{fp}/agent/{agent}", encoding="utf-8") as f:
            ir_json = json.load(f)
        update_controller_ir_path(ir_json, workflow_ir_dict)
        obs_upload(
            ir_path, json.dumps(ir_json, ensure_ascii=False, indent=4), self.obs_dict
        )

        # defer 预清理上传的obs文件
        self.ir_delete_path = list(workflow_ir_dict.values())
        self.ir_delete_path.append(ir_path)

        # 流式执行
        params = {
            "conversationHistory": [],
            "pluginConfigs": [],
            "globalVariables": {"name": "tom"},
            "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
            "workflowSequence": ["1f4c4496-0511-4367-a1bd-15d74d12ab0a"],
            "activeWorkflows": [],
        }

        talks = [
            {
                "query": "你好",
                "answer": [
                    "【开始工作流】你好",
                    "你好",
                    "#########我行天天盈换新升级，新增余额自动购买及自动快赎，产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，稍后我把产品介绍以短信形式发送给您？",
                ],
            },
            {
                "query": "是本人，我要投诉",
                "answer": ["非常抱歉给您带来困扰。祝您生活愉快，再见！"],
            },
            {
                "query": "不投诉了",
                "answer": [
                    "投诉，结束",
                    "#########我行天天盈换新升级，新增余额自动购买及自动快赎，产品扩容到58只底层货币基金，普通赎 回到账时间最快提速约半天，稍后我把产品介绍以短信形式发送给您？",
                ],
            },
            {
                "query": "我对天天盈感兴趣",
                "answer": [
                    "用户表示感兴趣，给出天天盈介绍",
                    "【这是天天盈工作流的结束节点】天天盈结束",
                    "【结束工作流】我对天天盈感兴趣",
                    "我对天天盈感兴趣",
                ],
            },
        ]

        self.ir_executes(self.conversation_id, talks, ir_path, params=params)


if __name__ == "__main__":
    unittest.main()
