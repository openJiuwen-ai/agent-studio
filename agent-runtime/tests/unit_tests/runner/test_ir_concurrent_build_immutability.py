# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""R-02 §9.2: IR 并发构建不变性测试。

修复后 adapter 只存只读 ir_data,invoke() 每次自建 LazyWorkflow。同一份 IR
被并发构建时必须满足:
- 原始 IR dict 内容不被修改(COW / 纯函数式 build);
- 各次构建得到不同的 LazyWorkflow 与不同的可执行 Workflow 实例。

坐实"复用 sub_ir 并发 rebuild 安全"——非仅依赖 docstring,而是实测。
"""

import asyncio
import copy
import json
from pathlib import Path

import pytest

IR_PATH = Path(__file__).resolve().parents[2] / "resource" / "ir_file" / "workflow_message.json"


class TestIRConcurrentBuildImmutability:
    """同一份 IR 并发构建:原始内容不变,各构建得到独立实例。"""

    @pytest.mark.asyncio
    async def test_concurrent_build_leaves_ir_unchanged_and_yields_distinct_instances(self):
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        snapshot = copy.deepcopy(ir_data)

        lazy_a, lazy_b = await asyncio.gather(
            IRConverter.async_ir_to_workflow(ir_data),
            IRConverter.async_ir_to_workflow(ir_data),
        )
        wf_a, wf_b = await asyncio.gather(lazy_a.instantiate(), lazy_b.instantiate())

        # 原始 IR 未被任何一次构建修改
        assert ir_data == snapshot
        # 两个 LazyWorkflow shell 不同
        assert lazy_a is not lazy_b
        # 两个底层可执行 Workflow 实例不同(各自的 _graph/_session 独立)
        assert wf_a is not wf_b

    @pytest.mark.asyncio
    async def test_single_ir_repeated_build_is_stable(self):
        """同一份 IR 连续构建两次,结果稳定、IR 不变(顺序版,补充并发版)。"""
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        ir_data = json.loads(IR_PATH.read_text(encoding="utf-8"))
        snapshot = copy.deepcopy(ir_data)

        lazy_a = await IRConverter.async_ir_to_workflow(ir_data)
        lazy_b = await IRConverter.async_ir_to_workflow(ir_data)
        wf_a = await lazy_a.instantiate()
        wf_b = await lazy_b.instantiate()

        assert ir_data == snapshot
        assert wf_a is not wf_b
