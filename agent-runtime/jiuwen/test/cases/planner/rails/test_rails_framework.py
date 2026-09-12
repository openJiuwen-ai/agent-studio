# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""Test Rails Framework - 核心功能测试"""

import os
from unittest import TestCase

from jiuwen.planner.rails.common.decorator import action
from jiuwen.planner.rails.config import RailsConfig, ActionConfig
from jiuwen.planner.rails.rails.execution_rails import ExecutionRails
from jiuwen.planner.rails.rails.input_rails import InputRails
from jiuwen.planner.rails.rails_factory import RailsFactory
from jiuwen.planner.rails.runtime.action_manager import ActionManagerSingleton
from jiuwen.planner.rails.runtime.context import RailsContext


class TestRailsFramework(TestCase):
    """Rails护栏框架核心功能测试"""

    def setUp(self):
        from jiuwen.test.cases.planner.rails.custom_action_config.actions import (
            mock_action,
            mock_action_append,
            mock_execution_action,
        )

        mock_action()
        mock_action_append()
        mock_execution_action()

    def test_rails_factory_create_input_rails(self):
        """测试RailsFactory创建InputRails实例"""
        config_dict = {"rails": {"input": [{"action": "mock_action"}]}}
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)

        input_rails = factory.get_input_rails()

        self.assertIsInstance(input_rails, InputRails)

    def test_rails_factory_create_execution_rails(self):
        """测试RailsFactory创建ExecutionRails实例"""
        config_dict = {"rails": {"execution": [{"action": "mock_execution_action"}]}}
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)

        execution_rails = factory.get_execution_rails()

        self.assertIsInstance(execution_rails, ExecutionRails)

    def test_input_rails_invoke_single_action(self):
        """测试InputRails执行单个Action"""
        config_dict = {"rails": {"input": [{"action": "mock_action"}]}}
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)
        input_rails = factory.get_input_rails()

        result = input_rails.invoke({"query": "原始query"})

        self.assertEqual(result.get("query"), "更新后的query")

    def test_input_rails_invoke_chained_actions(self):
        """测试InputRails链式执行多个Action"""
        config_dict = {
            "rails": {
                "input": [{"action": "mock_action_append"}, {"action": "mock_action"}]
            }
        }
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)
        input_rails = factory.get_input_rails()

        result = input_rails.invoke({"query": "原始query"})

        self.assertEqual(result.get("query"), "更新后的query")

    def test_execution_rails_invoke_action(self):
        """测试ExecutionRails执行Action"""
        config_dict = {"rails": {"execution": [{"action": "mock_execution_action"}]}}
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)
        execution_rails = factory.get_execution_rails()

        result = execution_rails.invoke({"arguments": {"param1": "value1"}})

        self.assertEqual(result.get("arguments"), "更新后的arguments")

    def test_action_decorator_registration(self):
        """测试@action装饰器自动注册Action"""

        @action
        def test_register_action(context: dict, config=None) -> dict:
            return {"result": "ok"}

        test_register_action()

        action_schema = ActionManagerSingleton.get_callable_action_schema(
            "test_register_action"
        )
        self.assertIsNotNone(action_schema)

    def test_action_decorator_async_detection(self):
        """测试@action装饰器检测异步Action"""

        @action
        async def async_action(context: dict, config=None) -> dict:
            return {"async": True}

        @action
        def sync_action(context: dict, config=None) -> dict:
            return {"async": False}

        async_action()
        sync_action()

        self.assertTrue(ActionManagerSingleton.is_action_async("async_action"))
        self.assertFalse(ActionManagerSingleton.is_action_async("sync_action"))

    def test_custom_action_with_config(self):
        """测试自定义Action使用配置参数"""

        @action
        def prefix_action(context: dict, config: ActionConfig = None) -> dict:
            query = context.get("query", "")
            extra_args = (
                config.action_extra_args if config and config.action_extra_args else {}
            )
            prefix = extra_args.get("prefix", "")
            return {"query": f"{prefix}{query}"}

        prefix_action()

        config_dict = {
            "rails": {"input": [{"action": "prefix_action"}]},
            "actions_config": [
                {"action": "prefix_action", "action_extra_args": {"prefix": "[处理] "}}
            ],
        }
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "configs/custom_action_config"
        )
        rails_config = RailsConfig.config_file_dir(
            config_path=config_dir, config_dict=config_dict
        )
        factory = RailsFactory(config=rails_config)
        input_rails = factory.get_input_rails()

        result = input_rails.invoke({"query": "测试"})

        self.assertEqual(result.get("query"), "[处理] 测试")

    def test_rails_context_management(self):
        """测试RailsContext上下文管理"""
        context = RailsContext()

        context.batch_update({"key1": "value1", "key2": "value2"})
        self.assertEqual(context.var_space.get("key1"), "value1")

        context.update("key3", "value3")
        self.assertEqual(context.var_space.get("key3"), "value3")

        context.clear()
        self.assertEqual(context.var_space, {})

    def test_rails_factory_without_config_raises_error(self):
        """测试未提供配置时抛出异常"""
        with self.assertRaises(ValueError):
            RailsFactory()
