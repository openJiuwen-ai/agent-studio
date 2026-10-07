# coding: utf-8
"""IRConverter 派生数据缓存（转换后 IR / node_defs）的单元测试。

覆盖:
1. extract_node_defs: 已发布 IR 首次提取后写入缓存、二次调用命中缓存不再
   提取、未发布/无 ir_path 不缓存、开关关闭不缓存、空结果不写缓存;
2. ir_to_workflow / async_ir_to_workflow: 转换结果首次写入、二次命中直接
   复用缓存对象（不再执行 COW 转换）、未发布不缓存;
3. 缓存值语义: 命中返回的对象与首次转换结果一致（共享引用，只读约定）。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jiuwen.serve.controllers.execution.ir_converter as ir_converter_module
from jiuwen.serve.controllers.execution.ir_converter import IRConverter

_PUBLISHED_PATH = "workflow/app_1782961387661.json"


def _published_ir(ir_path=_PUBLISHED_PATH, workflow_id="wf-1"):
    return {
        "workflowId": workflow_id,
        "ir_path": ir_path,
        "is_published": True,
        "components": [
            {"id": "node_start", "type": "jiuwen.start", "name": "开始"},
            {
                "id": "node_end",
                "type": "jiuwen.end",
                "name": "结束",
                "inputs": {"userFields": {"result": "${node_start.memory.xxx}"}},
            },
        ],
        "connections": [],
    }


def _make_cache_mock():
    """CacheUtils 替身：同步 get/put + 异步 aget/aput 全 mock，默认全 miss。"""
    cache = MagicMock()
    cache.aget = AsyncMock(return_value=None)
    cache.aput = AsyncMock(return_value=None)
    cache.get = MagicMock(return_value=None)
    cache.put = MagicMock(return_value=None)
    return cache


# ---------------------------------------------------------------------------
# extract_node_defs 缓存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_node_defs_caches_published_ir():
    ir = _published_ir()
    cache = _make_cache_mock()
    with patch.object(ir_converter_module, "cache_node_defs_queue", cache):
        result1 = await IRConverter.extract_node_defs(ir)

        # 首次调用：aget miss → 提取 → aput(key, result)
        cache.aget.assert_awaited_once_with(_PUBLISHED_PATH)
        cache.aput.assert_awaited_once()
        args = cache.aput.await_args.args
        assert args[0] == _PUBLISHED_PATH
        assert args[1] == result1

        # 提取结果正确（裁剪后的 node defs）
        assert result1["wf-1"]["node_end"]["node_name"] == "结束"
        assert "userFields" in result1["wf-1"]["node_end"]["configs"]

        # 二次调用：aget 命中 → 直接返回缓存对象，不再提取/写入
        cache.aget = AsyncMock(return_value=result1)
        result2 = await IRConverter.extract_node_defs(ir)
        assert result2 is result1
        assert cache.aput.await_count == 1


@pytest.mark.asyncio
async def test_extract_node_defs_draft_ir_not_cached():
    """未发布（is_published=False）与无 ir_path 的 IR 不读写缓存。"""
    cache = _make_cache_mock()
    with patch.object(ir_converter_module, "cache_node_defs_queue", cache):
        draft = _published_ir()
        draft["is_published"] = False
        await IRConverter.extract_node_defs(draft)

        no_path = _published_ir()
        no_path.pop("ir_path")
        await IRConverter.extract_node_defs(no_path)

        cache.aget.assert_not_awaited()
        cache.aput.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_node_defs_switch_off():
    """node_defs_cache_enable=False 时不读写缓存。"""
    ir = _published_ir()
    cache = _make_cache_mock()
    fake_settings = SimpleNamespace(
        cache=SimpleNamespace(node_defs_cache_enable=False)
    )
    with (
        patch.object(ir_converter_module, "cache_node_defs_queue", cache),
        patch.object(ir_converter_module, "settings", fake_settings),
    ):
        await IRConverter.extract_node_defs(ir)
        cache.aget.assert_not_awaited()
        cache.aput.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_node_defs_empty_result_not_cached():
    """无 components 的 IR 提取结果为空，不写缓存。"""
    ir = _published_ir()
    ir["components"] = []
    cache = _make_cache_mock()
    with patch.object(ir_converter_module, "cache_node_defs_queue", cache):
        result = await IRConverter.extract_node_defs(ir)
        assert result == {}
        cache.aget.assert_awaited_once()
        cache.aput.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_node_defs_subworkflow_recursion_cached():
    """SubWorkflow 子工作流递归提取结果并入父级缓存 value。"""
    parent = _published_ir(workflow_id="wf-parent")
    parent["components"].append(
        {
            "id": "node_sub",
            "type": "jiuwen.subWorkflow",
            "name": "子流程",
            "configs": {"reference": {"path": "workflow/child_1782961099999.json"}},
        }
    )
    child = _published_ir(
        ir_path="workflow/child_1782961099999.json", workflow_id="wf-child"
    )

    cache = _make_cache_mock()
    with (
        patch.object(ir_converter_module, "cache_node_defs_queue", cache),
        patch.object(
            ir_converter_module, "async_ir_load", AsyncMock(return_value=child)
        ),
    ):
        result = await IRConverter.extract_node_defs(parent)

        # 父级 value 同时包含父/子工作流 defs
        assert "wf-parent" in result
        assert "wf-child" in result

        # 父级一次 aput（子递归 miss 时也会各自 aput/aget——本例 child is_published
        # 且带 ir_path，因此子级同样走缓存：共两次 aget / 两次 aput）
        assert cache.aget.await_count == 2
        assert cache.aput.await_count == 2
        put_keys = [c.args[0] for c in cache.aput.await_args_list]
        assert _PUBLISHED_PATH in put_keys
        assert "workflow/child_1782961099999.json" in put_keys


# ---------------------------------------------------------------------------
# ir_to_workflow / async_ir_to_workflow 转换缓存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ir_to_workflow_sync_cache_roundtrip():
    ir = _published_ir()
    cache = _make_cache_mock()
    with (
        patch.object(ir_converter_module, "cache_ir_converted_queue", cache),
        patch.object(
            ir_converter_module,
            "_convert_global_variable_refs_in_ir",
            wraps=ir_converter_module._convert_global_variable_refs_in_ir,
        ) as convert,
    ):
        lazy1 = await IRConverter.ir_to_workflow(ir)
        # 首次：aget miss → 真实转换 → aput
        cache.aget.assert_awaited_once_with(_PUBLISHED_PATH)
        cache.aput.assert_awaited_once()
        put_key, put_value = cache.aput.await_args.args
        assert put_key == _PUBLISHED_PATH
        # 转换真实发生：End 节点 memory 引用已改写
        assert (
            put_value["components"][1]["inputs"]["userFields"]["result"]
            == "${MEMORY_VARIABLE.xxx}"
        )
        # LazyWorkflow 持有转换结果
        assert lazy1._ir_data is put_value
        assert convert.call_count == 1

        # 二次：aget 命中 → 直接复用缓存对象，不再转换
        cached_value = put_value
        cache.aget = AsyncMock(return_value=cached_value)
        lazy2 = await IRConverter.ir_to_workflow(ir)
        assert lazy2._ir_data is cached_value
        assert convert.call_count == 1
        assert cache.aput.await_count == 1


@pytest.mark.asyncio
async def test_async_ir_to_workflow_cache_roundtrip():
    ir = _published_ir()
    cache = _make_cache_mock()
    with (
        patch.object(ir_converter_module, "cache_ir_converted_queue", cache),
        patch.object(
            ir_converter_module,
            "_convert_global_variable_refs_in_ir",
            wraps=ir_converter_module._convert_global_variable_refs_in_ir,
        ) as convert,
    ):
        lazy1 = await IRConverter.async_ir_to_workflow(ir)
        cache.aget.assert_awaited_once_with(_PUBLISHED_PATH)
        cache.aput.assert_awaited_once()
        put_key, put_value = cache.aput.await_args.args
        assert put_key == _PUBLISHED_PATH
        assert lazy1._ir_data is put_value
        assert convert.call_count == 1

        cache.aget = AsyncMock(return_value=put_value)
        lazy2 = await IRConverter.async_ir_to_workflow(ir)
        assert lazy2._ir_data is put_value
        assert convert.call_count == 1
        assert cache.aput.await_count == 1


@pytest.mark.asyncio
async def test_async_ir_to_workflow_draft_not_cached():
    ir = _published_ir()
    ir["is_published"] = False
    cache = _make_cache_mock()
    with patch.object(ir_converter_module, "cache_ir_converted_queue", cache):
        await IRConverter.async_ir_to_workflow(ir)
        cache.aget.assert_not_awaited()
        cache.aput.assert_not_awaited()

        await IRConverter.ir_to_workflow(ir)
        cache.aget.assert_not_awaited()
        cache.aput.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_ir_to_workflow_switch_off():
    ir = _published_ir()
    cache = _make_cache_mock()
    fake_settings = SimpleNamespace(
        cache=SimpleNamespace(ir_converted_cache_enable=False)
    )
    with (
        patch.object(ir_converter_module, "cache_ir_converted_queue", cache),
        patch.object(ir_converter_module, "settings", fake_settings),
    ):
        await IRConverter.async_ir_to_workflow(ir)
        cache.aget.assert_not_awaited()
        cache.aput.assert_not_awaited()


@pytest.mark.asyncio
async def test_converted_cache_input_not_polluted():
    """缓存路径下转换仍保持 COW 语义：输入 IR 不被修改。"""
    ir = _published_ir()
    original_ref = ir["components"][1]["inputs"]["userFields"]["result"]
    cache = _make_cache_mock()
    with patch.object(ir_converter_module, "cache_ir_converted_queue", cache):
        await IRConverter.async_ir_to_workflow(ir)
        # 输入 IR 保持原样（共享缓存安全的前提）
        assert (
            ir["components"][1]["inputs"]["userFields"]["result"] == original_ref
        )
        # 缓存的转换结果与输入共享未命中子树（零拷贝快路径）
        put_value = cache.aput.await_args.args[1]
        assert put_value["components"][0] is ir["components"][0]
        assert put_value["components"][1] is not ir["components"][1]
