# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""
提示词优化任务版本登记去重（issue #1585 / GitHub #1315）单测。

覆盖修改点 1/2：
1. _refine_examples 示例精炼未带来提升（acc_tmp <= acc_base）时不登记新版本（返回 None）；
2. save_state 追加 history 前对候选文本（filled_prompt）与评分（success_rate）完全相同的记录去重兜底。
"""

import math
from unittest.mock import MagicMock, patch

from agent_builder.prompt.tune.base.context import History
from agent_builder.prompt.tune.joint_optimizer import JointOptimizer, _get_history_field


def _make_optimizer(**params_kwargs):
    """构造最小可用 JointOptimizer 实例（参数与辅助方法均为 Mock，不触达模型/评估依赖）"""
    optimizer = JointOptimizer()
    optimizer.params = MagicMock()
    optimizer.params.example_num = 2
    optimizer.params.cot_example_num = 2
    optimizer.params.filled_instruction = "instruction"
    optimizer.params.placeholder = {}
    optimizer.params.base_instruction = "base instruction"
    optimizer.params.examples = []
    optimizer.params.cot_examples = []
    optimizer.params.original_placeholder = []
    for key, value in params_kwargs.items():
        setattr(optimizer.params, key, value)
    optimizer.sampled_incorrect_data = []
    return optimizer


class TestRefineExamplesVersionRecord:
    """修改点 1：示例精炼未采纳不登记新版本"""

    @staticmethod
    def _make():
        return _make_optimizer()

    def test_refine_examples_not_improved_returns_none(self):
        """acc_tmp <= acc_base：示例精炼未提升，不产生新版本记录"""
        optimizer = self._make()
        optimizer.acc_base = 0.8
        optimizer.select_best_examples = MagicMock(return_value=[{"b": 2}])
        optimizer.generate_best_examples = MagicMock(return_value=[{"c": 3}])
        setattr(optimizer, "_prepare_example_strings", MagicMock(return_value="example"))
        setattr(optimizer, "_prepare_examples", MagicMock(return_value=["example"]))
        optimizer.prompt_combine = MagicMock(return_value="full prompt")
        optimizer.eval = MagicMock(return_value=(0.5, [], []))

        result = getattr(optimizer, "_refine_examples")({})

        assert result is None

    def test_refine_examples_improved_returns_history(self):
        """acc_tmp > acc_base：示例精炼带来提升，登记新版本"""
        optimizer = self._make()
        optimizer.acc_base = 0.8
        optimizer.select_best_examples = MagicMock(return_value=[{"b": 2}])
        optimizer.generate_best_examples = MagicMock(return_value=[])
        setattr(optimizer, "_prepare_example_strings", MagicMock(return_value="example"))
        setattr(optimizer, "_prepare_examples", MagicMock(return_value=["example"]))
        optimizer.prompt_combine = MagicMock(return_value="full prompt")
        optimizer.eval = MagicMock(return_value=(0.9, [], []))

        result = getattr(optimizer, "_refine_examples")({})

        assert result is not None
        assert result.filled_prompt == "full prompt"
        assert result.success_rate == 0.9
        assert result.optimized_prompt == "base instruction"


class TestSaveStateDedupe:
    """修改点 2：history 入库去重兜底"""

    @staticmethod
    def _make_optimizer(progress_info, record):
        optimizer = _make_optimizer()
        optimizer.acc_base = 0.8
        optimizer.iter_num = 1
        setattr(optimizer, "_check_event", MagicMock(return_value=True))
        setattr(optimizer, "_prepare_example_strings", MagicMock(return_value=""))
        optimizer.prompt_combine = MagicMock(return_value="full")
        with patch(
            "agent_builder.prompt.tune.joint_optimizer.calc_run_time",
            return_value="00:01:00",
        ), patch(
            "agent_builder.prompt.tune.joint_optimizer.ContextManager"
        ) as mock_context_manager:
            mock_context_manager.return_value.has_store.return_value = False
            optimizer.save_state(progress_info, record)
        return progress_info

    def test_save_state_skips_fully_duplicated_record(self):
        """候选文本（filled_prompt）与评分完全相同的记录不重复追加"""
        record = History(
            optimized_prompt="p",
            filled_prompt="full prompt",
            success_rate=0.8,
            iteration_round=1,
        )
        progress_info = {
            "id": "job1",
            "create_time": "2026-10-29 00:00:00",
            "history": [record],
        }

        result = self._make_optimizer(progress_info, record)

        assert len(result["history"]) == 1

    def test_save_state_appends_distinct_record(self):
        """候选文本不同的记录正常追加"""
        existing = History(
            optimized_prompt="p",
            filled_prompt="full prompt a",
            success_rate=0.8,
            iteration_round=1,
        )
        new_record = History(
            optimized_prompt="p2",
            filled_prompt="full prompt b",
            success_rate=0.9,
            iteration_round=2,
        )
        progress_info = {
            "id": "job1",
            "create_time": "2026-10-29 00:00:00",
            "history": [existing],
        }

        result = self._make_optimizer(progress_info, new_record)

        assert len(result["history"]) == 2
        assert result["history"][-1].filled_prompt == "full prompt b"


class TestHistoryFieldCompat:
    """_get_history_field 兼容 History 对象与 dict 两种形态"""

    @staticmethod
    def _field(item, field_name, default=None):
        return _get_history_field(item, field_name, default)

    def test_get_field_from_history_object(self):
        record = History(optimized_prompt="p", filled_prompt="f", success_rate=0.8)
        assert self._field(record, "filled_prompt") == "f"
        assert math.isclose(self._field(record, "success_rate"), 0.8)

    def test_get_field_from_dict(self):
        record = {"optimized_prompt": "p", "filled_prompt": None}
        assert self._field(record, "filled_prompt") is None
        assert math.isclose(self._field(record, "success_rate", 0.0), 0.0)