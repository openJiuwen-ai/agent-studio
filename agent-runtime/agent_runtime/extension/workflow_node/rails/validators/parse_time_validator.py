# agent_runtime/extension/workflow_node/rails/validators/parse_time_validator.py
"""
时间解析器 - parse_time

将自然语言日期时间字符串解析并格式化为标准格式
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from agent_runtime.extension.workflow_node.rails.base import ActionConfig, FormatAction

# 中文数字到阿拉伯数字的映射
CN_NUM_MAP = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def cn_to_arabic(cn_num: str) -> int:
    """将中文数字转换为阿拉伯数字"""
    if not cn_num:
        return 0
    result = 0
    for char in cn_num:
        if char in CN_NUM_MAP:
            result = result * 10 + CN_NUM_MAP[char]
    return result


def parse_cn_number(text: str) -> int:
    """解析中文数字（如"二十三" -> 23）"""
    text = text.strip()
    if not text:
        return 0

    # 处理 "十" 开头的情况（如"十三" = 13, "十" = 10）
    if text.startswith("十"):
        text = "一" + text

    result = 0
    temp = 0
    for char in text:
        if char in CN_NUM_MAP:
            val = CN_NUM_MAP[char]
            if val >= 10:
                if temp > 0:
                    result += temp * val
                else:
                    result = val
                temp = 0
            else:
                temp = val
    result += temp
    return result if result > 0 else int(text) if text.isdigit() else 0


class TimeParseAction(FormatAction):
    """时间解析 Action

    配置示例:
    ```json
    {
        "action": "parse_time",
        "action_extra_args": {
            "format": "%Y-%m-%d %H:%M"
        }
    }
    ```

    支持解析的时间格式:
    - "2024年5月20日"
    - "2024-05-20"
    - "2024/05/20"
    - "下午3点"
    - "15:30"
    - "明天上午10点"
    - "下周三"
    - "三天后"
    - "五分钟后"
    """

    # 触发词
    DATE_TRIGGER_WORDS = ["年", "月", "日", "号", "天", "周"]
    TIME_TRIGGER_WORDS = ["点", "刻", "分", "时"]

    def format_field(self, field_name: str, value: Any) -> Any:
        """解析并格式化日期时间字段"""
        if not isinstance(value, str):
            return value

        target_format = self.extra_args.get(field_name) or self.extra_args.get(
            "format", "%Y-%m-%d %H:%M"
        )
        if not target_format:
            target_format = "%Y-%m-%d %H:%M"

        parsed_time = self._parse_time(value.strip(), target_format)
        return parsed_time if parsed_time else value

    def _parse_time(self, time_str: str, target_format: str) -> str:
        """解析时间字符串"""
        # 检查是否包含时间触发词
        has_date = any(w in time_str for w in self.DATE_TRIGGER_WORDS)
        has_time = any(w in time_str for w in self.TIME_TRIGGER_WORDS)

        if not has_date and not has_time:
            return time_str

        try:
            # 纯时间（如"下午3点"）
            if has_time and not has_date:
                return self._parse_time_only(time_str, target_format)

            # 带日期的时间
            if has_date:
                return self._parse_date_time(time_str, target_format)

            return time_str
        except Exception:
            return time_str

    def _parse_time_only(self, time_str: str, target_format: str) -> str:
        """解析纯时间表达式"""
        now = datetime.now(tz=timezone.utc) + timedelta(hours=8)

        # 处理相对时间
        relative_result = self._parse_relative_time(time_str, now, target_format)
        if relative_result:
            return relative_result

        # 解析"上午/下午/晚上" + 数字时间
        time_patterns = [
            (
                r"上午\s*(\d{1,2})[:：]?(\d{1,2})?",
                lambda m: self._format_time(
                    now, int(m.group(1)), int(m.group(2) or 0), 0, target_format, False
                ),
            ),
            (
                r"下午\s*(\d{1,2})[:：]?(\d{1,2})?",
                lambda m: self._format_time(
                    now, int(m.group(1)), int(m.group(2) or 0), 0, target_format, True
                ),
            ),
            (
                r"晚上\s*(\d{1,2})[:：]?(\d{1,2})?",
                lambda m: self._format_time(
                    now, int(m.group(1)), int(m.group(2) or 0), 0, target_format, True
                ),
            ),
            (
                r"凌晨\s*(\d{1,2})[:：]?(\d{1,2})?",
                lambda m: self._format_time(
                    now, int(m.group(1)), int(m.group(2) or 0), 0, target_format, False
                ),
            ),
            (
                r"(\d{1,2})[:：](\d{1,2})",
                lambda m: self._format_time(
                    now, int(m.group(1)), int(m.group(2)), 0, target_format, False
                ),
            ),
            (
                r"(\d{1,2})点",
                lambda m: self._format_time(
                    now, int(m.group(1)), 0, 0, target_format, False
                ),
            ),
            (
                r"(\d{1,2})[:：]?(\d{1,2})?分",
                lambda m: self._format_time(
                    now,
                    int(m.group(1) or 0),
                    int(m.group(2) or 0),
                    0,
                    target_format,
                    False,
                ),
            ),
        ]

        for pattern, parser in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                return parser(match)

        return time_str

    def _parse_date_time(self, time_str: str, target_format: str) -> str:
        """解析日期时间表达式"""
        now = datetime.now(tz=timezone.utc) + timedelta(hours=8)

        # 处理相对日期
        relative_result = self._parse_relative_date(time_str, now, target_format)
        if relative_result:
            return relative_result

        # 处理具体日期
        # 格式: YYYY年MM月DD日 或 YYYY-MM-DD 或 YYYY/MM/DD
        date_patterns = [
            r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})[日号]?\s*(\d{1,2})[:：](\d{1,2})",
            r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})[日号]?",
            r"(\d{1,2})[月/\-](\d{1,2})[日号]?",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, time_str)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    year = int(groups[0]) if len(groups[0]) == 4 else now.year
                    month = int(groups[1])
                    day = int(groups[2])
                    hour = int(groups[3]) if len(groups) > 3 else 0
                    minute = int(groups[4]) if len(groups) > 4 else 0

                    # 处理下午
                    if ("下午" in time_str or "晚上" in time_str) and hour < 12:
                        hour += 12

                    try:
                        dt = datetime(year, month, day, hour, minute)
                        return dt.strftime(target_format)
                    except ValueError:
                        continue

        return time_str

    def _parse_relative_time(
        self, time_str: str, base_time: datetime, target_format: str
    ) -> str:
        """解析相对时间表达式（如"五分钟后"）"""
        relative_patterns = [
            (
                r"(\d+)\s*分钟\s*(?:后|以后)",
                lambda m: base_time + timedelta(minutes=int(m.group(1))),
            ),
            (
                r"(\d+)\s*小时\s*(?:后|以后)",
                lambda m: base_time + timedelta(hours=int(m.group(1))),
            ),
            (
                r"(\d+)\s*秒\s*(?:后|以后)",
                lambda m: base_time + timedelta(seconds=int(m.group(1))),
            ),
        ]

        for pattern, delta_func in relative_patterns:
            match = re.search(pattern, time_str)
            if match:
                return delta_func(match).strftime(target_format)

        return None

    def _parse_relative_date(
        self, time_str: str, base_time: datetime, target_format: str
    ) -> str:
        """解析相对日期表达式（如"明天"、"三天后"）"""
        relative_date_patterns = [
            (r"今天", lambda: base_time),
            (r"明天", lambda: base_time + timedelta(days=1)),
            (r"后天", lambda: base_time + timedelta(days=2)),
            (r"大后天", lambda: base_time + timedelta(days=3)),
            (r"昨天", lambda: base_time - timedelta(days=1)),
            (r"前天", lambda: base_time - timedelta(days=2)),
            (r"大前天", lambda: base_time - timedelta(days=3)),
            (
                r"(\d+)\s*天\s*(?:后|以后)",
                lambda m: base_time + timedelta(days=int(m.group(1))),
            ),
            (
                r"(\d+)\s*天\s*(?:前|以前)",
                lambda m: base_time - timedelta(days=int(m.group(1))),
            ),
        ]

        for pattern, day_func in relative_date_patterns:
            if re.search(pattern, time_str):
                dt = day_func()
                # 检查是否有时间
                time_match = re.search(r"(\d{1,2})[:：]?(\d{1,2})?", time_str)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2) or 0)
                    if ("下午" in time_str or "晚上" in time_str) and hour < 12:
                        hour += 12
                    dt = dt.replace(hour=hour, minute=minute)
                return dt.strftime(target_format)

        # 处理"下周一"等
        weekday_match = re.search(r"下下周?([一二三四五六日])", time_str)
        if weekday_match:
            weekday_cn = weekday_match.group(1)
            weekday_map = {
                "一": 0,
                "二": 1,
                "三": 2,
                "四": 3,
                "五": 4,
                "六": 5,
                "日": 6,
            }
            target_weekday = weekday_map.get(weekday_cn)
            if target_weekday is not None:
                days_ahead = (target_weekday - base_time.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                dt = base_time + timedelta(days=days_ahead)
                return dt.strftime(target_format)

        return None

    def _format_time(
        self,
        base_time: datetime,
        hour: int,
        minute: int,
        second: int,
        target_format: str,
        is_pm: bool,
    ) -> str:
        """格式化时间"""
        if is_pm and hour < 12:
            hour += 12
        dt = base_time.replace(hour=hour, minute=minute, second=second)
        return dt.strftime(target_format)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行时间解析"""
        args = context.get("arguments", {})
        formatted_args = {}

        for key in args.keys():
            value = args.get(key)
            if value is None:
                formatted_args[key] = None
                continue

            formatted_args[key] = self.format_field(key, value)

        return {"arguments": formatted_args}


async def parse_time(
    context: Dict[str, Any] = None, config: ActionConfig = None
) -> Dict[str, Any]:
    """时间解析 action 函数"""
    if config is None and context is not None:
        component_config = context.get("component_config", {})
        rails_config = component_config.get("railsConfig", {})
        actions_config = rails_config.get("actions_config", [])
        for ac in actions_config:
            if ac.get("action") == "parse_time":
                config = ActionConfig(ac.get("action_extra_args", {}))
                break

    if config is None:
        return {"arguments": context.get("arguments", {})}

    action = TimeParseAction(config)
    return await action.async_execute(context or {})
