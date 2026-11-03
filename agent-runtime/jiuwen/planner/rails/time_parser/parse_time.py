# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

import datetime
import re
import time

from jiuwen.planner.rails.time_parser.cn_date import LunarSolarDate
from jiuwen.planner.rails.time_parser.time_utils import (
    TimeUtility,
    TOMORROW_ZH,
    INPUT_TIME_ERROR,
    DAY_EN,
    MONTH,
    WEEK_EN,
    TimePoint,
    SPANS,
    INFOS,
    TimeParserResult,
    ILLEGAL_TIME_STRING_ERROR,
    TimeHandlerResult,
    TimeHandlerFuncResult,
)


class TimeParser(TimeUtility):
    def __init__(self):
        super(TimeParser, self).__init__()
        self.tp = None
        self.base_handler = None
        self.future = None
        self.ret_future = False
        self.lunar_date = False

        self.solar_terms = {
            "小寒": [5.4055, "1", (2019, -1), (1982, 1)],
            "大寒": [20.12, "1", (2082, 1)],
            "立春": [3.87, "2", (None, 0)],
            "雨水": [18.73, "2", (2026, -1)],
            "惊蛰": [5.63, "3", (None, 0)],
            "春分": [20.646, "3", (2084, 1)],
            "清明": [4.81, "4", (None, 0)],
            "谷雨": [20.1, "4", (None, 0)],
            "立夏": [5.52, "5", (1911, 1)],
            "小满": [21.04, "5", (2008, 1)],
            "芒种": [5.678, "6", (1902, 1)],
            "夏至": [21.37, "6", (None, 0)],
            "小暑": [7.108, "7", (2016, 1), (1925, 1)],
            "大暑": [22.83, "7", (1922, 1)],
            "立秋": [7.5, "8", (2002, 1)],
            "处暑": [23.13, "8", (None, 0)],
            "白露": [7.646, "9", (1927, 1)],
            "秋分": [23.042, "9", (None, 0)],
            "寒露": [8.318, "10", (2088, 0)],
            "霜降": [23.438, "10", (2089, 1)],
            "立冬": [7.438, "11", (2089, 1)],
            "小雪": [22.36, "11", (1978, 0)],
            "大雪": [7.18, "12", (1954, 1)],
            "冬至": [21.94, "12", (2021, -1), (1918, -1)],
        }
        self.lunar2solar = LunarSolarDate()._to_solar_date
        self.ymd_reg_norm_funcs = None
        self.hms_reg_norm_funcs = None
        self.future_time_unit_reg = re.compile("(年|月|周|星期|礼拜|日|号|节|时|点)")
        self.future_time_unit_hms_reg = re.compile("(时|点|分)")
        chinese_num = "零〇一二三四五六七八九"
        arabic_num = "00123456789"
        self.chinese_num_2_arabic_num = str.maketrans(chinese_num, arabic_num)
        self.future_time = "inf"
        self.past_time = "-inf"
        self.string_strict = False

    def __call__(self, time_str: str = "", time_base=time.time(), ret_future=False):
        if self.future is None:
            self._preprocess()

        self.ret_future = ret_future
        self.lunar_date = True

        time_str = TimeParser._cleansing(time_str)

        self.base_handler = TimeParser._convert_time_base2handler(time_base)

        legal = TimeUtility.check_handler(self.base_handler) and (
            self.base_handler[0] != -1
        )
        if not legal:
            raise ValueError("The given time base is illegal.")

        full_time_handler_1, full_time_handler_2, time_type = (
            self.parse_time_span_point(time_str)
        )

        first_standard_time_str, second_standard_time_str = (
            self.time_handler2standard_time(full_time_handler_1, full_time_handler_2)
        )

        return {
            "type": time_type,
            "time": [first_standard_time_str, second_standard_time_str],
        }

    @staticmethod
    def parse_pattern(time_string, pattern):
        """公共解析函数"""
        searched_res = pattern.search(time_string)
        if searched_res:
            return searched_res.group()
        return ""

    @staticmethod
    def handle_cur_ymd_hms(cur_hms, cur_hms_func, cur_ymd, cur_ymd_func):
        """handle_cur_ymd_hms"""
        day_bias = 0
        if cur_ymd and not cur_hms:
            time_handler_1, time_handler_2, time_type = cur_ymd_func(cur_ymd)

        elif cur_ymd and cur_hms:
            ymd_handler_1, ymd_handler_2, _ = cur_ymd_func(cur_ymd)

            if (ymd_handler_1 != ymd_handler_2) or ymd_handler_1[2] == -1:
                raise ValueError(
                    "the str is illegal, "
                    "because the hour-min-sec str can NOT be designated to a specific day."
                )

            # hms_time_type is always "time_point"
            hms_handler_1, hms_handler_2, day_bias = cur_hms_func(cur_hms)

            time_handler_1 = [max(i, j) for i, j in zip(ymd_handler_1, hms_handler_1)]
            time_handler_2 = [max(i, j) for i, j in zip(ymd_handler_1, hms_handler_2)]
            time_type = "time_point"

        elif not cur_ymd and cur_hms:
            time_handler_1, time_handler_2, day_bias = cur_hms_func(cur_hms)
            time_type = "time_point"
        else:
            raise ValueError("can not parse the time_str.")
        return TimeHandlerResult(day_bias, time_handler_1, time_handler_2, time_type)

    @staticmethod
    def _year_completion(year_str, time_base_handler):
        if len(year_str) == 2:
            year_base = str(time_base_handler[0])
            if year_base[:2] in ["17", "18", "19"]:
                return year_base[:2] + year_str
            if year_base[:2] == "20":
                if int(year_str) > int(year_base[2:]) + 10:
                    century = "19"
                else:
                    century = year_base[:2]
                return century + year_str
            raise ValueError("maybe the `year` can not be parsed.")
        return year_str

    @staticmethod
    def _check_weekday(time_base_datetime):
        if time_base_datetime.weekday() <= 4:
            return True
        return False

    @staticmethod
    def _get_norm_month_order_week(day_1, day_offset):
        day_weekday_1 = int(day_1.strftime("%w"))
        if day_weekday_1 == 1:
            pass  # Monday: day_offset unchanged.
        elif day_weekday_1 == 0:
            day_offset += 1
        else:
            day_offset += 7 + 1 - day_weekday_1

        point_day_1 = day_1 + datetime.timedelta(days=day_offset - 7)
        point_day_2 = day_1 + datetime.timedelta(days=day_offset - 1)

        return point_day_1, point_day_2

    @staticmethod
    def _get_norm_solar_season_one(_season):
        if "初" in _season:
            _month_1 = 1
            _month_2 = 1
        elif "中" in _season:
            _month_1 = 2
            _month_2 = 2
        elif "末" in _season:
            _month_1 = 3
            _month_2 = 3
        else:
            _month_1 = 1
            _month_2 = 3
        return _month_1, _month_2

    @staticmethod
    def _get_norm_solar_season_two(_season):
        if "初" in _season:
            _month_1 = 4
            _month_2 = 4
        elif "中" in _season:
            _month_1 = 5
            _month_2 = 5
        elif "末" in _season:
            _month_1 = 6
            _month_2 = 6
        else:
            _month_1 = 4
            _month_2 = 6
        return _month_1, _month_2

    @staticmethod
    def _get_norm_solar_season_three(_season):
        if "初" in _season:
            _month_1 = 7
            _month_2 = 7
        elif "中" in _season:
            _month_1 = 8
            _month_2 = 8
        elif "末" in _season:
            _month_1 = 9
            _month_2 = 9
        else:
            _month_1 = 7
            _month_2 = 9
        return _month_1, _month_2

    @staticmethod
    def _get_norm_solar_season_four(_season):
        if "初" in _season:
            _month_1 = 10
            _month_2 = 10
        elif "中" in _season:
            _month_1 = 11
            _month_2 = 11
        elif "末" in _season:
            _month_1 = 12
            _month_2 = 12
        else:
            _month_1 = 10
            _month_2 = 12
        return _month_1, _month_2

    @staticmethod
    def _convert_handler2datetime(handler):
        """将 time handler 转换为 datetime 类型

        :param handler:
        :return:
        """
        new_handler = []
        for idx, i in enumerate(handler):
            if i > -1:
                new_handler.append(i)
            else:
                if idx in [0, 1, 2]:
                    new_handler.append(1)  # 月、日 从 1 开始计数
                elif idx in [3, 4, 5]:
                    new_handler.append(0)  # 时分秒从 0 开始计数

        return datetime.datetime(*new_handler)

    @staticmethod
    def _time_point():
        return TimePoint(), TimePoint()

    def norm_limit_month(self, time_str):
        """norm_limit_month method"""
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp, second_tp = self._norm_limit_month(
            time_str, self.base_handler, first_tp, second_tp
        )

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_point"

    def normalize_day_delta_point(self, time_string):
        """解析 time delta 日的 point 时间"""
        if self.base_handler[2] == -1:
            raise ValueError(
                "the time_base `{}` is lack of day, "
                "causing an error for the string `{}`.".format(
                    self.base_handler, time_string
                )
            )
        time_day_delta, _ = self._normalize_delta_unit(
            time_string, self.day_delta_pattern
        )

        time_base_datetime = TimeParser._convert_handler2datetime(self.base_handler)
        time_type = "time_span"
        if "之前" in time_string or "以前" in time_string:
            first_time_handler, second_time_handler = self.handle_before_string(
                time_base_datetime, time_day_delta
            )
        elif "前" in time_string:
            first_time_handler, second_time_handler = self.handle_single_before_string(
                time_base_datetime, time_day_delta, time_string
            )
        elif "之后" in time_string or "以后" in time_string:
            first_time_handler, second_time_handler = self.handle_after_string(
                time_base_datetime, time_day_delta
            )
        elif "后" in time_string:
            first_time_handler, second_time_handler = self.handle_single_after_string(
                time_base_datetime, time_day_delta, time_string
            )
        elif "内" in time_string:
            first_time_handler, second_time_handler = self.handle_in_string(
                time_base_datetime, time_day_delta
            )
        elif "来" in time_string:
            first_time_handler, second_time_handler = self.handle_blur_string(
                time_base_datetime, time_day_delta
            )
        else:
            raise ValueError(ILLEGAL_TIME_STRING_ERROR.format(time_string))

        return first_time_handler, second_time_handler, time_type

    def handle_blur_string(self, time_base_datetime, time_day_delta):
        """处理包含‘来’字的时间语义"""
        cur_datetime = time_base_datetime - datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        if int(time_day_delta) == time_day_delta:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        second_time_handler = self.base_handler
        return first_time_handler, second_time_handler

    def handle_in_string(self, time_base_datetime, time_day_delta):
        """处理包含‘内’字的时间语义"""
        cur_datetime = time_base_datetime + datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        first_time_handler = self.base_handler
        if int(time_day_delta) == time_day_delta:
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        return first_time_handler, second_time_handler

    def handle_single_after_string(
        self, time_base_datetime, time_day_delta, time_string
    ):
        """处理包含‘后’字的时间语义"""
        cur_datetime = time_base_datetime + datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        if int(time_day_delta) == time_day_delta:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        if time_day_delta == 0.5:
            second_datetime = cur_datetime + datetime.timedelta(days=0.5)
        elif time_day_delta >= 1:
            second_datetime = cur_datetime
        else:
            raise ValueError(ILLEGAL_TIME_STRING_ERROR.format(time_string))
        second_time_handler = TimeParser._convert_time_base2handler(second_datetime)
        if int(time_day_delta) == time_day_delta:
            second_time_handler = [
                second_time_handler[0],
                second_time_handler[1],
                second_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            second_time_handler = [
                second_time_handler[0],
                second_time_handler[1],
                second_time_handler[2],
                second_time_handler[3],
                -1,
                -1,
            ]
        return first_time_handler, second_time_handler

    def handle_after_string(self, time_base_datetime, time_day_delta):
        """处理包含‘之后’ ，‘以后’字的时间语义"""
        cur_datetime = time_base_datetime + datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        if int(time_day_delta) == time_day_delta:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            first_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        second_time_handler = self.future_time
        return first_time_handler, second_time_handler

    def handle_single_before_string(
        self, time_base_datetime, time_day_delta, time_string
    ):
        """处理包含‘前’字的时间语义"""
        cur_datetime = time_base_datetime - datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        if int(time_day_delta) == time_day_delta:  # 是整数，按整数返回
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        if time_day_delta == 0.5:
            first_datetime = cur_datetime - datetime.timedelta(days=0.5)
        elif time_day_delta >= 1:
            first_datetime = cur_datetime
        else:
            raise ValueError(ILLEGAL_TIME_STRING_ERROR.format(time_string))
        first_time_handler = TimeParser._convert_time_base2handler(first_datetime)
        if int(time_day_delta) == time_day_delta:  # 是整数，按整数返回
            first_time_handler = [
                first_time_handler[0],
                first_time_handler[1],
                first_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            first_time_handler = [
                first_time_handler[0],
                first_time_handler[1],
                first_time_handler[2],
                first_time_handler[3],
                -1,
                -1,
            ]
        return first_time_handler, second_time_handler

    def handle_before_string(self, time_base_datetime, time_day_delta):
        """处理包含‘之前’，‘以前’的时间语义"""
        cur_datetime = time_base_datetime - datetime.timedelta(days=time_day_delta)
        cur_time_handler = TimeParser._convert_time_base2handler(cur_datetime)
        first_time_handler = self.past_time
        if int(time_day_delta) == time_day_delta:  # 是整数，按整数返回
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                -1,
                -1,
                -1,
            ]
        else:
            second_time_handler = [
                cur_time_handler[0],
                cur_time_handler[1],
                cur_time_handler[2],
                cur_time_handler[3],
                -1,
                -1,
            ]
        return first_time_handler, second_time_handler

    def chinese_year_char_2_arabic_year_char(self, char_year):
        """将 二零一九 年份转化为 2019"""
        arabic_year_char = char_year.translate(self.chinese_num_2_arabic_num)
        return arabic_year_char

    def parse_tp(self, time_str, time_base_handler):
        """parse tp"""
        time_parser_result = self.get_cur_ymd_hms(time_str)

        handle_result = self.handle_cur_ymd_hms(
            time_parser_result.cur_hms,
            time_parser_result.cur_hms_func,
            time_parser_result.cur_ymd,
            time_parser_result.cur_ymd_func,
        )

        day_bias = handle_result.day_bias
        time_handler_1 = handle_result.time_handler_1
        time_handler_2 = handle_result.time_handler_2
        time_type = handle_result.time_type
        legal = TimeUtility.check_handler(time_handler_1)
        if not legal:
            raise ValueError(INPUT_TIME_ERROR)

        full_handler_1 = TimeUtility.time_completion(time_handler_1, time_base_handler)
        full_handler_2 = TimeUtility.time_completion(time_handler_2, time_base_handler)

        if day_bias == 1:
            full_handler_1, full_handler_2 = self._get_parse_tp_day_bias(
                full_handler_1, full_handler_2
            )

        return full_handler_1, full_handler_2, time_type

    def get_cur_ymd_hms(self, time_str):
        """get_cur_ymd_hms"""
        res = self.generate_func_list(time_str)
        hms_funcs = res.hms_func_list
        hms_strings = res.hms_string_list
        ymd_funcs = res.ymd_func_list
        ymd_strings = res.ymd_string_list
        best_match = max(
            (
                (ymd, ymd_func, hms, hms_func)
                for ymd, (_, ymd_func) in zip(ymd_strings, ymd_funcs)
                for hms, (_, hms_func) in zip(hms_strings, hms_funcs)
            ),
            key=lambda x: len(x[0]) + len(x[2]),
        )

        cur_ymd, cur_ymd_func, cur_hms, cur_hms_func = best_match

        self.check_valid(cur_hms, cur_ymd, time_str)
        return TimeParserResult(cur_hms, cur_hms_func, cur_ymd, cur_ymd_func)

    def check_valid(self, cur_hms, cur_ymd, time_str):
        """字符串是否合规"""
        if len("".join([cur_ymd, cur_hms])) < len(time_str.replace(" ", "")):
            if self.chinese_char_pattern.search(time_str):
                # 若搜索到中文，则 `-` 等符号可用作 time_span 的分隔符，可以不用处理判断字符串未匹配的异常情况
                if self.string_strict:
                    raise ValueError("## exception string `{}`.".format(type(time_str)))
            else:
                # 若未搜索到中文，则 `-` 等符号很可能只是间隔符，如`2018-08-09`而非 span 分隔符，此时要求字符串干净
                raise ValueError("## exception string `{}`.".format(type(time_str)))

    def generate_func_list(self, time_str):
        """generate_func_list 减少循环和遍历"""
        ymd_string_list = []
        ymd_func_list = []
        ymd_empty_string_flag = False
        for ymd_pattern, ymd_func in self.ymd_reg_norm_funcs:
            ymd_string = TimeParser.parse_pattern(time_str, ymd_pattern)

            if ymd_string != "":
                ymd_string_list.append(ymd_string)
                ymd_func_list.append([ymd_pattern, ymd_func])
            else:
                if not ymd_empty_string_flag:
                    ymd_string_list.append(ymd_string)
                    ymd_func_list.append([ymd_pattern, ymd_func])

                    ymd_empty_string_flag = True
        hms_string_list = []
        hms_func_list = []
        hms_empty_string_flag = False
        for hms_pattern, hms_func in self.hms_reg_norm_funcs:
            hms_string = TimeParser.parse_pattern(time_str, hms_pattern)

            if hms_string != "":
                hms_string_list.append(hms_string)
                hms_func_list.append([hms_pattern, hms_func])
            else:
                if not hms_empty_string_flag:
                    hms_string_list.append(hms_string)
                    hms_func_list.append([hms_pattern, hms_func])

                    hms_empty_string_flag = True
        return TimeHandlerFuncResult(
            hms_func_list, hms_string_list, ymd_func_list, ymd_string_list
        )

    def norm_year_24st(self, time_str):
        """norm_year_24st method"""
        _24st = self.day_regs[2].search(time_str)

        tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            tp.year = year

        if _24st:
            if tp.year == -1:
                tp.year = self.base_handler[0]

            _24st_str = _24st.group()
            month_str, day_str = self._parse_solar_terms(tp.year, _24st_str)
            tp.month = int(month_str)
            tp.day = int(day_str)

            if _24st_str in ["小寒", "大寒"]:
                tp.year += 1

        time_handler = tp.handler()

        return time_handler, time_handler, "time_point"

    def parse_span_2_2_point(self, time_str):
        """parse_span_2_2_point method"""
        time_str = self._seg_or_not_first(time_str)

        first_res = self._get_first_res(time_str)

        str_1 = None if first_res is None else first_res.group()

        str_2 = None
        second_res, str_2 = self._get_second_res(str_2, time_str)

        if str_2 is None:
            str_2 = None if second_res is None else second_res.group()

        str_1 = self._seg_or_not_second(str_1)
        str_2 = self._seg_or_not_second(str_2)

        return str_1, str_2

    def parse_time_span_point(self, time_str):
        """parse_time_span_point"""
        time_str_1, time_str_2 = self.parse_span_2_2_point(time_str)

        if time_str_1 is not None or time_str_2 is not None:
            return self._parse_time_span(time_str, time_str_1, time_str_2)
        return self._parse_single_time(time_str)

    def normalize_enum_day_pattern(self, time_string):
        """normalize_enum_day_pattern"""
        month = self.month_patterns[0].search(time_string)
        day_list = self.day_patterns[0].findall(time_string)

        first_tp, second_tp = self._time_point()

        year = self._normalize_year(time_string, self.base_handler)
        if year:
            second_tp.year = year
            first_tp.year = year

        if month:
            month_string = month.group(1)
            first_tp.month = int(self._char_num2num(month_string))
            second_tp.month = first_tp.month

        if len(day_list) != 0:
            day_list = [int(item[0]) for item in day_list]
            first_tp.day = min(day_list)
            second_tp.day = max(day_list)

        return first_tp.handler(), second_tp.handler(), "time_span"

    def _normalize_delta_unit(self, time_string, pattern):
        """将 time_delta 归一化"""
        # 处理字符串的问题
        time_string = time_string.replace("俩", "两个")
        time_string = time_string.replace("仨", "三个")

        deviation = pattern.search(time_string)
        time_deviation = 0.0
        time_definition = "accurate"

        if deviation:
            deviation_string = deviation.group()
            deviation_num = self.delta_num_pattern.search(deviation_string)
            if deviation_num:
                delta_num_string = deviation_num.group()
                time_deviation = float(self._char_num2num(delta_num_string))
            if "半" in time_string:
                if time_deviation > 0:
                    time_deviation += 0.5
                else:
                    time_deviation = 0.5
                time_definition = "blur"

            if "多" in time_string or "余" in time_string:
                time_definition = "blur"

        return time_deviation, time_definition

    def _parse_time_span(self, time_str, time_str_1, time_str_2):
        old_time_base_handler = self.base_handler
        try:
            if time_str_1 is not None and time_str_2 is None:
                full_time_handler_1, full_time_handler_2 = self._parse_single_end_point(
                    time_str_1
                )
            elif time_str_1 is not None and time_str_2 is not None:
                full_time_handler_1, full_time_handler_2 = self._parse_both_end_points(
                    time_str, time_str_1, time_str_2
                )
            elif time_str_1 is None and time_str_2 is not None:
                full_time_handler_1, full_time_handler_2 = self._parse_single_end_point(
                    time_str_2, reverse=True
                )
            else:
                raise KeyError()
        except Exception:
            self.base_handler = old_time_base_handler
            full_time_handler_1, full_time_handler_2, _ = self.parse_tp(
                time_str, self.base_handler
            )
        return full_time_handler_1, full_time_handler_2, "time_span"

    def _parse_single_time(self, time_str):
        time_str = self._compensate_num_month_num(time_str)
        full_time_handler_1, full_time_handler_2, time_type = self.parse_tp(
            time_str, self.base_handler
        )
        if self.ret_future:
            future_time_str = self._adjust_underlying_future_time(
                time_str, full_time_handler_1, full_time_handler_2
            )
            full_time_handler_1, full_time_handler_2, time_type = self.parse_tp(
                future_time_str, self.base_handler
            )
        return full_time_handler_1, full_time_handler_2, time_type

    def _parse_single_end_point(self, time_str, reverse=False):
        full_time_handler_2 = None
        time_str = self._compensate_num_month_num(time_str)
        full_time_handler_1, _, _ = self.parse_tp(time_str, self.base_handler)
        compare_res = TimeUtility._compare_handler(
            full_time_handler_1, self.base_handler
        )
        if reverse:
            if compare_res >= 0:
                full_time_handler_2 = self.past_time
            elif compare_res < 0:
                full_time_handler_2 = self.base_handler
        else:
            if compare_res >= 0:
                full_time_handler_2 = self.future
            elif compare_res < 0:
                full_time_handler_2 = self.base_handler
        return full_time_handler_1, full_time_handler_2

    def _parse_both_end_points(self, time_str, time_str_1, time_str_2):
        time_str_1 = self._compensate_num_month_num(time_str_1)
        time_str_2 = self._compensate_num_month_num(time_str_2)
        time_str_1, time_str_2 = self._compensate_str(time_str, time_str_1, time_str_2)
        full_time_handler_1, _, _ = self.parse_tp(time_str_1, self.base_handler)
        if time_str_2 in ["今", "至今", "现在", "今天"]:
            full_time_handler_2 = self.base_handler
        else:
            self.base_handler = self._check_limit_time_base(
                time_str_1, time_str_2, full_time_handler_1
            )
            _, full_time_handler_2, _ = self.parse_tp(time_str_2, self.base_handler)
            if full_time_handler_2[3] > -1 and full_time_handler_2[4:] == [-1, -1]:
                if time_str[-1] in "点时":
                    full_time_handler_2[4:] = [0, 0]
        return full_time_handler_1, full_time_handler_2

    def _get_second_res(self, str_2, time_str):
        second_res = None
        if self.second_0_span_reg.search(time_str):
            second_res = self.second_0_span_reg.search(time_str)
        elif self.second_1_span_reg.search(time_str):
            second_res = self.second_1_span_reg.search(time_str)
        elif self.second_2_span_reg.search(time_str):
            second_res = self.second_2_span_reg.search(time_str)
        elif self.second_3_span_reg.search(time_str) is None:
            if "之前" in time_str[-2:] or "以前" in time_str[-2:]:
                str_2 = time_str[:-2]
            elif "前" in time_str[-1:]:
                str_2 = time_str[:-1]
            else:
                second_res = None
        else:
            second_res = None
        return second_res, str_2

    def _get_first_res(self, time_str):
        if self.first_1_span_reg.search(time_str):
            first_res = self.first_1_span_reg.search(time_str)
        elif self.first_2_span_reg.search(time_str):
            first_res = self.first_2_span_reg.search(time_str)
        elif self.first_3_span_reg.search(time_str):
            if time_str[-2:] in ["夏至", "冬至"]:
                first_res = None
            else:
                first_res = self.first_3_span_reg.search(time_str)
        elif self.first_4_span_reg.search(time_str) and "前后" not in time_str:
            first_res = self.first_4_span_reg.search(time_str)
        elif self.first_5_span_reg.search(time_str) and "前后" not in time_str:
            first_res = self.first_5_span_reg.search(time_str)
        else:
            first_res = None
        return first_res

    def _handle_no_time_str(self, time_str):
        time_str = self._compensate_num_month_num(time_str)
        full_time_handler_1, full_time_handler_2, time_type = self.parse_tp(
            time_str, self.base_handler
        )

        if self.ret_future:
            future_time_str = self._adjust_underlying_future_time(
                time_str, full_time_handler_1, full_time_handler_2
            )
            full_time_handler_1, full_time_handler_2, time_type = self.parse_tp(
                future_time_str, self.base_handler
            )

        return full_time_handler_1, full_time_handler_2, time_type

    def _handle_single_time_str(self, time_str, reverse=False):
        time_str = self._compensate_num_month_num(time_str)

        if not reverse:
            full_time_handler_1, _, _ = self.parse_tp(time_str, self.base_handler)
            compare_res = TimeUtility._compare_handler(
                full_time_handler_1, self.base_handler
            )
            full_time_handler_2 = self.future if compare_res >= 0 else self.base_handler
        else:
            _, full_time_handler_2, _ = self.parse_tp(time_str, self.base_handler)
            compare_res = TimeUtility._compare_handler(
                self.base_handler, full_time_handler_2
            )
            full_time_handler_1 = (
                self.past_time if compare_res >= 0 else self.base_handler
            )

        return full_time_handler_1, full_time_handler_2, "time_span"

    def _handle_both_time_strs(self, time_str, time_str_1, time_str_2):
        time_str_1 = self._compensate_num_month_num(time_str_1)
        time_str_2 = self._compensate_num_month_num(time_str_2)
        time_str_1, time_str_2 = self._compensate_str(time_str, time_str_1, time_str_2)

        full_time_handler_1, _, _ = self.parse_tp(time_str_1, self.base_handler)

        if time_str_2 in ["今", "至今", "现在", "今天"]:
            full_time_handler_2 = self.base_handler
        else:
            self.base_handler = self._check_limit_time_base(
                time_str_1, time_str_2, full_time_handler_1
            )
            _, full_time_handler_2, _ = self.parse_tp(time_str_2, self.base_handler)

            if full_time_handler_2[3] > -1 and full_time_handler_2[4:] == [-1, -1]:
                if time_str[-1] in "点时":
                    full_time_handler_2[4:] = [0, 0]

        return full_time_handler_1, full_time_handler_2, "time_span"

    def _norm_limit_day(self, time_str):
        limit_day = self.day_regs[9].search(time_str)

        tp = TimePoint()

        if limit_day:
            limit_day_str = limit_day.group()
            time_base_datetime = TimeParser._convert_handler_to_datetime(
                self.base_handler
            )
            if "大大前" in limit_day_str:
                time_base_datetime -= datetime.timedelta(days=4)
            elif "大前" in limit_day_str:
                time_base_datetime -= datetime.timedelta(days=3)
            elif "前" in limit_day_str:
                time_base_datetime -= datetime.timedelta(days=2)
            elif "昨" in limit_day_str:
                time_base_datetime -= datetime.timedelta(days=1)
            elif (
                "今" in limit_day_str
                or "同一" in limit_day_str
                or "当" in limit_day_str
            ):
                pass  # Relative day is today; no date shift.
            elif "明" in limit_day_str or "次" in limit_day_str:
                time_base_datetime += datetime.timedelta(days=1)
            elif "大大后" in limit_day_str:
                time_base_datetime += datetime.timedelta(days=4)
            elif "大后" in limit_day_str:
                time_base_datetime += datetime.timedelta(days=3)
            elif "后" in limit_day_str:
                time_base_datetime += datetime.timedelta(days=2)
            else:
                raise ValueError(INPUT_TIME_ERROR)

            tp.day = time_base_datetime.day
            tp.month = time_base_datetime.month
            tp.year = time_base_datetime.year
        else:
            tp.day = self.base_handler[2]

        if tp.day < 0:
            raise ValueError(
                "The given base time `{}` is illegal.".format(self.base_handler)
            )

        time_handler = tp.handler()

        return time_handler, time_handler, "time_point"

    def _norm_hour_minute_second(self, time_str):
        day_bias = 0

        hour = self.hour_regs[0].search(time_str)
        minute = self.minute_regs[0].search(time_str)
        second = self.second_regs[0].search(time_str)

        tp = TimePoint()

        if hour:
            hour_str = hour.group(1)
            hour = int(self._char_num2num(hour_str))
            hour_limitation = self.hour_regs[1].search(time_str)
            if hour_limitation:
                hour_limit_str = hour_limitation.group()
                if (5 <= hour <= 12) and (
                    "晚" in hour_limit_str or "夜" in hour_limit_str
                ):
                    hour += 12
                if "中午" in hour_limit_str and hour not in [11, 12]:
                    hour += 12
                if "下午" in hour_limit_str and (1 <= hour <= 11):
                    hour += 12
            if hour == 24:
                hour = 0
                day_bias = 1

            tp.hour = hour

        if minute:
            minute_str = minute.group(1)
            tp.minute = int(self._char_num2num(minute_str))

        if second:
            str_2 = second.group(1)
            tp.second = int(self._char_num2num(str_2))

        time_handler = tp.handler()

        return time_handler, time_handler, day_bias

    def _norm_num_hour_minute_second(self, time_str):
        time_str = time_str.replace("时", "")

        day_bias = 0
        hour_limitation = self.hour_regs[1].search(time_str)
        if hour_limitation:
            hour_limit_str = hour_limitation.group()
            time_str = time_str.replace(hour_limit_str, "")

        def convert_hour(h, h_str):
            if (5 <= h <= 12) and ("晚" in h_str or "夜" in h_str):
                h += 12
            if "中午" in h_str and h not in [11, 12]:
                h += 12
            if "下午" in h_str and (1 <= h <= 11):
                h += 12
            return h

        colon_num = len(self.hms_segs.findall(time_str))
        if colon_num == 2:
            hour, minute, second = self.hms_segs.split(time_str)
            if hour_limitation:
                hour = convert_hour(hour, hour_limit_str)

        elif colon_num == 1:
            int_1, int_2 = self.hms_segs.split(time_str)
            if int(int_1) == 24 and int(int_2) == 0:
                hour = 24
                minute = 0
                second = -1
            elif int(int_1) <= 23:
                hour = int(int_1)
                minute = int(int_2)
                second = -1
                if hour_limitation:
                    hour = convert_hour(hour, hour_limit_str)
            else:
                hour = -1
                minute = int(int_1)
                second = int(int_2)
        else:
            raise ValueError(INPUT_TIME_ERROR)

        tp = TimePoint()

        tp.hour = int(hour)
        tp.minute = int(minute)
        tp.second = int(second)

        time_handler = tp.handler()

        return time_handler, time_handler, day_bias

    def _norm_hour_limit_minute(self, time_str):
        day_bias = 0
        hour = self.hour_regs[0].search(time_str)
        hour_limitation = self.hour_regs[1].search(time_str)
        limit_minute = self.minute_regs[1].search(time_str)

        def convert_hour(h, h_str):
            if (5 <= h <= 12) and ("晚" in h_str or "夜" in h_str):
                h += 12
            if "中午" in h_str and h not in [11, 12]:
                h += 12
            if "下午" in h_str and (1 <= h <= 11):
                h += 12
            return h

        tp = TimePoint()

        if hour:
            hour_str = hour.group(1)
            hour = int(self._char_num2num(hour_str))
            if hour_limitation:
                hour_limit_str = hour_limitation.group()
                hour = convert_hour(hour, hour_limit_str)
            tp.hour = hour

        if limit_minute:
            limit_minute_str = limit_minute.group()
            if "半" in limit_minute_str:
                tp.minute = 30
            elif "刻" in limit_minute_str:
                num = self.month_num_reg.search(limit_minute_str)
                if num:
                    num = int(self._char_num2num(num.group()))
                    if num == 1:
                        tp.minute = 15
                    elif num == 2:
                        tp.minute = 30
                    elif num == 3:
                        tp.minute = 45
                    else:
                        raise ValueError(INPUT_TIME_ERROR)
                else:
                    raise ValueError(INPUT_TIME_ERROR)
            else:
                raise ValueError(INPUT_TIME_ERROR)

        time_handler = tp.handler()
        return time_handler, time_handler, day_bias

    def _norm_standard_year_month_day(self, time_str):
        def reg_strip(ymd_segs, time_str):
            head = ymd_segs.search(time_str[0])
            tail = ymd_segs.search(time_str[-1])
            while head or tail:
                if head:
                    time_str = time_str[1:]
                if tail:
                    time_str = time_str[:-1]
                head = ymd_segs.search(time_str[0])
                tail = ymd_segs.search(time_str[-1])

            return time_str

        time_str = reg_strip(self.ymd_segs, time_str)

        colon_num = len(self.ymd_segs.findall(time_str))
        if colon_num == 2:
            year, month, day = self.ymd_segs.split(time_str)

        elif colon_num == 1:
            int_1, int_2 = self.ymd_segs.split(time_str)
            if (1600 < int(int_1) < 2200) and int(int_2) <= 12:
                year = int(int_1)
                month = int(int_2)
                day = -1
            elif int(int_1) <= 12 and int(int_2) <= 31:
                year = -1
                month = int(int_1)
                day = int(int_2)
            else:
                raise ValueError(INPUT_TIME_ERROR)
        else:
            raise ValueError(INPUT_TIME_ERROR)

        tp = TimePoint()

        tp.year = int(year)
        tp.month = int(month)
        tp.day = int(day)

        time_handler = tp.handler()

        return time_handler, time_handler, "time_point"

    def _norm_standard_year(self, time_str):
        tp = TimePoint()

        year = self.standard_year_reg.search(time_str)
        tp.year = int(year.group()) if year else self.base_handler[0]
        time_handler = tp.handler()

        return time_handler, time_handler, "time_span"

    def _norm_special_time_span(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()
        if "今明" in time_str:
            if "年" in time_str:
                first_tp.year = self.base_handler[0]
                second_tp.year = self.base_handler[0] + 1
            elif "天" in time_str:
                if self.base_handler[2] == -1:
                    raise ValueError(
                        "the given time_base `{}` is illegal.".format(time_str)
                    )
                first_tp.day = self.base_handler[2]
                second_tp.day = self.base_handler[2] + 1
            else:
                raise ValueError(f"the given `{time_str}` is illegal.")

        elif "全" in time_str:
            if "年" in time_str:
                first_tp.year = self.base_handler[0]
                second_tp.year = self.base_handler[0]
            elif "月" in time_str:
                first_tp.month = self.base_handler[1]
                second_tp.month = self.base_handler[1]
            elif "天" in time_str:
                first_tp.day = self.base_handler[2]
                second_tp.day = self.base_handler[2]
            else:
                raise ValueError(f"the given `{time_str}` is illegal.")
        else:
            raise ValueError(f"the given `{time_str}` is illegal.")

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_month_day(self, time_str):
        month = self.month_regs[0].search(time_str)
        day = self.day_regs[0].search(time_str)

        tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            tp.year = year

        if month is not None:
            month_str = month.group(1)
            tp.month = int(self._char_num2num(month_str))

        if day is not None:
            day_str = day.group(1)
            tp.day = int(self._char_num2num(day_str))

        time_handler = tp.handler()
        return time_handler, time_handler, "time_point"

    def _norm_limit_solar_season(self, time_str):
        first_tp, second_tp = TimePoint(), TimePoint()

        if self.base_handler[1] == -1 or self.base_handler[1] > 12:
            raise ValueError(
                f"the `month` of time_base `{self.base_handler}` is undefined."
            )
        if "上" in time_str:
            self._deal_previous(first_tp, second_tp, time_str)

        elif "下" in time_str:
            self._deal_next(first_tp, second_tp, time_str)

        elif "这" in time_str or "本" in time_str:
            self._deal_now(first_tp, second_tp)

        else:
            raise ValueError("the given `{}` is illegal.".format(time_str))

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _deal_now(self, first_tp, second_tp):
        for item in INFOS:
            if self.base_handler[1] in item:
                first_tp.month = item[0]
                second_tp.month = item[2]

    def _deal_previous(self, first_tp, second_tp, time_str):
        for idx, item in enumerate(INFOS):
            if self.base_handler[1] not in item:
                continue
            match_span_flag = False
            for i, span in enumerate(SPANS):
                if span in time_str:
                    first_tp.month = item[i] - 3
                    second_tp.month = item[i] - 3
                    match_span_flag = True
                    break
            if not match_span_flag:
                first_tp.month = item[0] - 3
                second_tp.month = item[2] - 3

            if idx == 0:
                first_tp.year = self.base_handler[0] - 1
                second_tp.year = self.base_handler[0] - 1
                first_tp.month += 12
                second_tp.month += 12

    def _deal_next(self, first_tp, second_tp, time_str):
        for idx, item in enumerate(INFOS):
            if self.base_handler[1] in item:
                match_span_flag = False
                for i, span in enumerate(SPANS):
                    if span in time_str:
                        first_tp.month = item[i] + 3
                        second_tp.month = item[i] + 3
                        match_span_flag = True
                        break
                if not match_span_flag:
                    first_tp.month = item[0] + 3
                    second_tp.month = item[2] + 3

                if idx == 3:
                    first_tp.year = self.base_handler[0] + 1
                    second_tp.year = self.base_handler[0] + 1
                    first_tp.month -= 12
                    second_tp.month -= 12

    def _norm_limit_year_solar_season(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp.year, second_tp.year = self._norm_limit_year(
            time_str, self.base_handler
        )

        first_tp.month, second_tp.month = self._norm_solar_season(time_str)

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_solar_season(self, time_str):

        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
            second_tp.year = year

        first_tp.month, second_tp.month = self._norm_solar_season(time_str)

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_year_span_month(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp.year, second_tp.year = self._norm_limit_year(
            time_str, self.base_handler
        )

        first_tp.month, second_tp.month = self._norm_span_month(time_str)

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_span_month(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
            second_tp.year = year

        first_tp.month, second_tp.month = self._norm_span_month(time_str)

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_month_day(self, time_str):
        day = self.day_regs[0].search(time_str)

        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp, second_tp = self._norm_limit_month(
            time_str, self.base_handler, first_tp, second_tp
        )

        if day:
            day = int(self._char_num2num(day.group(1)))
            first_tp.day = day
            second_tp.day = day

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_point"

    def _norm_limit_year_month_day(self, time_str):
        month = self.month_regs[0].search(time_str)
        day = self.day_regs[0].search(time_str)

        tp = TimePoint()

        tp.year, _ = self._norm_limit_year(time_str, self.base_handler)
        time_type = "time_span"
        if month is not None:
            tp.month = int(self._char_num2num(month.group(1)))

        if day is not None:
            tp.day = int(self._char_num2num(day.group(1)))
            time_type = "time_point"

        time_handler = tp.handler()

        return time_handler, time_handler, time_type

    def _norm_lunar_year_month_day(self, time_str):
        lu_month = self.month_regs[3].search(time_str)
        lu_day = self.day_regs[1].search(time_str)

        lu_time_point = TimePoint()
        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            lu_time_point.year = year

        first_time_handler, second_time_handler = self._get_lunar_time_handler(
            lu_month, lu_day, lu_time_point
        )

        return first_time_handler, second_time_handler, "time_point"

    def _norm_lunar_limit_year_month_day(self, time_str):
        lu_month = self.month_regs[3].search(time_str)
        lu_day = self.day_regs[1].search(time_str)

        year_1, _ = self._norm_limit_year(time_str, self.base_handler)
        lu_time_point = TimePoint()
        lu_time_point.year = year_1

        first_time_handler, second_time_handler = self._get_lunar_time_handler(
            lu_month, lu_day, lu_time_point
        )
        return first_time_handler, second_time_handler, "time_point"

    def _norm_year_lunar_season(self, time_str):
        season = self.day_regs[3].search(time_str)

        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
            second_tp.year = year
        else:
            first_tp.year = self.base_handler[0]
            second_tp.year = self.base_handler[0]

        if season is not None:
            solar_season = season.group()
            if "春" in solar_season:
                month_1, first_day = self._parse_solar_terms(first_tp.year, "立春")
                month_2, second_day = self._parse_solar_terms(first_tp.year, "立夏")
            elif "夏" in solar_season:
                month_1, first_day = self._parse_solar_terms(first_tp.year, "立夏")
                month_2, second_day = self._parse_solar_terms(first_tp.year, "立秋")
            elif "秋" in solar_season:
                month_1, first_day = self._parse_solar_terms(first_tp.year, "立秋")
                month_2, second_day = self._parse_solar_terms(first_tp.year, "立冬")
            elif "冬" in solar_season:
                month_1, first_day = self._parse_solar_terms(first_tp.year, "立冬")
                month_2, second_day = self._parse_solar_terms(first_tp.year, "立春")
                second_tp.year += 1
            else:
                raise ValueError("the season str {} is illegal.".format(time_str))

            first_tp.month = int(month_1)
            second_tp.month = int(month_2)
            first_tp.day = int(first_day)
            second_tp.day = int(second_day) - 1

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_year_lunar_season(self, time_str):
        season = self.day_regs[3].search(time_str)

        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp.year, second_tp.year = self._norm_limit_year(
            time_str, self.base_handler
        )

        if season is not None:
            solar_season = season.group()

            four_season_str = "春夏秋冬春"
            for idx, item in enumerate(four_season_str):
                if idx != 4 and item in solar_season:
                    month_1, first_day = self._parse_solar_terms(
                        first_tp.year, "立" + item
                    )
                    month_2, second_day = self._parse_solar_terms(
                        first_tp.year, "立" + four_season_str[idx + 1]
                    )
                    if idx == 3:
                        second_tp.year += 1
                    break
            else:
                raise ValueError("the season str {} is illegal.".format(time_str))

            first_tp.month = int(month_1)
            second_tp.month = int(month_2)
            first_tp.day = int(first_day)
            second_tp.day = int(second_day) - 1

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _norm_standard_week_day(self, time_str):
        week = self.day_regs[6].search(time_str)
        week_day = self.day_regs[7].search(time_str)

        one_week = datetime.timedelta(days=7)
        time_base_datetime = TimeParser._convert_handler_to_datetime(self.base_handler)

        if week:
            week_str = week.group()
            if "上上" in week_str:
                time_base_datetime -= one_week + one_week
            elif "下下" in week_str:
                time_base_datetime += one_week + one_week
            elif "上" in week_str:
                time_base_datetime -= one_week
            elif "下" in week_str:
                time_base_datetime += one_week
            elif "本" in week_str or "这" in week_str:
                pass  # Current week; no week offset.

        def compute_week_day(cur, target_week_day):
            one_day = datetime.timedelta(days=1)
            cur_week_day = cur.weekday()
            delta = cur_week_day - target_week_day
            if delta == 0:
                return cur
            if delta > 0:
                for _ in range(delta):
                    cur -= one_day
            elif delta < 0:
                for _ in range(abs(delta)):
                    cur += one_day

            return cur

        if week_day:
            week_day_str = week_day.group()

            trans = ["一二三四五六天末日", [0, 1, 2, 3, 4, 5, 6, 6, 6]]
            for c, i in zip(trans[0], trans[1]):
                if c in week_day_str:
                    target_day = compute_week_day(time_base_datetime, i)
                    break
            else:
                raise ValueError("`星期{}` is illegal.".format(week_day_str))

        time_handler = TimeParser._convert_time_base2handler(target_day)
        tp = TimePoint()
        tp.year = time_handler[0]
        tp.month = time_handler[1]
        tp.day = time_handler[2]
        time_handler = tp.handler()

        return time_handler, time_handler, "time_point"

    def _norm_limit_week(self, time_str):
        month_match = self.month_regs[0].search(time_str)
        if not month_match:
            raise ValueError(f"month str is not in `{time_str}`.")

        month_num_match = self.month_num_reg.search(month_match.group())
        if not month_num_match:
            raise ValueError(f"month str is not in `{time_str}`.")

        week_res = self.day_regs[8].search(time_str)
        week_day = self.day_regs[7].search(time_str)
        if not (week_res and week_day):
            raise ValueError(f"the given str `{time_str}` is illegal.")

        tp = TimePoint()
        tp.month = int(self._char_num2num(month_num_match.group()))
        tp.year = self.base_handler[0]

        week_order_num = int(
            self._char_num2num(self.week_num_reg.search(week_res.group()).group())
        )
        time_base_datetime = TimeParser._convert_handler_to_datetime(
            [tp.year, tp.month, 1, 0, 0, 0]
        )

        trans = {
            "一": 0,
            "二": 1,
            "三": 2,
            "四": 3,
            "五": 4,
            "六": 5,
            "天": 6,
            "末": 6,
            "日": 6,
        }
        for c in week_day.group():
            if c in trans:
                target_day = self._get_compute_week_day(time_base_datetime, trans[c])
                break
        else:
            raise ValueError(f"`星期{week_day.group()}` is illegal.")

        target_day += datetime.timedelta(days=7) * (week_order_num - 1)
        tp.day = TimeParser._convert_time_base2handler(target_day)[2]

        return tp.handler(), tp.handler(), "time_point"

    def _norm_month_week(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        month = self.month_regs[0].search(time_str)

        if month:
            month_num = self.month_num_reg.search(month.group())
            month_num = int(self._char_num2num(month_num.group()))
            first_tp.month = month_num
            second_tp.month = month_num
        else:
            raise ValueError("month str is not in `{}`.".format(type(time_str)))

        time_handler_1, time_handler_2 = self._get_norm_limit_month_week(
            time_str, first_tp, second_tp
        )

        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_month_week(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp, second_tp = self._norm_limit_month(
            time_str, self.base_handler, first_tp, second_tp
        )

        time_handler_1, time_handler_2 = self._get_norm_limit_month_week(
            time_str, first_tp, second_tp
        )
        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_month_week(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
            second_tp.year = year

        time_handler_1, time_handler_2 = self._get_norm_limit_year_month_week(
            time_str, first_tp, second_tp
        )
        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_year_month_week(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp.year, second_tp.year = self._norm_limit_year(
            time_str, self.base_handler
        )
        time_handler_1, time_handler_2 = self._get_norm_limit_year_month_week(
            time_str, first_tp, second_tp
        )
        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_week(self, time_str):

        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
        else:
            first_tp.year = self.base_handler[0]

        time_handler_1, time_handler_2 = self._get_norm_limit_year_week(
            time_str, first_tp, second_tp
        )

        return time_handler_1, time_handler_2, "time_span"

    def _norm_limit_year_week(self, time_str):
        first_tp = TimePoint()
        second_tp = TimePoint()

        first_tp.year, _ = self._norm_limit_year(time_str, self.base_handler)

        time_handler_1, time_handler_2 = self._get_norm_limit_year_week(
            time_str, first_tp, second_tp
        )

        return time_handler_1, time_handler_2, "time_span"

    def _norm_year_fixed_solar_festival(self, time_str):
        time_point = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        time_point.year = year if year is not None else self.base_handler[0]

        time_handler = self._get_norm_limit_year_fixed_solar_festival(
            time_str, time_point
        )
        return time_handler, time_handler, "time_point"

    def _norm_limit_year_fixed_solar_festival(self, time_str):
        time_point = TimePoint()

        time_point.year, _ = self._norm_limit_year(time_str, self.base_handler)

        time_handler = self._get_norm_limit_year_fixed_solar_festival(
            time_str, time_point
        )
        return time_handler, time_handler, "time_point"

    def _norm_year_fixed_lunar_festival(self, time_str):
        tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        tp.year = year if year is not None else self.base_handler[0]

        time_handler = self._get_norm_limit_year_fixed_lunar_festival(time_str, tp)
        return time_handler, time_handler, "time_point"

    def _norm_limit_year_fixed_lunar_festival(self, time_str):
        tp = TimePoint()

        tp.year, _ = self._norm_limit_year(time_str, self.base_handler)

        time_handler = self._get_norm_limit_year_fixed_lunar_festival(time_str, tp)
        return time_handler, time_handler, "time_point"

    def _norm_year_regular_solar_festival(self, time_str):
        tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        tp.year = year if year is not None else self.base_handler[0]

        time_handler = self._get_norm_year_regular_solar_festival(time_str, tp)

        return time_handler, time_handler, "time_point"

    def _norm_limit_year_regular_solar_festival(self, time_str):
        tp = TimePoint()

        tp.year, _ = self._norm_limit_year(time_str, self.base_handler)

        time_handler = self._get_norm_year_regular_solar_festival(time_str, tp)

        return time_handler, time_handler, "time_point"

    def _norm_enum_day_reg(self, time_str):
        month = self.month_regs[0].search(time_str)
        day_list = self.day_regs[0].findall(time_str)

        first_tp = TimePoint()
        second_tp = TimePoint()

        year = self._norm_year(time_str, self.base_handler)
        if year is not None:
            first_tp.year = year
            second_tp.year = year

        if month is not None:
            month_str = month.group(1)
            first_tp.month = int(self._char_num2num(month_str))
            second_tp.month = first_tp.month

        if len(day_list) != 0:
            day_list = [int(item[0]) for item in day_list]
            first_tp.day = min(day_list)
            second_tp.day = max(day_list)

        time_handler_1 = first_tp.handler()
        time_handler_2 = second_tp.handler()

        return time_handler_1, time_handler_2, "time_span"

    def _normalize_year(self, time_string, time_base_handler):
        year = self.year_patterns[0].search(time_string)
        if year is not None:
            year_string = year.group(1)
            # 针对汉字年份进行转换
            year_string = self.chinese_year_char_2_arabic_year_char(year_string)

            # 针对 13年8月，08年6月，三三年 这类日期，补全其年份
            if len(year_string) == 2:
                year_string = TimeParser._year_completion(
                    year_string, time_base_handler
                )

            return int(year_string)
        return None

    def _convert_lunar2solar(self, lunar_handler, leap_month):

        def str2handler(datetime_obj):
            return [datetime_obj.year, datetime_obj.month, datetime_obj.day, -1, -1, -1]

        if lunar_handler[2] == -1:
            first_solar_time_handler = self.lunar2solar(
                lunar_handler[0], lunar_handler[1], 1, leap_month
            )
            try:
                second_solar_time_handler = self.lunar2solar(
                    lunar_handler[0], lunar_handler[1], 30, leap_month
                )
            except Exception:
                second_solar_time_handler = self.lunar2solar(
                    lunar_handler[0], lunar_handler[1], 29, leap_month
                )

            return str2handler(first_solar_time_handler), str2handler(
                second_solar_time_handler
            )
        solar_time_handler = self.lunar2solar(
            lunar_handler[0], lunar_handler[1], lunar_handler[2], leap_month
        )
        return str2handler(solar_time_handler), str2handler(solar_time_handler)

    def _norm_year_order_week(self, time_str, first_point_year):
        week_res = self.day_regs[8].search(time_str)
        if week_res:
            week_res = week_res.group()
            week_order_num = self.week_num_reg.search(week_res)
            week_order_num = int(self._char_num2num(week_order_num.group()))
            offset = week_order_num * 7

            day_1 = datetime.datetime(first_point_year, 1, 1)

            point_day_1, point_day_2 = self._get_norm_month_order_week(day_1, offset)
            if point_day_1.year != first_point_year:
                raise ValueError(INPUT_TIME_ERROR)

            return point_day_1, point_day_2

        raise ValueError(INPUT_TIME_ERROR)

    def _norm_month_order_week(
        self, time_str, first_point_month, first_point_year=None
    ):
        week_res = self.day_regs[8].search(time_str)
        if week_res:
            week_res = week_res.group()
            week_order_num = self.week_num_reg.search(week_res)
            week_order_num = int(self._char_num2num(week_order_num.group()))
            day_offset = week_order_num * 7
            if first_point_year is not None:
                day_1 = datetime.datetime(first_point_year, first_point_month, 1)
            else:
                day_1 = datetime.datetime(self.base_handler[0], first_point_month, 1)

            point_day_1, point_day_2 = self._get_norm_month_order_week(
                day_1, day_offset
            )
            if point_day_1.month != first_point_month:
                raise ValueError(INPUT_TIME_ERROR)
        else:
            raise ValueError(INPUT_TIME_ERROR)

        return point_day_1, point_day_2

    def _norm_limit_year(self, time_str, time_base_handler):
        def _condition_one(_year_str, _time_str):
            return (
                "今" in _year_str
                or "这" in _time_str
                or "同" in _time_str
                or "当" in _time_str
                or "本" in _time_str
            )

        year = self.year_regs[1].search(time_str)
        if year is not None:
            year_str = year.group(1)
            if "大前" in year_str:
                year_1 = time_base_handler[0] - 3
                year_2 = time_base_handler[0] - 3
            elif "前一" in year_str or "去" in year_str or "上" in year_str:
                year_1 = time_base_handler[0] - 1
                year_2 = time_base_handler[0] - 1
            elif "前" in year_str:
                year_1 = time_base_handler[0] - 2
                year_2 = time_base_handler[0] - 2
            elif _condition_one(year_str, time_str):
                year_1 = time_base_handler[0]
                year_2 = time_base_handler[0]
            elif "明" in year_str or "次" in year_str:
                year_1 = time_base_handler[0] + 1
                year_2 = time_base_handler[0] + 1
            elif "后" in year_str:
                year_1 = time_base_handler[0] + 2
                year_2 = time_base_handler[0] + 2
            else:
                raise ValueError(INPUT_TIME_ERROR)
        else:
            year_1 = time_base_handler[0]
            year_2 = time_base_handler[0]

        return year_1, year_2

    def _norm_limit_month(self, time_str, time_base_handler, first_tp, second_tp):
        def _condition_two(_month_str):
            return (
                "同" in _month_str
                or "本" in _month_str
                or "当" in _month_str
                or "这" in _month_str
            )

        month = self.month_regs[4].search(time_str)
        if month is not None:
            month_str = month.group()
            if "上" in month_str:
                if time_base_handler[1] == 1:
                    first_tp.year = time_base_handler[0] - 1
                    second_tp.year = time_base_handler[0] - 1
                    first_tp.month = 12
                    second_tp.month = 12
                else:
                    first_tp.month = time_base_handler[1] - 1
                    second_tp.month = time_base_handler[1] - 1
            elif "下" in month_str or "次" in month_str:
                if time_base_handler[1] == 12:
                    first_tp.year = time_base_handler[0] + 1
                    second_tp.year = time_base_handler[0] + 1
                    first_tp.month = 1
                    second_tp.month = 1
                else:
                    first_tp.month = time_base_handler[1] + 1
                    second_tp.month = time_base_handler[1] + 1
            elif _condition_two(month_str):
                first_tp.month = time_base_handler[1]
                second_tp.month = time_base_handler[1]
            else:
                raise ValueError(INPUT_TIME_ERROR)
        else:
            first_tp.month = time_base_handler[1]
            second_tp.month = time_base_handler[1]

        return first_tp, second_tp

    def _norm_solar_season(self, time_str):
        month_1, month_2 = -1, -1
        month = self.month_regs[1].search(time_str)
        if month is None:
            return month_1, month_2
        season = month.group()

        if "1" in season or "一" in season or "首" in season:
            month_1, month_2 = self._deal_first_month(month_1, month_2, season)
        elif "2" in season or "二" in season:
            month_1, month_2 = self._deal_second_month(month_1, month_2, season)
        elif "3" in season or "三" in season:
            month_1, month_2 = self._deal_third_month(month_1, month_2, season)
        elif "4" in season or "四" in season:
            month_1, month_2 = self._get_norm_solar_season_four(season)
        elif "前两" in season or "头两" in season:
            month_1, month_2 = 1, 6
        elif "后两" in season:
            month_1, month_2 = 7, 12
        else:
            raise ValueError(INPUT_TIME_ERROR)

        return month_1, month_2

    def _deal_third_month(self, month_1, month_2, season):
        if "第" in season:
            month_1, month_2 = self._get_norm_solar_season_three(season)
        elif "前" in season or "头" in season:
            month_1, month_2 = 1, 9
        elif "后" in season:
            month_1, month_2 = 4, 12
        else:
            month_1, month_2 = self._get_norm_solar_season_three(season)
        return month_1, month_2

    def _deal_second_month(self, month_1, month_2, season):
        if "第" in season:
            month_1, month_2 = self._get_norm_solar_season_two(season)
        elif "前" in season or "头" in season:
            month_1, month_2 = 1, 6
        elif "后" in season:
            month_1, month_2 = 7, 12
        else:
            month_1, month_2 = self._get_norm_solar_season_two(season)
        return month_1, month_2

    def _deal_first_month(self, month_1, month_2, season):
        if "第" in season:
            month_1, month_2 = self._get_norm_solar_season_one(season)
        elif "前" in season or "头" in season:
            month_1, month_2 = 1, 3
        elif "后" in season:
            month_1, month_2 = 10, 12
        else:
            month_1, month_2 = self._get_norm_solar_season_one(season)
        return month_1, month_2

    def _norm_span_month(self, time_str):
        month = self.month_regs[2].search(time_str)
        if month is not None:
            span_month = month.group()
            if "首" not in span_month:
                month_num = self.month_num_reg.search(span_month)
                month_num = int(self._char_num2num(month_num.group()))

                if "前" in span_month or "头" in span_month:
                    month_1 = 1
                    month_2 = month_num
                elif "后" in span_month:
                    month_1 = 13 - month_num
                    month_2 = 12
                elif "第" in span_month:
                    month_1 = month_num
                    month_2 = month_num
                else:
                    raise ValueError(INPUT_TIME_ERROR)
            else:
                month_1 = 1
                month_2 = 1

        else:
            month_1 = -1
            month_2 = -1

        return month_1, month_2

    def _preprocess(self):
        super(TimeParser, self).__call__()

    def _compensate_str(self, time_str, time_str_1, time_str_2):
        time_compensation = self.time_span_point_compensation.search(time_str)
        if time_compensation:
            time_compensation = time_compensation.group()

            if "年" in time_compensation:
                if time_str_1[-1] not in "点时日号月年":
                    time_str_1 = "".join([time_str_1, "年"])
            elif "月" in time_compensation:
                if time_str_1[-1] not in "点时日号月":
                    time_str_1 = "".join([time_str_1, "月"])
            elif "日" in time_compensation or "号" in time_compensation:
                if time_str_1[-1] not in "点时日号":
                    time_str_1 = "".join([time_str_1, "日"])
            elif "点" in time_compensation or "时" in time_compensation:
                if time_str_1[-1] not in "点时":
                    time_str_1 = "".join([time_str_1, "时"])

            hour_limitation = self.hour_regs[1].search(time_str)
            if hour_limitation:
                time_str_2 = "".join([hour_limitation.group(), time_str_2])

            return time_str_1, time_str_2
        return time_str_1, time_str_2

    def _check_limit_time_base(self, time_str_1, time_str_2, full_time_handler_1):
        limit_ymd_time_regs = [
            [self.limit_year_lunar_season_reg, self._norm_limit_year_lunar_season],
            [self.limit_year_solar_season_reg, self._norm_limit_year_solar_season],
            [self.limit_solar_season_reg, self._norm_limit_solar_season],
            [self.limit_year_week_reg, self._norm_limit_year_week],
            [self.limit_week_reg, self._norm_limit_week],
            [self.limit_month_day_reg, self._norm_limit_month_day],
            [self.limit_month_reg, self.norm_limit_month],
            [self.limit_year_span_month_reg, self._norm_limit_year_span_month],
            [self.standard_week_day_reg, self._norm_standard_week_day],
            [
                self.limit_year_fixed_solar_festival_reg,
                self._norm_limit_year_fixed_solar_festival,
            ],
            [
                self.limit_year_fixed_lunar_festival_reg,
                self._norm_limit_year_fixed_lunar_festival,
            ],
            [
                self.limit_year_regular_solar_festival_reg,
                self._norm_limit_year_regular_solar_festival,
            ],
            [
                self.lunar_limit_year_month_day_reg,
                self._norm_lunar_limit_year_month_day,
            ],
            [self.limit_year_month_day_reg, self._norm_limit_year_month_day],
            [self.limit_day_reg, self._norm_limit_day],
        ]

        time_str_1_limit = False
        time_str_2_limit = False

        for ymd_limit_reg in limit_ymd_time_regs:
            first_ymd_limit_str = TimeParser.parse_reg(time_str_1, ymd_limit_reg[0])
            second_ymd_limit_str = TimeParser.parse_reg(time_str_2, ymd_limit_reg[0])
            if first_ymd_limit_str != "":
                time_str_1_limit = True
            if second_ymd_limit_str != "":
                time_str_2_limit = True
            if time_str_1_limit and time_str_2_limit:
                break

        if time_str_2_limit:
            return self.base_handler
        return full_time_handler_1

    def _adjust_underlying_future_time(
        self, time_str, full_time_handler_1, full_time_handler_2
    ):
        ymd_time_regs = [
            self.year_24st_reg,
            self.year_lunar_season_reg,
            self.year_solar_season_reg,
            self.standard_week_day_reg,
            self.year_span_month_reg,
            self.year_fixed_solar_festival_reg,
            self.year_fixed_lunar_festival_reg,
            self.year_regular_solar_festival_reg,
            self.lunar_limit_year_month_day_reg,
            self.lunar_year_month_day_reg,
            self.year_month_day_reg,
            self.standard_year_reg,
        ]
        hms_time_regs = [
            self.hour_minute_second_reg,
            self.num_hour_minute_second_reg,
            self.hour_limit_minute_reg,
        ]

        time_str_flag = False
        for ymd_limit_reg in ymd_time_regs + hms_time_regs:
            ymd_str = TimeParser.parse_reg(time_str, ymd_limit_reg)
            if ymd_str != "":
                time_str_flag = True
                break

        if time_str_flag:
            time_str = self._get_underlying_future_time_with_flag(
                time_str, full_time_handler_1
            )
        return time_str

    def _compensate_num_month_num(self, time_str):
        matched_res = self.num_month_num_reg.search(time_str)
        if matched_res is not None:
            return time_str + "日"
        return time_str

    def _seg_or_not_first(self, time_str):
        seg_regs = [self.time_span_seg_standard_year_month_to_year_month]
        for reg in seg_regs:
            matched_str = TimeParser.parse_reg(time_str, reg)
            if matched_str is not None and matched_str != "":
                return time_str

        no_seg_regs = [self.time_span_no_seg_standard_year_month_day]
        for reg in no_seg_regs:
            searched_res = reg.search(time_str)
            if searched_res:
                time_str = time_str.replace("-", "䶵")
                break
        if "起" in time_str or "至" in time_str or "到" in time_str:
            time_str = time_str.replace("-", "䶵")
        return time_str

    def _seg_or_not_second(self, time_str):
        if time_str is None:
            return None

        time_str = time_str.replace("䶵", "-").strip()
        return time_str

    def _norm_year(self, time_str, time_base_handler):
        year = self.year_regs[0].search(time_str)
        if year is not None:
            year_str = year.group(1)
            year_str = self.cn_year_char_2_arabic_year_char(year_str)

            if len(year_str) == 2:
                year_str = TimeParser._year_completion(year_str, time_base_handler)

            return int(year_str)
        return None

    def _parse_solar_terms(self, year, solar_term):
        if solar_term in ["小寒", "大寒", "立春", "雨水"]:
            flag_day = int(
                (year % 100) * 0.2422 + self.solar_terms.get(solar_term, [0])[0]
            ) - int((year % 100 - 1) / 4)
        else:
            flag_day = int(
                (year % 100) * 0.2422 + self.solar_terms.get(solar_term, [0])[0]
            ) - int((year % 100) / 4)

        for special in self.solar_terms.get(solar_term, [0, 0, 0])[2:]:
            if year == special[0]:
                flag_day += special[1]
                break
        return (self.solar_terms.get(solar_term, [0, "0"])[1]), str(flag_day)

    def _get_lunar_time_handler(self, lu_month, lu_day, lu_time_point):
        leap_month = False
        if lu_month:
            lu_month_str = lu_month.group(1)
            if "闰" in lu_month_str:
                leap_month = True
            lu_month_str = (
                lu_month_str.replace("正", "一")
                .replace("冬", "十一")
                .replace("腊", "十二")
                .replace("闰", "")
            )
            lu_month_str = int(self._char_num2num(lu_month_str))

            lu_time_point.month = lu_month_str

        if lu_day:
            lu_day_str = lu_day.group(0)
            lu_day_str = lu_day_str.replace("初", "").replace("廿", "二十")
            lu_day_str = int(self._char_num2num(lu_day_str))

            lu_time_point.day = lu_day_str

        lu_time_handler = lu_time_point.handler()

        lu_time_handler = TimeUtility.time_completion(
            lu_time_handler, self.base_handler
        )

        return self._convert_lunar2solar(lu_time_handler, leap_month=leap_month)

    def _get_norm_limit_year_month_week(self, time_str, first_tp, second_tp):
        month = self.month_regs[0].search(time_str)
        if month:
            month_str = int(self._char_num2num(month.group(1)))
            first_tp.month = month_str
            second_tp.month = month_str

        first_point_day, second_point_day = self._norm_month_order_week(
            time_str, first_tp.month, first_tp.year
        )

        first_tp.month = first_point_day.month
        first_tp.day = first_point_day.day
        second_tp.year = second_point_day.year
        second_tp.month = second_point_day.month
        second_tp.day = second_point_day.day

        return first_tp.handler(), second_tp.handler()

    def _get_norm_limit_year_fixed_solar_festival(self, time_str, tp):
        for festival, date in self.fixed_solar_holiday_dict.items():
            if festival in time_str:
                tp.month = date[0]
                tp.day = date[1]
                break

        if tp.day < 0:
            raise ValueError(INPUT_TIME_ERROR)

        return tp.handler()

    def _get_norm_year_regular_solar_festival(self, time_str, tp):
        for festival, date in self.regular_solar_holiday_dict.items():
            if festival in time_str:
                tp.month = date.get(MONTH, -1)
                week_order_num = date.get(WEEK_EN, -1)
                week_day = date.get(DAY_EN, -1)

                one_week = datetime.timedelta(days=7)
                self._get_compute_week_day
                time_base_datetime = TimeParser._convert_handler_to_datetime(
                    [tp.year, tp.month, 1, 0, 0, 0]
                )

                target_day = self._get_compute_week_day(
                    time_base_datetime, week_day - 1
                )

                for _ in range(week_order_num - 1):
                    target_day += one_week

                time_handler = TimeParser._convert_time_base2handler(target_day)
                tp.day = time_handler[2]
                break

        if tp.day < 0:
            raise ValueError(INPUT_TIME_ERROR)

        return tp.handler()

    def _get_norm_limit_month_week(self, time_str, first_tp, second_tp):
        first_point_day, second_point_day = self._norm_month_order_week(
            time_str, first_tp.month
        )

        first_tp.month = first_point_day.month
        first_tp.day = first_point_day.day
        second_tp.year = second_point_day.year
        second_tp.month = second_point_day.month
        second_tp.day = second_point_day.day

        return first_tp.handler(), second_tp.handler()

    def _get_norm_limit_year_week(self, time_str, first_tp, second_tp):
        first_point_day, second_point_day = self._norm_year_order_week(
            time_str, first_tp.year
        )

        first_tp.month = first_point_day.month
        first_tp.day = first_point_day.day
        second_tp.year = second_point_day.year
        second_tp.month = second_point_day.month
        second_tp.day = second_point_day.day

        return first_tp.handler(), second_tp.handler()

    def _get_norm_limit_year_fixed_lunar_festival(self, time_str, tp):
        for festival, date in self.fixed_lunar_holiday_dict.items():
            if festival in time_str:
                first_solar_date, _ = self._convert_lunar2solar(
                    [tp.year, date[0], date[1], -1, -1, -1], False
                )
                tp.year = first_solar_date[0]
                tp.month = first_solar_date[1]
                tp.day = first_solar_date[2]
                break

        if tp.day < 0:
            raise ValueError(INPUT_TIME_ERROR)

        return tp.handler()

    def _get_compute_week_day(self, cur, target_week_day):
        one_day = datetime.timedelta(days=1)
        cur_week_day = cur.weekday()
        delta = cur_week_day - target_week_day
        if delta == 0:
            return cur
        if delta > 0:
            for _ in range(7 - delta):
                cur += one_day
        elif delta < 0:
            for _ in range(abs(delta)):
                cur += one_day

        return cur

    def _get_parse_tp_day_bias(self, full_time_handler_1, full_time_handler_2):
        first_full_timebase = self._convert_handler_to_datetime(full_time_handler_1)
        first_full_timebase += datetime.timedelta(days=1)
        _full_time_handler_1 = self._convert_time_base2handler(first_full_timebase)
        full_time_handler_1 = [
            i if i == -1 else j
            for i, j in zip(full_time_handler_1, _full_time_handler_1)
        ]

        second_full_timebase = self._convert_handler_to_datetime(full_time_handler_2)
        second_full_timebase += datetime.timedelta(days=1)
        _full_time_handler_2 = self._convert_time_base2handler(second_full_timebase)
        full_time_handler_2 = [
            i if i == -1 else j
            for i, j in zip(full_time_handler_2, _full_time_handler_2)
        ]
        return full_time_handler_1, full_time_handler_2

    def _get_underlying_future_time_with_flag(self, time_str, full_time_handler_1):
        matched_res = self.future_time_unit_reg.search(time_str)
        if matched_res:
            matched_unit = matched_res.group()
            if matched_unit in ["月", "节"]:
                time_str = "明年" + time_str
            elif matched_unit in ["日", "号"]:
                time_str = "下个月" + time_str
            elif matched_unit in ["周", "星期", "礼拜"]:
                time_str = "下" + time_str

            elif matched_unit in ["时", "点"]:
                if full_time_handler_1[3] != -1 and self.base_handler[3] != -1:
                    if full_time_handler_1[3] > self.base_handler[3]:
                        pass  # Parsed hour after base; keep same calendar day.
                    elif full_time_handler_1[3] < self.base_handler[3]:
                        time_str = TOMORROW_ZH + time_str
                    else:
                        if full_time_handler_1[4] != -1 and self.base_handler[4] != -1:
                            if full_time_handler_1[4] > self.base_handler[4]:
                                pass  # Parsed minute after base; keep same day.
                            elif full_time_handler_1[4] < self.base_handler[4]:
                                time_str = TOMORROW_ZH + time_str
                            else:
                                time_str = TOMORROW_ZH + time_str
                        else:
                            time_str = TOMORROW_ZH + time_str
                else:
                    time_str = TOMORROW_ZH + time_str
        return time_str
