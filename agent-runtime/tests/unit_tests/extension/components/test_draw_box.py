# coding: utf-8
"""DrawBox 插件单元测试。

覆盖修改点 B2-B4：
- B2: calculate_area 操作
- B3: find_overlaps 操作
- B4: merge_boxes 操作
"""

import base64
import importlib.util
import json
import os
import sys
from unittest import mock

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

MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024


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


# --------------------------------------------------------------------------- #
# draw_boxes: 在图像上绘制边界框和标签
# --------------------------------------------------------------------------- #

def _make_test_image_base64(width=100, height=80):
    """生成一张纯色 PNG 的 base64 字符串用于测试。"""
    from PIL import Image
    import io
    import base64 as b64
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return b64.b64encode(buf.getvalue()).decode("ascii")


def _make_test_image_path(tmp_path, width=100, height=80):
    """生成一张纯色 PNG 文件并返回路径。"""
    from PIL import Image
    p = tmp_path / "test.png"
    img = Image.new("RGB", (width, height), (255, 255, 255))
    img.save(p, format="PNG")
    return str(p)


@pytest.mark.asyncio
async def test_draw_boxes_basic_base64():
    """draw_boxes: base64 图像 + 1 个标注 → 成功绘制。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64(100, 80)
    annotations = json.dumps({"annotations": [
        {"bbox": [10, 20, 50, 60], "label": "person", "confidence": 0.95}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
    })
    out = result["output"]
    assert out["success"] is True
    assert out["annotation_count"] == 1
    assert out["image_size"] == {"width": 100, "height": 80}
    assert "image_base64" in out
    assert len(out["image_base64"]) > 0


@pytest.mark.asyncio
async def test_draw_boxes_path_input(tmp_path):
    """draw_boxes: 本地路径图像输入 → 正常绘制。"""
    plugin = FlowDrawBox()
    image_path = _make_test_image_path(tmp_path)
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 50, 50], "label": "car"}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_path,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_file_dict(tmp_path):
    """draw_boxes: 文件对象(dict 含 path) → 兼容解析。"""
    plugin = FlowDrawBox()
    from PIL import Image
    p = tmp_path / "file_obj_test.png"
    Image.new("RGB", (50, 50), (0, 0, 0)).save(p, format="PNG")
    file_obj = {"url": "", "path": str(p), "filename": "test.png", "mime_type": "image/png"}
    annotations = json.dumps({"annotations": [{"bbox": [0, 0, 10, 10], "label": "x"}]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": file_obj,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_relative_coords():
    """draw_boxes: relative 坐标(0-1000) → 按比例转换到像素。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64(200, 100)
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 1000, 1000], "label": "full"}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "relative",
    })
    assert result["output"]["success"] is True
    assert result["output"]["image_size"] == {"width": 200, "height": 100}


@pytest.mark.asyncio
async def test_draw_boxes_missing_image():
    """draw_boxes: 缺少 image → error_code=400。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400


@pytest.mark.asyncio
async def test_draw_boxes_invalid_annotation_format():
    """draw_boxes: annotations 不是合法 JSON → error_code=422。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": "not-a-json",
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 422


@pytest.mark.asyncio
async def test_draw_boxes_invalid_base64():
    """draw_boxes: 无法解析的 image 字符串 → error_code=404。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": "!!!not-valid-base64-or-url-or-path!!!",
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


@pytest.mark.asyncio
async def test_draw_boxes_too_many_annotations():
    """draw_boxes: 超过 100 个标注 → error_code=400。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    anns = [{"bbox": [0, 0, 10, 10], "label": "x"} for _ in range(101)]
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": json.dumps({"annotations": anns}),
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400


@pytest.mark.asyncio
async def test_draw_boxes_custom_styling():
    """draw_boxes: 自定义颜色/线宽/字号 → 正常绘制不报错。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [10, 10, 50, 50], "label": "test", "confidence": 0.8}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "box_color": "#00ff00",
        "text_color": "#000000",
        "line_width": 5,
        "font_size": 24,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_clamp_line_width():
    """draw_boxes: line_width 超范围 → clamp 到 [1,20]。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 10, 10], "label": "x"}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "line_width": 100,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_no_label():
    """draw_boxes: 标注无 label 字段 → 仍成功绘制(只画框)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 10, 10]}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


# --------------------------------------------------------------------------- #
# draw_boxes: 错误码与参数校验补充
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_draw_boxes_missing_annotations():
    """draw_boxes: 缺省 annotations → 视为空标注，仅绘制图像(success=True)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 0


@pytest.mark.asyncio
async def test_draw_boxes_empty_string_annotations():
    """draw_boxes: annotations 为空字符串 → 视为空标注，仅绘制图像(success=True)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": "",
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 0


@pytest.mark.asyncio
async def test_calculate_area_empty_coordinates():
    """calculate_area: coordinates 为空字符串 → 按空坐标处理，不抛 JSONDecodeError。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "calculate_area", "coordinates": ""})
    assert isinstance(result["output"], dict)
    assert result["output"].get("error_code") != 400
    assert "success" in result["output"] or "point_count" in result["output"]


@pytest.mark.asyncio
async def test_calculate_area_invalid_coordinates():
    """calculate_area: coordinates 为非法 JSON 字符串 → 返回明确错误提示（error_code=400）。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "calculate_area", "coordinates": "not-json"})
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400
    assert "coordinates" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_image_too_large():
    """draw_boxes: 图像宽度超过 4096 → error_code=413。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64(4097, 10)
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 413
    assert "4096" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_annotations_not_list():
    """draw_boxes: annotations 解析后为非 list(字符串) → error_code=422。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations": "not-a-list"}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 422
    assert "must be a list" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_annotations_as_list():
    """draw_boxes: annotations 直接为 list(非 dict 包装) → 正常解析绘制。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = [{"bbox": [0, 0, 10, 10], "label": "x"}]
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_non_rgb_image():
    """draw_boxes: RGBA 模式图像 → 自动转换为 RGB 后绘制。"""
    plugin = FlowDrawBox()
    from PIL import Image
    import io
    img = Image.new("RGBA", (60, 60), (255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    annotations = json.dumps({"annotations": [{"bbox": [0, 0, 30, 30], "label": "x"}]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_annotation_not_dict():
    """draw_boxes: 标注项非 dict(字符串/int) → 跳过，有效标注正常绘制。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        "not-a-dict",
        {"bbox": [0, 0, 10, 10], "label": "valid"},
        42,
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_invalid_bbox():
    """draw_boxes: bbox 缺失或长度不为 4 → 跳过，仅绘制有效标注。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"label": "no-bbox"},
        {"bbox": [0, 0, 10], "label": "len3"},
        {"bbox": [0, 0, 10, 10, 50], "label": "len5"},
        {"bbox": [0, 0, 20, 20], "label": "valid"},
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_confidence_only():
    """draw_boxes: 标注仅有 confidence 无 label → 标签为置信度数值。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 30, 30], "confidence": 0.87}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_pillow_import_error():
    """draw_boxes: Pillow 导入失败 → error_code=500。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    with mock.patch.dict(sys.modules, {
        "PIL": None, "PIL.Image": None,
        "PIL.ImageDraw": None, "PIL.ImageFont": None,
    }):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": image_b64,
            "annotations": '{"annotations":[]}',
        })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 500
    assert "Pillow" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_text_fallback():
    """draw_boxes: textbbox 抛异常 → 回退到 draw.text 无字体绘制。"""
    from PIL import ImageDraw
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 50, 50], "label": "hello", "confidence": 0.9}
    ]})
    with mock.patch.object(
        ImageDraw.ImageDraw, "textbbox", side_effect=RuntimeError("boom")
    ):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": image_b64,
            "annotations": annotations,
            "coordinate_type": "absolute",
        })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_clamp_font_size():
    """draw_boxes: font_size 超范围 → clamp 到 [8,72]。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 10, 10], "label": "x"}
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "font_size": 999,
        "line_width": 0,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True


# --------------------------------------------------------------------------- #
# draw_boxes: _resolve_image_bytes 多格式输入兼容
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_draw_boxes_dict_with_binary():
    """draw_boxes: 文件 dict 含 binary(原始字节) → 直接使用。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    raw_bytes = base64.b64decode(image_b64)
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": {"binary": raw_bytes, "filename": "img.png"},
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_json_string_dict_binary():
    """draw_boxes: image 为 JSON 字符串(dict 含 binary base64 文本) → base64 解码后使用。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    image_json_str = json.dumps({"binary": image_b64, "filename": "img.png"})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_json_str,
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_dict_with_url_mocked():
    """draw_boxes: dict 含 url → 通过 fetch_url 拉取(已 mock)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    raw_bytes = base64.b64decode(image_b64)
    with mock.patch.object(FlowDrawBox, "fetch_url", return_value=raw_bytes):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": {"url": "https://example.com/img.png"},
            "annotations": '{"annotations":[]}',
        })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_dict_no_valid_key():
    """draw_boxes: dict 无 binary/url/path → ValueError → error_code=404。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": {"filename": "no-data.png"},
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


@pytest.mark.asyncio
async def test_draw_boxes_json_string_dict_image(tmp_path):
    """draw_boxes: image 为 JSON 字符串(dict 含 path) → 递归解析。"""
    plugin = FlowDrawBox()
    image_path = _make_test_image_path(tmp_path)
    image_json_str = json.dumps({"path": image_path})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_json_str,
        "annotations": '{"annotations":[]}',
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_json_string_invalid():
    """draw_boxes: image 为以 { 开头的非法 JSON → JSONDecodeError 跳过 → 404。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": "{not-valid-json",
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


@pytest.mark.asyncio
async def test_draw_boxes_url_string_mocked():
    """draw_boxes: image 为 URL 字符串 → fetch_url 拉取(已 mock)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    raw_bytes = base64.b64decode(image_b64)
    with mock.patch.object(FlowDrawBox, "fetch_url", return_value=raw_bytes):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": "https://example.com/img.png",
            "annotations": '{"annotations":[]}',
        })
    assert result["output"]["success"] is True


@pytest.mark.asyncio
async def test_draw_boxes_unsupported_image_type():
    """draw_boxes: image 为 int 类型 → ValueError → error_code=404。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": 12345,
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


# --------------------------------------------------------------------------- #
# draw_boxes: clamp / fetch_url / load_font 内部方法
# --------------------------------------------------------------------------- #

def test_clamp_non_numeric():
    """clamp: 非数值输入(str/None) → 返回下界 lo。"""
    assert FlowDrawBox.clamp("abc", 1, 20) == 1
    assert FlowDrawBox.clamp(None, 1, 20) == 1


def test_clamp_boundaries():
    """clamp: 超出上下界 → clamp 到 [lo, hi]。"""
    assert FlowDrawBox.clamp(0, 1, 20) == 1
    assert FlowDrawBox.clamp(100, 1, 20) == 20
    assert FlowDrawBox.clamp(10, 1, 20) == 10


def test_fetch_url_mocked():
    """fetch_url: 通过 mock 验证 opener.open 调用与分块读取。"""
    fake_resp = mock.MagicMock()
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.read.side_effect = [b"fake-image-bytes", b""]
    fake_opener = mock.MagicMock()
    fake_opener.open.return_value = fake_resp
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.build_opener", return_value=fake_opener):
        data = FlowDrawBox.fetch_url("https://example.com/img.png")
    assert data == b"fake-image-bytes"
    fake_opener.open.assert_called_once_with("https://example.com/img.png", timeout=30)


def test_load_font_no_candidates():
    """load_font: 无可用字体文件 → load_default(size=)。"""
    from PIL import ImageFont
    plugin = FlowDrawBox()
    with mock.patch("os.path.exists", return_value=False):
        font = plugin.load_font(ImageFont, 16)
    assert font is not None


def test_load_font_truetype_exception(tmp_path):
    """load_font: 字体文件存在但非有效字体 → truetype 失败 → 继续到 load_default。"""
    from PIL import ImageFont
    plugin = FlowDrawBox()
    bad_font = tmp_path / "bad_font.ttf"
    bad_font.write_bytes(b"not a real font file")
    with mock.patch.object(FlowDrawBox, "FONT_CANDIDATES", [str(bad_font)]):
        font = plugin.load_font(ImageFont, 16)
    assert font is not None


def test_load_font_default_typeerror():
    """load_font: load_default(size=) 抛 TypeError → load_default() 无参数。"""
    from PIL import ImageFont
    plugin = FlowDrawBox()
    original_load_default = ImageFont.load_default
    call_count = {"n": 0}

    def fake_load_default(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TypeError("size kwarg not supported")
        return original_load_default()

    with mock.patch("os.path.exists", return_value=False), \
         mock.patch.object(ImageFont, "load_default", side_effect=fake_load_default):
        font = plugin.load_font(ImageFont, 16)
    assert font is not None


# --------------------------------------------------------------------------- #
# B2-B4: merge/parse 补充边界
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_merge_boxes_all_invalid_groups():
    """B4: 所有坐标组点数<2 → 解析后 boxes 为空 → box_count=0。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}],
        [{"x": 1, "y": 1}],
    ]
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": box_groups})
    assert result["output"]["box_count"] == 0
    assert result["output"]["merged_boxes"] == []


@pytest.mark.asyncio
async def test_merge_boxes_string_group():
    """B4: 坐标组为 JSON 字符串 → json.loads 解析后正常合并。"""
    plugin = FlowDrawBox()
    group_str = json.dumps([{"x": 0, "y": 0}, {"x": 10, "y": 10}])
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": [group_str]})
    assert result["output"]["box_count"] == 1
    merged = result["output"]["merged_boxes"][0]
    assert merged["min_x"] == 0
    assert merged["max_x"] == 10


@pytest.mark.asyncio
async def test_merge_boxes_non_list_input():
    """B4: coordinates 为非 list(dict) → 返回空合并。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": {"a": 1}})
    assert result["output"]["box_count"] == 0
    assert result["output"]["merged_boxes"] == []


@pytest.mark.asyncio
async def test_find_overlaps_non_list_input():
    """B3: coordinates 为非 list(dict) → 返回空重叠。"""
    plugin = FlowDrawBox()
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": {"a": 1}})
    assert result["output"]["overlap_count"] == 0
    assert result["output"]["overlap_pairs"] == []


@pytest.mark.asyncio
async def test_parse_box_groups_partial_invalid():
    """B3/B4: 混合有效与无效组 → 仅保留有效组参与重叠/合并。"""
    plugin = FlowDrawBox()
    box_groups = [
        [{"x": 0, "y": 0}],  # 1 point → skipped (line 348)
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],  # valid
    ]
    result = await plugin.invoke({"operation": "merge_boxes", "coordinates": box_groups})
    assert result["output"]["box_count"] == 1


# --------------------------------------------------------------------------- #
# MR 评审修复：安全校验与容错
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_draw_boxes_invalid_coordinate_type():
    """draw_boxes: coordinate_type 非 relative/absolute → error_code=400。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations":[]}',
        "coordinate_type": "pixel",
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400
    assert "coordinate_type" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_non_numeric_bbox_skipped():
    """draw_boxes: bbox 含非数值元素 → 该条标注跳过，有效标注正常绘制。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": ["a", "b", "c", "d"], "label": "invalid"},
        {"bbox": [0, 0, 20, 20], "label": "valid"},
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_nan_inf_bbox_skipped():
    """draw_boxes: bbox 含 NaN/Inf → float() 成功但 isfinite 校验失败 → 跳过。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": ["nan", "nan", 50, 50], "label": "nan-bbox"},
        {"bbox": ["inf", "-inf", 50, 50], "label": "inf-bbox"},
        {"bbox": [0, 0, 20, 20], "label": "valid"},
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_bad_confidence_skipped():
    """draw_boxes: confidence 为非数值 → 跳过置信度，标注仍绘制。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    annotations = json.dumps({"annotations": [
        {"bbox": [0, 0, 20, 20], "label": "test", "confidence": "high"},
    ]})
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": annotations,
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 1


@pytest.mark.asyncio
async def test_draw_boxes_non_image_extension_rejected(tmp_path):
    """draw_boxes: 路径指向 .txt 文件 → 路径校验失败 → error_code=404。"""
    plugin = FlowDrawBox()
    txt_file = tmp_path / "secret.txt"
    txt_file.write_text("not an image")
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": str(txt_file),
        "annotations": '{"annotations":[]}',
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


def test_fetch_url_invalid_scheme():
    """fetch_url: file:// scheme → illegal_url 拒绝 → ValueError。"""
    with pytest.raises(ValueError, match="illegal"):
        FlowDrawBox.fetch_url("file:///etc/passwd")


def test_fetch_url_ftp_scheme_rejected():
    """fetch_url: ftp:// scheme → illegal_url 拒绝 → ValueError。"""
    with pytest.raises(ValueError, match="illegal"):
        FlowDrawBox.fetch_url("ftp://example.com/img.png")


def test_validate_image_path_valid_png(tmp_path):
    """validate_image_path: .png 路径 → 通过校验。"""
    from PIL import Image
    p = tmp_path / "valid.png"
    Image.new("RGB", (10, 10)).save(p, format="PNG")
    FlowDrawBox.validate_image_path(str(p))


def test_validate_image_path_invalid_extension():
    """validate_image_path: .txt 路径 → ValueError。"""
    with pytest.raises(ValueError, match="image file"):
        FlowDrawBox.validate_image_path("/tmp/secret.txt")


# --------------------------------------------------------------------------- #
# 安全评审修复：SSRF / 解压炸弹 / 大小限制 / 颜色预校验 / truthiness
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_draw_boxes_empty_annotations_list():
    """安全修复 G: annotations 为空列表 [] → 正常绘制 0 个标注(success=True)。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": [],
        "coordinate_type": "absolute",
    })
    assert result["output"]["success"] is True
    assert result["output"]["annotation_count"] == 0


@pytest.mark.asyncio
async def test_draw_boxes_invalid_box_color():
    """安全修复 F: box_color 非法颜色格式 → error_code=400。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations":[]}',
        "box_color": "not-a-color",
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400
    assert "color" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_invalid_text_color():
    """安全修复 F: text_color 非法颜色格式 → error_code=400。"""
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations":[]}',
        "text_color": "rainbow",
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400
    assert "color" in result["output"]["error"]


@pytest.mark.asyncio
async def test_draw_boxes_binary_too_large():
    """安全修复 E: binary 数据超过 50MB → ValueError → error_code=404。"""
    plugin = FlowDrawBox()
    huge_data = b"\x00" * (MAX_DOWNLOAD_SIZE + 1)
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": {"binary": huge_data},
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


@pytest.mark.asyncio
async def test_draw_boxes_base64_too_large():
    """安全修复 E: base64 字符串超过上限 → ValueError → error_code=404。"""
    plugin = FlowDrawBox()
    huge_b64 = "A" * (MAX_DOWNLOAD_SIZE * 2 + 1)
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": huge_b64,
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


@pytest.mark.asyncio
async def test_draw_boxes_dict_binary_base64_too_large():
    """dict.binary 为超长 base64 字符串 → 解码前长度检查拒绝 → error_code=404。"""
    plugin = FlowDrawBox()
    huge_b64 = "A" * (MAX_DOWNLOAD_SIZE * 2 + 1)
    result = await plugin.invoke({
        "operation": "draw_boxes",
        "image": {"binary": huge_b64, "filename": "img.png"},
        "annotations": '{"annotations":[]}',
    })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


def test_fetch_url_rejects_internal_ip():
    """安全修复 A: 内网 URL → illegal_url 返回 True → ValueError。"""
    with mock.patch.object(_module, "illegal_url", return_value=True):
        with pytest.raises(ValueError, match="illegal"):
            FlowDrawBox.fetch_url("http://10.0.0.1/secret.png")


def test_fetch_url_chunked_size_limit():
    """安全修复 C: 分块读取超过 50MB → ValueError。"""
    fake_resp = mock.MagicMock()
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.read.side_effect = [b"\x00" * (64 * 1024)] * 1000 + [b""]
    fake_opener = mock.MagicMock()
    fake_opener.open.return_value = fake_resp
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.build_opener", return_value=fake_opener):
        with pytest.raises(ValueError, match="too large"):
            FlowDrawBox.fetch_url("https://example.com/big.png")


# --------------------------------------------------------------------------- #
# 第 4 轮安全评审修复：SSRF 重定向 / MAX_IMAGE_PIXELS 恢复 / base64 解码后大小
# --------------------------------------------------------------------------- #

def test_ssrf_redirect_handler_rejects_internal():
    """安全修复: 重定向到内网地址 → illegal_url 返回 True → ValueError。"""
    handler = _module.SSRFSafeRedirectHandler()
    with mock.patch.object(_module, "illegal_url", return_value=True):
        with pytest.raises(ValueError, match="Redirect URL is illegal"):
            handler.redirect_request(None, None, 302, "Found", {}, "http://10.0.0.1/secret")


def test_ssrf_redirect_handler_allows_external():
    """安全修复: 重定向到合法外部地址 → 放行给父类处理。"""
    handler = _module.SSRFSafeRedirectHandler()
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.HTTPRedirectHandler.redirect_request", return_value="ok"):
        result = handler.redirect_request(None, None, 302, "Found", {}, "https://cdn.example.com/img.png")
    assert result == "ok"


@pytest.mark.asyncio
async def test_draw_boxes_max_image_pixels_not_modified():
    """安全修复: 不修改进程级 Image.MAX_IMAGE_PIXELS，避免并发竞态。"""
    from PIL import Image
    original = Image.MAX_IMAGE_PIXELS
    plugin = FlowDrawBox()
    image_b64 = _make_test_image_base64()
    await plugin.invoke({
        "operation": "draw_boxes",
        "image": image_b64,
        "annotations": '{"annotations":[]}',
    })
    assert Image.MAX_IMAGE_PIXELS == original


@pytest.mark.asyncio
async def test_draw_boxes_base64_decoded_too_large():
    """安全修复: base64 解码后超过 _MAX_DOWNLOAD_SIZE → ValueError → error_code=404。"""
    plugin = FlowDrawBox()
    small_b64 = base64.b64encode(b"\x00" * 150).decode()
    with mock.patch.object(FlowDrawBox, "_MAX_DOWNLOAD_SIZE", 100):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": small_b64,
            "annotations": '{"annotations":[]}',
        })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 404


# --------------------------------------------------------------------------- #
# BUG2026102804734 问题1: fetch_url verify_ssl + 证书错误归 400
# --------------------------------------------------------------------------- #

def test_fetch_url_verify_ssl_true_keeps_default_handlers():
    """问题1: verify_ssl 默认 true → 不注入关闭校验的 HTTPSHandler，行为不变。"""
    import urllib.request
    fake_resp = mock.MagicMock()
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.read.side_effect = [b"x", b""]
    fake_opener = mock.MagicMock()
    fake_opener.open.return_value = fake_resp
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.build_opener", return_value=fake_opener) as build_opener:
        FlowDrawBox.fetch_url("https://example.com/img.png")
    handlers = build_opener.call_args.args
    assert all(not isinstance(h, urllib.request.HTTPSHandler) for h in handlers)
    fake_opener.open.assert_called_once_with("https://example.com/img.png", timeout=30)


def test_fetch_url_verify_ssl_false_uses_unverified_context():
    """问题1: verify_ssl=false → 注入 HTTPSHandler 且关闭证书校验。"""
    import ssl
    import urllib.request
    fake_resp = mock.MagicMock()
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.read.side_effect = [b"x", b""]
    fake_opener = mock.MagicMock()
    fake_opener.open.return_value = fake_resp
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.build_opener", return_value=fake_opener) as build_opener:
        data = FlowDrawBox.fetch_url("https://self-signed.example/img.png", verify_ssl=False)
    assert data == b"x"
    https_handlers = [h for h in build_opener.call_args.args
                      if isinstance(h, urllib.request.HTTPSHandler)]
    assert len(https_handlers) == 1
    # HTTPSHandler 的 context 属性名随 Python 版本不同（_context / context），双取兼容
    ctx = getattr(https_handlers[0], "_context", None) or getattr(https_handlers[0], "context", None)
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_NONE


def test_fetch_url_verify_ssl_false_http_initial_injects_unverified():
    """意见7: verify_ssl=false 且初始 URL 为 http → 仍注入 unverified HTTPSHandler，
    http→https 重定向时同样不过校验证书（不再误报 UntrustedCertError）。"""
    import ssl
    import urllib.request
    fake_resp = mock.MagicMock()
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.read.side_effect = [b"x", b""]
    fake_opener = mock.MagicMock()
    fake_opener.open.return_value = fake_resp
    with mock.patch.object(_module, "illegal_url", return_value=False), \
         mock.patch("urllib.request.build_opener", return_value=fake_opener) as build_opener:
        data = FlowDrawBox.fetch_url("http://example.com/img.png", verify_ssl=False)
    assert data == b"x"
    https_handlers = [h for h in build_opener.call_args.args
                      if isinstance(h, urllib.request.HTTPSHandler)]
    assert len(https_handlers) == 1
    ctx = getattr(https_handlers[0], "_context", None) or getattr(https_handlers[0], "context", None)
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_NONE


def test_fetch_url_cert_error_raises_untrusted_error():
    """问题1: 证书校验失败 → 抛 _UntrustedCertError（与图片 404 区分）。"""
    import ssl
    import urllib.error
    fake_opener = mock.MagicMock()
    # urlopen 实际将证书错误包装为 URLError(reason=SSLError)，与真实链路保持一致
    fake_opener.open.side_effect = urllib.error.URLError(
        ssl.SSLCertVerificationError("certificate verify failed: self-signed"))
    with mock.patch.object(_module, "illegal_url", return_value=False), mock.patch(
        "urllib.request.build_opener", return_value=fake_opener
    ), pytest.raises(_module.UntrustedCertError) as exc:
        FlowDrawBox.fetch_url("https://self-signed.example/img.png")
    assert "verify_ssl" in str(exc.value)


@pytest.mark.asyncio
async def test_draw_boxes_untrusted_cert_returns_400_not_404():
    """问题1: draw_boxes 自签证书 URL → error_code=400（而非 404 图像加载失败）。"""
    plugin = FlowDrawBox()
    with mock.patch.object(FlowDrawBox, "fetch_url",
                           side_effect=_module.UntrustedCertError(
                               "SSL certificate verification failed: x. "
                               "Use http/base64 image input, or set verify_ssl=false")):
        result = await plugin.invoke({
            "operation": "draw_boxes",
            "image": "https://self-signed.example/a.png",
            "annotations": '{"annotations":[]}',
        })
    assert result["output"]["success"] is False
    assert result["output"]["error_code"] == 400
    assert "verify_ssl" in result["output"]["error"]


# --------------------------------------------------------------------------- #
# BUG2026102804734 问题2: coordinates 为 string 二维 JSON 全链路可用
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_find_overlaps_string_2d_coordinates():
    """问题2: coordinates 传 string 二维 JSON → find_overlaps 正常执行。"""
    plugin = FlowDrawBox()
    coordinates_str = json.dumps([
        [{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        [{"x": 5, "y": 5}, {"x": 15, "y": 15}],
    ])
    result = await plugin.invoke({"operation": "find_overlaps", "coordinates": coordinates_str})
    assert result["output"]["overlap_count"] == 1
    assert result["output"]["overlap_pairs"] == [{"box_a": 0, "box_b": 1}]


# --------------------------------------------------------------------------- #
# BUG2026102804734 问题3: 插件目录字体扫描
# --------------------------------------------------------------------------- #

def test_list_plugin_fonts_missing_dir_returns_empty(tmp_path, monkeypatch):
    """问题3: 插件目录无 fonts/ 子目录时扫描结果为空。"""
    monkeypatch.setattr(_module.os.path, "abspath", lambda p: str(tmp_path / "draw_box.py"))
    assert _module.list_plugin_fonts() == []


def test_list_plugin_fonts_returns_sorted_fonts(tmp_path, monkeypatch):
    """问题3: 插件目录 fonts/ 存在时返回排序后的字体文件（忽略非字体文件）。"""
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    for name in ["wqy-microhei.ttc", "b.TTF", "a.otf"]:
        (font_dir / name).write_bytes(b"font-data")
    (font_dir / "readme.txt").write_text("ignore me")
    monkeypatch.setattr(_module.os.path, "abspath", lambda p: str(tmp_path / "draw_box.py"))
    fonts = _module.list_plugin_fonts()
    assert len(fonts) == 3
    assert fonts[0].endswith("a.otf")
    assert fonts[-1].endswith("wqy-microhei.ttc")
