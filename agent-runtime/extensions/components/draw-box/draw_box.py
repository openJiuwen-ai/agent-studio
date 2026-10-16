import json

from jiuwen.extension.wrapper.plugin_base import PluginBase


class FlowDrawBox(PluginBase):
    """画布框选交互插件

    支持三种框选数据分析操作：
    - calculate_area: 计算框选区域面积、中心点和边界
    - find_overlaps: 检测多组框选区域之间的重叠
    - merge_boxes: 合并重叠的框选区域

    一个插件通过 operation 参数支持多种操作。
    """

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        operation = inputs.get("operation", "calculate_area")
        coordinates = inputs.get("coordinates", [])
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)

        handler = {
            "calculate_area": self._calc_area,
            "find_overlaps": self._find_overlaps,
            "merge_boxes": self._merge_boxes,
        }.get(operation, self._calc_area)

        return {"output": handler(coordinates)}

    def _calc_area(self, coordinates):
        if not coordinates or len(coordinates) < 2:
            return {
                "operation": "calculate_area",
                "area": 0,
                "center": None,
                "bounds": None,
                "point_count": len(coordinates) if coordinates else 0,
            }

        xs = [p.get("x", 0) for p in coordinates]
        ys = [p.get("y", 0) for p in coordinates]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        area = (max_x - min_x) * (max_y - min_y)
        center = {"x": (min_x + max_x) / 2, "y": (min_y + max_y) / 2}

        return {
            "operation": "calculate_area",
            "area": area,
            "center": center,
            "bounds": {
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
            },
            "point_count": len(coordinates),
        }

    @staticmethod
    def _boxes_overlap(a: dict, b: dict) -> bool:
        """判断两个矩形框是否重叠（不含边界相切）。"""
        return (
            a["min_x"] < b["max_x"] and a["max_x"] > b["min_x"]
            and a["min_y"] < b["max_y"] and a["max_y"] > b["min_y"]
        )

    @staticmethod
    def _merge_two(a: dict, b: dict) -> dict:
        """合并两个矩形框，返回包含两者的最小外接矩形。"""
        return {
            "min_x": min(a["min_x"], b["min_x"]),
            "max_x": max(a["max_x"], b["max_x"]),
            "min_y": min(a["min_y"], b["min_y"]),
            "max_y": max(a["max_y"], b["max_y"]),
        }

    def _find_overlaps(self, box_groups):
        if not box_groups or not isinstance(box_groups, list):
            return {
                "operation": "find_overlaps",
                "overlap_pairs": [],
                "overlap_count": 0,
            }

        boxes = self._parse_box_groups(box_groups, with_index=True)

        overlap_pairs = []
        for i, a in enumerate(boxes):
            for j in range(i + 1, len(boxes)):
                b = boxes[j]
                if self._boxes_overlap(a, b):
                    overlap_pairs.append({"box_a": a["index"], "box_b": b["index"]})

        return {
            "operation": "find_overlaps",
            "overlap_pairs": overlap_pairs,
            "overlap_count": len(overlap_pairs),
        }

    def _merge_boxes(self, box_groups):
        if not box_groups or not isinstance(box_groups, list):
            return {
                "operation": "merge_boxes",
                "merged_boxes": [],
                "box_count": 0,
            }

        boxes = self._parse_box_groups(box_groups)
        if not boxes:
            return {
                "operation": "merge_boxes",
                "merged_boxes": [],
                "box_count": 0,
            }

        merged = list(boxes)
        changed = True
        while changed:
            changed = False
            for i, box_a in enumerate(merged):
                for j in range(i + 1, len(merged)):
                    if self._boxes_overlap(box_a, merged[j]):
                        box_a = self._merge_two(box_a, merged[j])
                        merged[i] = box_a
                        merged.pop(j)
                        changed = True
                        break
                if changed:
                    break

        return {
            "operation": "merge_boxes",
            "merged_boxes": merged,
            "box_count": len(merged),
        }

    @staticmethod
    def _parse_box_groups(box_groups, with_index=False):
        """将坐标组列表解析为矩形边界框列表。"""
        boxes = []
        for i, group in enumerate(box_groups):
            if isinstance(group, str):
                group = json.loads(group)
            if not group or len(group) < 2:
                continue
            xs = [p.get("x", 0) for p in group]
            ys = [p.get("y", 0) for p in group]
            box = {
                "min_x": min(xs), "max_x": max(xs),
                "min_y": min(ys), "max_y": max(ys),
            }
            if with_index:
                box["index"] = i
            boxes.append(box)
        return boxes
