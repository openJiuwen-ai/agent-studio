import asyncio
import base64
import io
import json
import math
import os
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlparse

from jiuwen.common.utils.utils import illegal_url
from jiuwen.extension.wrapper.plugin_base import PluginBase


class SSRFSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """每个重定向目标都过 illegal_url 校验，防止 SSRF 重定向绕过。"""

    def redirect_request(self, *args, **kwargs):
        newurl = args[-1] if args else kwargs.get("newurl", "")
        if illegal_url(newurl):
            raise ValueError(
                f"Redirect URL is illegal or points to an internal network address: {newurl}"
            )
        return super().redirect_request(*args, **kwargs)


class UntrustedCertError(RuntimeError):
    """HTTPS 证书校验失败（自签/不受信证书），与图片 404 区分开。"""


def list_plugin_fonts():
    """扫描插件目录 fonts/ 子目录下的字体文件，支持插件包自包含中文字体。"""
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    if not os.path.isdir(font_dir):
        return []
    return sorted(
        os.path.join(font_dir, f)
        for f in os.listdir(font_dir)
        if f.lower().endswith((".ttf", ".ttc", ".otf"))
    )


class FlowDrawBox(PluginBase):
    """画布框选交互插件

    支持四种框选操作：
    - calculate_area: 计算框选区域面积、中心点和边界
    - find_overlaps: 检测多组框选区域之间的重叠
    - merge_boxes: 合并重叠的框选区域
    - draw_boxes: 在图像上绘制边界框和标签
    """

    _MAX_IMAGE_SIZE = 4096
    _MAX_ANNOTATIONS = 100
    _MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    _DEFAULT_BOX_COLOR = "#ff0000"
    _DEFAULT_TEXT_COLOR = "#ffffff"
    _DEFAULT_LINE_WIDTH = 2
    _DEFAULT_FONT_SIZE = 16
    _ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".ico")

    FONT_CANDIDATES = list_plugin_fonts() + [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        operation = inputs.get("operation", "calculate_area")

        if operation == "draw_boxes":
            return {"output": await asyncio.to_thread(self._draw_boxes, inputs)}

        coordinates = inputs.get("coordinates", [])
        if coordinates is None or (isinstance(coordinates, str) and not coordinates.strip()):
            # 空坐标输入与 schema 非必填/默认空串契约一致，按空列表处理
            coordinates = []
        elif isinstance(coordinates, str):
            try:
                coordinates = json.loads(coordinates)
            except json.JSONDecodeError as e:
                return {"output": {"success": False, "error": f"coordinates JSON 解析失败: {e}", "error_code": 400}}

        handler = {
            "calculate_area": self._calc_area,
            "find_overlaps": self._find_overlaps,
            "merge_boxes": self._merge_boxes,
        }.get(operation, self._calc_area)

        return {"output": handler(coordinates)}

    def _draw_boxes(self, inputs):
        """在图像上绘制边界框和标签，返回标注后图像的 base64。"""
        try:
            from PIL import Image, ImageColor, ImageDraw, ImageFont
        except ImportError:
            return {
                "success": False,
                "error": "Pillow is required for draw_boxes operation",
                "error_code": 500,
            }

        image_input = inputs.get("image")
        if not image_input:
            return {"success": False, "error": "image is required", "error_code": 400}

        try:
            # verify_ssl 显式布尔校验：仅 bool 值生效，非 bool（如 "false"/null）回退默认 True
            raw_verify_ssl = inputs.get("verify_ssl", True)
            verify_ssl = raw_verify_ssl if isinstance(raw_verify_ssl, bool) else True
            image_bytes = self._resolve_image_bytes(image_input, verify_ssl)
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                if width > self._MAX_IMAGE_SIZE or height > self._MAX_IMAGE_SIZE:
                    return {
                        "success": False,
                        "error": f"Image too large (max {self._MAX_IMAGE_SIZE}x{self._MAX_IMAGE_SIZE})",
                        "error_code": 413,
                    }
                image = img.copy()
        except UntrustedCertError as e:
            return {"success": False, "error": str(e), "error_code": 400}
        except Exception as e:
            return {"success": False, "error": f"Image loading failed: {e}", "error_code": 404}

        annotations_input = inputs.get("annotations")
        # 空标注输入"仅绘制图像不画框"（与 schema 非必填/默认空串契约一致）
        if annotations_input is None or (
            isinstance(annotations_input, str) and not annotations_input.strip()
        ):
            annotations = []
        else:
            try:
                annotations_data = (
                    json.loads(annotations_input)
                    if isinstance(annotations_input, str)
                    else annotations_input
                )
                annotations = (
                    annotations_data.get("annotations", [])
                    if isinstance(annotations_data, dict)
                    else annotations_data
                )
            except (json.JSONDecodeError, TypeError) as e:
                return {"success": False, "error": f"Invalid annotation format: {e}", "error_code": 422}

        if not isinstance(annotations, list):
            return {"success": False, "error": "annotations must be a list", "error_code": 422}

        if len(annotations) > self._MAX_ANNOTATIONS:
            return {
                "success": False,
                "error": f"Too many annotations (max {self._MAX_ANNOTATIONS})",
                "error_code": 400,
            }

        box_color = inputs.get("box_color", self._DEFAULT_BOX_COLOR)
        text_color = inputs.get("text_color", self._DEFAULT_TEXT_COLOR)
        try:
            ImageColor.getrgb(box_color)
            ImageColor.getrgb(text_color)
        except Exception:
            return {
                "success": False,
                "error": f"Invalid color format: box_color={box_color}, text_color={text_color}",
                "error_code": 400,
            }
        line_width = self.clamp(inputs.get("line_width", self._DEFAULT_LINE_WIDTH), 1, 20)
        font_size = self.clamp(inputs.get("font_size", self._DEFAULT_FONT_SIZE), 8, 72)
        coordinate_type = inputs.get("coordinate_type", "relative")
        if coordinate_type not in ("relative", "absolute"):
            return {
                "success": False,
                "error": f"Invalid coordinate_type '{coordinate_type}', must be 'relative' or 'absolute'",
                "error_code": 400,
            }

        if image.mode != "RGB":
            image = image.convert("RGB")
        draw = ImageDraw.Draw(image)
        font = self.load_font(ImageFont, font_size)

        drawn = 0
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            try:
                bbox = ann.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                try:
                    x1, y1, x2, y2 = [float(v) for v in bbox]
                except (TypeError, ValueError):
                    continue
                if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
                    continue
                if coordinate_type == "relative":
                    x1 = x1 * width / 1000
                    y1 = y1 * height / 1000
                    x2 = x2 * width / 1000
                    y2 = y2 * height / 1000

                draw.rectangle([x1, y1, x2, y2], outline=box_color, width=line_width)
                drawn += 1

                label = ann.get("label", "")
                confidence = ann.get("confidence")
                if confidence is not None:
                    try:
                        confidence_val = float(confidence)
                    except (TypeError, ValueError):
                        confidence_val = None
                    if confidence_val is not None:
                        label = f"{label} {confidence_val:.2f}" if label else f"{confidence_val:.2f}"

                if label:
                    text_xy = (x1 + line_width, y1 + line_width)
                    try:
                        bbox_text = draw.textbbox(text_xy, label, font=font)
                        draw.rectangle(
                            [bbox_text[0], bbox_text[1], bbox_text[2], bbox_text[3]],
                            fill=box_color,
                        )
                        draw.text(text_xy, label, fill=text_color, font=font)
                    except Exception:
                        draw.text(text_xy, label, fill=text_color)
            except (TypeError, ValueError, OSError):
                continue

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_base64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return {
            "success": True,
            "annotation_count": drawn,
            "image_size": {"width": width, "height": height},
            "image_base64": image_base64,
            "message": f"Successfully drew {drawn} annotations",
        }

    @staticmethod
    def clamp(value, lo, hi):
        try:
            v = int(value)
        except (TypeError, ValueError):
            v = lo
        return max(lo, min(hi, v))

    @staticmethod
    def validate_image_path(path):
        """校验本地文件路径：扩展名必须为图片类型，文件大小不能超过上限。"""
        if not path.lower().endswith(FlowDrawBox._ALLOWED_IMAGE_EXTS):
            raise ValueError(f"Path must point to an image file (allowed: {FlowDrawBox._ALLOWED_IMAGE_EXTS})")
        file_size = os.path.getsize(path)
        if file_size > FlowDrawBox._MAX_DOWNLOAD_SIZE:
            raise ValueError(f"Image file too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")

    def _resolve_image_bytes(self, image_input, verify_ssl=True):
        """兼容文件对象(dict/JSON string) / URL / 本地路径 / base64 多种格式。"""
        if isinstance(image_input, dict):
            if "binary" in image_input:
                data = image_input["binary"]
                if isinstance(data, str):
                    if len(data) > FlowDrawBox._MAX_DOWNLOAD_SIZE * 2:
                        raise ValueError(f"Image data too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
                    data = base64.b64decode(data)
                if len(data) > FlowDrawBox._MAX_DOWNLOAD_SIZE:
                    raise ValueError(f"Image data too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
                return data
            url = image_input.get("url")
            if url:
                return self.fetch_url(url, verify_ssl)
            path = image_input.get("path")
            if path:
                self.validate_image_path(path)
                with open(path, "rb") as f:
                    return f.read()
            raise ValueError("dict image must contain non-empty binary/url/path")

        if isinstance(image_input, str):
            if image_input.startswith("{"):
                try:
                    return self._resolve_image_bytes(json.loads(image_input), verify_ssl)
                except json.JSONDecodeError:
                    pass
            if image_input.startswith(("http://", "https://")):
                return self.fetch_url(image_input, verify_ssl)
            if os.path.exists(image_input):
                self.validate_image_path(image_input)
                with open(image_input, "rb") as f:
                    return f.read()
            if len(image_input) > FlowDrawBox._MAX_DOWNLOAD_SIZE * 2:
                raise ValueError(f"Image data too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
            try:
                decoded = base64.b64decode(image_input)
            except Exception as e:
                raise ValueError("Unsupported image string format") from e
            if len(decoded) > FlowDrawBox._MAX_DOWNLOAD_SIZE:
                raise ValueError(f"Image data too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
            return decoded

        raise ValueError(f"Unsupported image type: {type(image_input)}")

    @staticmethod
    def fetch_url(url, verify_ssl=True):
        if illegal_url(url):
            raise ValueError("URL is illegal or points to an internal network address")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Only http/https URLs are allowed, got scheme: {parsed.scheme}")
        handlers = [SSRFSafeRedirectHandler]
        if parsed.scheme == "https" and not verify_ssl:
            # 关闭证书校验仅用于测试/内网自签证书场景，验证逻辑仍走同一 SSRF 防护链。
            # 使用公开 API 构造不校验对端的上下文（避免依赖受保护的 _create_unverified_context）
            unverified_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            unverified_context.check_hostname = False
            unverified_context.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=unverified_context))
        opener = urllib.request.build_opener(*handlers)
        try:
            with opener.open(url, timeout=30) as resp:
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    try:
                        cl_val = int(content_length)
                    except (TypeError, ValueError):
                        cl_val = 0
                    if cl_val > FlowDrawBox._MAX_DOWNLOAD_SIZE:
                        raise ValueError(f"Image file too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
                chunks = []
                total = 0
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > FlowDrawBox._MAX_DOWNLOAD_SIZE:
                        raise ValueError(f"Image file too large (max {FlowDrawBox._MAX_DOWNLOAD_SIZE} bytes)")
                    chunks.append(chunk)
                return b"".join(chunks)
        except urllib.error.URLError as e:
            # urlopen 会把 SSL 证书错误包装为 URLError(reason=SSLError)，解开单独归类
            if isinstance(e.reason, ssl.SSLError):
                raise UntrustedCertError(
                    f"SSL certificate verification failed: {e.reason}. "
                    "The certificate may be self-signed or untrusted. "
                    "Use http/base64 image input, or set verify_ssl=false (test environments only)."
                ) from e
            raise

    def load_font(self, image_font, font_size):
        for path in self.FONT_CANDIDATES:
            if os.path.exists(path):
                try:
                    return image_font.truetype(path, font_size)
                except OSError:
                    continue
        try:
            return image_font.load_default(size=font_size)
        except TypeError:
            return image_font.load_default()

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
