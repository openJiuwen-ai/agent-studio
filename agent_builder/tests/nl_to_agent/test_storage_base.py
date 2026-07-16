#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""BaseConversationMemory 基类单元测试"""

from unittest.mock import MagicMock, patch

import pytest

from agent_builder.nl_to_agent.storage.base import BaseConversationMemory


class ConcreteMemory(BaseConversationMemory):

    @staticmethod
    def add(key: object, value: object) -> bool:
        return True

    @staticmethod
    def get(key: object) -> object:
        return "value_of_" + str(key)

    @staticmethod
    def get_nearest_k(key: object, k: int) -> list:
        return ["nearest_item"]

    @staticmethod
    def get_all(key: object) -> list:
        return ["all_item"]

    @staticmethod
    def contains(key: object) -> bool:
        return True

    @staticmethod
    def delete(key: object) -> bool:
        return True


class TestBaseConversationMemoryAbstract:

    @staticmethod
    def test_can_instantiate_directly():
        obj = BaseConversationMemory()
        assert isinstance(obj, BaseConversationMemory)

    @staticmethod
    def test_is_subclass_of_abc():
        from abc import ABC
        assert issubclass(BaseConversationMemory, ABC)

    @staticmethod
    def test_has_no_abstract_methods():
        from abc import ABC
        assert len(getattr(BaseConversationMemory, "__abstractmethods__", set())) == 0


class TestConcreteSubclass:

    @staticmethod
    def test_can_instantiate_concrete_subclass():
        obj = ConcreteMemory()
        assert isinstance(obj, BaseConversationMemory)

    @staticmethod
    def test_add_override():
        obj = ConcreteMemory()
        assert obj.add("key1", "value1") is True

    @staticmethod
    def test_get_override():
        obj = ConcreteMemory()
        assert obj.get("key1") == "value_of_key1"

    @staticmethod
    def test_get_nearest_k_override():
        obj = ConcreteMemory()
        assert obj.get_nearest_k("key1", 3) == ["nearest_item"]

    @staticmethod
    def test_get_all_override():
        obj = ConcreteMemory()
        assert obj.get_all("key1") == ["all_item"]

    @staticmethod
    def test_contains_override():
        obj = ConcreteMemory()
        assert obj.contains("key1") is True

    @staticmethod
    def test_delete_override():
        obj = ConcreteMemory()
        assert obj.delete("key1") is True


class TestDefaultImplementations:

    @staticmethod
    def test_add_default_returns_none():
        assert BaseConversationMemory.add(None, "key", "value") is None

    @staticmethod
    def test_get_default_returns_none():
        assert BaseConversationMemory.get(None, "key") is None

    @staticmethod
    def test_get_nearest_k_default_returns_none():
        assert BaseConversationMemory.get_nearest_k(None, "key", 5) is None

    @staticmethod
    def test_get_all_default_returns_none():
        assert BaseConversationMemory.get_all(None, "key") is None

    @staticmethod
    def test_contains_default_returns_none():
        assert BaseConversationMemory.contains(None, "key") is None

    @staticmethod
    def test_delete_default_returns_none():
        assert BaseConversationMemory.delete(None, "key") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])