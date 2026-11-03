# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 以独名注册本目录 fakes：规避两包 tests/fakes.py 同名互撞，以及
# importlib 收集模式下顶层 `from fakes import` 不可达的问题。

import importlib.util
import pathlib
import sys

_FAKES_ALIAS = "redis_native_test_fakes"
if _FAKES_ALIAS not in sys.modules:
    _path = pathlib.Path(__file__).parent / "fakes.py"
    _spec = importlib.util.spec_from_file_location(_FAKES_ALIAS, _path)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_FAKES_ALIAS] = _mod
    _spec.loader.exec_module(_mod)

import pytest


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """隔离 CWD（.env 按 CWD 相对解析），避免开发目录的 .env 注入 Settings。"""
    monkeypatch.chdir(tmp_path)
