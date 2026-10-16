# coding: utf-8
"""DrawBox 插件单元测试。

覆盖修改点 B2-B4：
- B2: calculate_area 操作
- B3: find_overlaps 操作
- B4: merge_boxes 操作
"""

import importlib.util
import json
import os

import pytest

# extensions 目录不是标准 Python 包，用 importlib 按文件路径加载
_draw_box_path = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..",
        "extensions", "components", "draw-box", "draw_box.py",
    )
)
_spec = importlib.util.spec_from_file_location("draw_box", _draw_box_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
FlowDrawBox = _module.FlowDrawBox


# --------------------------------------------------------------------------- #
# B2: calculate_area
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_calculate_area_basic():
    """B2: 4 个点 → 正确面积/中心/边界。"""
    plugin = FlowDrawBox()
    coordinates = [
        {"x": 0, "y": 0},
        {"x": 10, "y": 0},
        {"x": 10, "y": 5},
        {"x": 0, "y": 5},
    ]
    result = await plugin.invoke({"operation": "calculate_area", "coordinates": coordinates})
    assert result["output"]["operation"] == "calculate_area"
    assert result["output"]["area"] == 50
    assert result["output"]["center"] == {"x": 5.0, "y": 2.5}
    assert result["output"]["bounds"] == {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 5}
    assert result["output"]["point_count"] == 4


@pytest.mark.asyncio
async def test_calculate_area_less_than_2_points():
    """B2: <2 个点 → area=0。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "calculate_area",
        "coordinates": [{"x": 1, "y": 1}],
    })
    assert result["output"]["area"] == 0
    assert result["output"]["center"] is None
    assert result["output"]["bounds"] is None
    assert result["output"]["point_count"] == 1


@pytest.mark.asyncio
async def test_calculate_area_empty():
    """B2: 空列表 → area=0。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "calculate_area", "coordinates": []})
    assert result["output"]["area"] == 0
    assert result["output"]["point_count"] == 0


# --------------------------------------------------------------------------- #
# B3: find_overlaps
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_find_overlaps_basic():
    """B3: 2 组有重叠 → overlap_pairs 非空。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 5, "y": 5}, {"x": 15, "y": 15}],
    ]
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": box_groups})
    assert result["output"]["operation"] == "find_overlaps"
    assert len(result["output"]["overlap_pairs"]) > 0
    assert result["output"]["overlap_count"] == 1


@pytest.mark.asyncio
async def test_find_overlaps_no_overlap():
    """B3: 2 组无重叠 → overlap_count=0。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 20, "y": 20}, {"x": 30, "y": 30}],
    ]
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": box_groups})
    assert result["output"]["overlap_count"] == 0
    assert result["output"]["overlap_pairs"] == []


@pytest.mark.asyncio
async def test_find_overlaps_empty_input():
    """B3: 空输入 → overlap_count=0。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": []})
    assert result["output"]["overlap_count"] == 0
    assert result["output"]["overlap_pairs"] == []


# --------------------------------------------------------------------------- #
# B4: merge_boxes
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_merge_boxes_basic():
    """B4: 2 组有重叠 → 合并为 1 组。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 5, "y": 5}, {"x": 15, "y": 15}],
    ]
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": box_groups})
    assert result["output"]["operation"] == "merge_boxes"
    assert result["output"]["box_count"] == 1
    merged = result["output"]["merged_boxes"][0]
    assert merged["min_x"] == 0
    assert merged["max_x"] == 15
    assert merged["min_y"] == 0
    assert merged["max_y"] == 15


@pytest.mark.asyncio
async def test_merge_boxes_no_overlap():
    """B4: 2 组无重叠 → 保持 2 组。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 20, "y": 20}, {"x": 30, "y": 30}],
    ]
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": box_groups})
    assert result["output"]["box_count"] == 2


@pytest.mark.asyncio
async def test_merge_boxes_empty_input():
    """B4: 空输入 → box_count=0。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": []})
    assert result["output"]["box_count"] == 0
    assert result["output"]["merged_boxes"] == []


@pytest.mark.asyncio
async def test_merge_boxes_transitive_overlap():
    """B4: 传递性重叠 — A∩C, B∩C, A∩B 不相交，三者应合并为 1 组。

    A=[0,10], B=[20,30], C=[5,25]。
    A 与 B 不相交，但 C 分别与 A、B 相交，传递性合并后应为 1 个框。
    """
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 20, "y": 20}, {"x": 30, "y": 30}],
        [{"x": 5, "y": 5}, {"x": 25, "y": 25}],
    ]
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": box_groups})
    assert result["output"]["box_count"] == 1
    merged = result["output"]["merged_boxes"][0]
    assert merged["min_x"] == 0
    assert merged["max_x"] == 30
    assert merged["min_y"] == 0
    assert merged["max_y"] == 30


@pytest.mark.asyncio
async def test_find_overlaps_border_touching():
    """B3: 边界相切不算重叠。A=[0,10], B=[10,20] → 相切不重叠。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 10, "y": 10}, {"x": 20, "y": 20}],
    ]
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": box_groups})
    assert result["output"]["overlap_count"] == 0


# --------------------------------------------------------------------------- #
# B2-B4: 边界场景
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_invoke_string_coordinates():
    """B2-B4: coordinates 为 JSON 字符串 → json.loads 解析。"""
    plugin = FlowDrawBox()
    coordinates_str = json.dumps([
        {"x": 0, "y": 0},
        {"x": 10, "y": 0},
        {"x": 10, "y": 5},
        {"x": 0, "y": 5},
    ])
    result = await plugin.invoke({
        "operation": "calculate_area",
        "coordinates": coordinates_str,
    })
    assert result["output"]["area"] == 50
    assert result["output"]["point_count"] == 4


@pytest.mark.asyncio
async def test_invoke_default_operation():
    """B2: 不传 operation → 默认 calculate_area。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"coordinates": [{"x": 0, "y": 0}, {"x": 5, "y": 5}]})
    assert result["output"]["operation"] == "calculate_area"
    assert result["output"]["area"] == 25
