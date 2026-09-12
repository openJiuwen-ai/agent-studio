"""
Planner -- 全量测试入口

自动发现并导入 planner/ 下所有 **/test_*.py 中的测试类，
使 pytest 仅运行本文件即可触发全部用例。

用法：
  pytest -v test_planner.py
"""

import importlib.util
from pathlib import Path

import pytest

_CASE_DIR = Path(__file__).resolve().parent

_SUBDIR_TEST_FILES = sorted(
    p
    for p in _CASE_DIR.rglob("test_*.py")
    if p.is_file() and "old_backup" not in p.name and p.parent != _CASE_DIR
)

_CLASS_TO_MODULE: dict[str, object] = {}
_FIXTURE_MODULES: dict[str, object] = {}

for _path in _SUBDIR_TEST_FILES:
    _module_name = (
        f"planner.{'.'.join(_path.relative_to(_CASE_DIR).with_suffix('').parts)}"
    )
    _spec = importlib.util.spec_from_file_location(_module_name, str(_path))
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    _FIXTURE_MODULES[_path.parent.name] = _module
    for _attr in dir(_module):
        if _attr.startswith("Test"):
            globals()[_attr] = getattr(_module, _attr)
            _CLASS_TO_MODULE[_attr] = _module


@pytest.fixture()
def local_ir_path(request, tmp_path_factory, monkeypatch):
    source_module = _CLASS_TO_MODULE.get(request.cls.__name__)
    if source_module is None:
        raise ValueError(
            f"Unknown test class: {request.cls.__name__}, "
            f"cannot resolve local_ir_path fixture"
        )
    source_module._init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp(request.cls.__name__)
    return source_module._copy_ir_to_tmp(tmp_path)
