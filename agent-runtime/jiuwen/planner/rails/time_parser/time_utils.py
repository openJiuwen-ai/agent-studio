# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

import datetime
import re
import time
from typing import NamedTuple, Optional, Callable

from jiuwen.planner.rails.time_parser.function import bracket, absence, bracket_absence
from jiuwen.planner.rails.time_parser.patterns import Pattern

CN_NUM = "零〇一二三四五六七八九"
ARABIC_NUM = "00123456789"
BIG_MOON = {1, 3, 5, 7, 8, 10, 12}
SMALL_MOON = {4, 6, 9, 11}
FUTURE = "inf"
PAST_TIME = "-inf"
WEEKDAYS = "[一二三四五六日末天]"
INPUT_TIME_ERROR = "input time str error"
OF_ZH = "(的)?"
ONE_TO_FIVE_ZH = "第[1-5一二三四五](个)?"
PIECE_ZH = "(个)?"
MONTH = "month"
WEEK_EN = "week"
DAY_EN = "day"
TOMORROW_ZH = "明天"
INFOS = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]
SPANS = ["初", "中", "末"]
ILLEGAL_TIME_STRING_ERROR = "the given string `{}` is illegal."


class TimePoint(object):
    def __init__(self):
        self.year, self.month, self.day, self.hour, self.minute, self.second = (
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
        )

    def __repr__(self):
        return "TimePoint: {},{},{}  {},{},{}".format(
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )

    def handler(self):
        """handler method"""
        return [self.year, self.month, self.day, self.hour, self.minute, self.second]

    def assign(self, *args):
        """assign method"""
        args_num = len(args)
        if args_num >= 1:
            self.year = args[0]
        if args_num >= 2:
            self.month = args[1]
        if args_num >= 3:
            self.day = args[2]
        if args_num >= 4:
            self.hour = args[3]
        if args_num >= 5:
            self.minute = args[4]
        if args_num >= 6:
            self.second = args[5]


class TimeParserResult:
    def __init__(
        self,
        cur_hms: str,
        cur_hms_func: Optional[Callable],
        cur_ymd: str,
        cur_ymd_func: Optional[Callable],
    ):
        self.cur_hms = cur_hms
        self.cur_hms_func = cur_hms_func
        self.cur_ymd = cur_ymd
        self.cur_ymd_func = cur_ymd_func


class TimeHandlerResult(NamedTuple):
    day_bias: int
    time_handler_1: list
    time_handler_2: list
    time_type: str


class TimeHandlerFuncResult(NamedTuple):
    hms_func_list: list
    hms_string_list: list
    ymd_func_list: list
    ymd_string_list: list


class TimeUtility(object):
    """utility of time parsing"""

    cn_num_2_arabic_num = str.maketrans(CN_NUM, ARABIC_NUM)
    single_num_reg = re.compile(Pattern.SINGLE_NUM_STR)

    def __init__(self):
        self._init_members_part_one()
        self._init_members_part_two()
        self._init_members_pattern()
        self.ymd_reg_norm_funcs = None
        self.hms_reg_norm_funcs = None

    def __call__(self, time_str: str = "", time_base=time.time(), ret_future=False):
        self._preprocess_regular_expression()

    @staticmethod
    def time_completion(handler, base_handler):
        """time_completion method"""
        if handler in ["inf", "-inf"]:
            return handler

        for i, _ in enumerate(handler):
            if handler[i] > -1:
                break
            handler[i] = base_handler[i]

        return handler

    @staticmethod
    def check_handler(handler):
        """check_handler method"""
        if handler in ["inf", "-inf"]:
            return True

        if set(handler) == {-1}:
            return False

        fir = False
        sec = False
        for i in range(5):
            if handler[i] > -1 and handler[i + 1] == -1:
                fir = True
            if handler[i] == -1 and handler[i + 1] > -1 and fir:
                sec = True

        if fir and sec:
            return False
        return True

    @staticmethod
    def parse_reg(time_str, reg):
        """parse_reg method"""
        searched_res = reg.search(time_str)
        if searched_res:
            return searched_res.group()
        return ""

    @staticmethod
    def parse_str_num(str_num):
        """parse_str_num method"""
        plus_nums = {
            "O": 0,
            "零": 0,
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
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
        }
        multi_nums = {"十": 10, "百": 100, "千": 1000, "万": 10000}

        if str_num[0] in "十百千":
            str_num = "一" + str_num

        tmp_nums = list()
        for char in list(str_num):
            plus_num = plus_nums.get(char, 0)
            if plus_num != 0:
                tmp_nums.append(plus_num)

            multi_num = multi_nums.get(char, 1)
            if len(tmp_nums) >= 1:
                tmp_nums[-1] = tmp_nums[-1] * multi_num

        rtn_std_num = sum(tmp_nums)
        return rtn_std_num

    @staticmethod
    def _convert_time_base2handler(base):
        """将 time_base 转换为 handler,"""
        if type(base) in [float, int]:
            # 即 timestamp
            time_array = datetime.datetime.fromtimestamp(base)
            base_handler = [
                time_array.year,
                time_array.month,
                time_array.day,
                time_array.hour,
                time_array.minute,
                time_array.second,
            ]
        elif isinstance(base, datetime.datetime):
            base_handler = [
                base.year,
                base.month,
                base.day,
                base.hour,
                base.minute,
                base.second,
            ]
        elif isinstance(base, list):
            if len(base) > 6:
                raise ValueError("length of time_base must be less than 6.")
            for i in base:
                if not isinstance(i, int):
                    raise ValueError("type of element of time_base must be `int`.")
            if len(base) < 6:
                base.extend([-1 for _ in range(6 - len(base))])
            base_handler = base
        elif isinstance(base, dict):
            base_handler = [
                base.get("year", -1),
                base.get("month", -1),
                base.get("day", -1),
                base.get("hour", -1),
                base.get("minute", -1),
                base.get("second", -1),
            ]
        elif isinstance(base, str):
            time_array = time.strptime(base, "%Y-%m-%d %H:%M:%S")
            base_handler = [
                time_array.tm_year,
                time_array.tm_mon,
                time_array.tm_mday,
                time_array.tm_hour,
                time_array.tm_min,
                time_array.tm_sec,
            ]
        elif base is None:
            base_handler = None
        else:
            raise ValueError("the given time_base is illegal.")

        return base_handler

    @staticmethod
    def _convert_handler_to_datetime(handler):
        format_handler = []
        for idx, i in enumerate(handler):
            if i > -1:
                format_handler.append(i)
            else:
                if idx in [0, 1, 2]:
                    format_handler.append(1)
                elif idx in [3, 4, 5]:
                    format_handler.append(0)

        return datetime.datetime(*format_handler)

    @staticmethod
    def _cleansing(time_str):
        return time_str.strip()

    @staticmethod
    def _compare_handler(first, second):
        for fir, sec in zip(first, second):
            if fir == -1 or sec == -1:
                break
            if fir == sec:
                continue
            if fir > sec:
                return 1
            if fir < sec:
                return -1
        return 0

    @staticmethod
    def _cut_zero_key(dict_obj):
        return dict([item for item in dict_obj.items() if item[1] > 0])

    @staticmethod
    def _check_if_lunar_run_year(input_year: int):
        return (input_year % 100 != 0 and input_year % 4 == 0) or (
            input_year % 100 == 0 and input_year % 400 == 0
        )

    @staticmethod
    def _first_time_handler2standard_time(time_handler_1):
        def _append_handler(_handler, _idx, _f):
            if _f > -1:
                _handler.append(_f)
            elif _f == -1:
                if _idx in [1, 2]:
                    _handler.append(1)
                elif _idx in [3, 4, 5]:
                    _handler.append(0)
                else:
                    raise ValueError("first time handler {} illegal.".format(_handler))
            else:
                raise ValueError("can not be converted to standard time reg.")

        handler_1 = []
        if time_handler_1 == PAST_TIME:
            time_str_1 = PAST_TIME
        else:
            for idx, f in enumerate(time_handler_1):
                _append_handler(handler_1, idx, f)

            try:
                time_str_1 = TimeUtility._convert_handler_to_datetime(handler_1)
            except Exception as _:
                raise ValueError("the given time str is illegal.") from _

        return time_str_1.strftime("%Y-%m-%d %H:%M:%S")

    def cn_year_char_2_arabic_year_char(self, char_year):
        """cn_year_char_2_arabic_year_char method"""
        arabic_year_char = char_year.translate(self.cn_num_2_arabic_num)
        return arabic_year_char

    def time_handler2standard_time(self, time_handler_1, time_handler_2):
        """time_handler2standard_time method"""
        time_str_1 = self._first_time_handler2standard_time(time_handler_1)
        time_str_2 = self._second_time_handler2standard_time(time_handler_2)

        return time_str_1, time_str_2

    def _char_num2num(self, char_num):
        num_reg = re.compile(r"^\d+(\.)?\d*$")
        if num_reg.search(char_num):
            res_num = float(char_num)
        else:
            res_num = self.parse_str_num(char_num)
        return float(res_num)

    def _second_time_handler2standard_time(self, time_handler_2):
        def _append_handler(_handler, _idx):
            if _idx == 1:
                _handler.append(12)
            elif _idx == 2:
                if _handler[1] in BIG_MOON:
                    handler_2.append(31)
                elif _handler[1] in SMALL_MOON:
                    handler_2.append(30)
                else:
                    if self._check_if_lunar_run_year(_handler[0]):
                        _handler.append(29)
                    else:
                        _handler.append(28)
            elif _idx == 3:
                _handler.append(23)
            elif _idx == 4:
                _handler.append(59)
            elif _idx == 5:
                _handler.append(59)
            else:
                raise ValueError("second time handler illegal.")

        handler_2 = []
        if time_handler_2 == FUTURE:
            time_str_2 = FUTURE
        else:
            for idx, s in enumerate(time_handler_2):
                if s > -1:
                    handler_2.append(s)
                elif s == -1:
                    _append_handler(handler_2, idx)
                else:
                    raise ValueError(
                        "before Christ {} can not be converted to standard time reg.".format(
                            time_handler_2
                        )
                    )

            try:
                time_str_2 = TimeUtility._convert_handler_to_datetime(handler_2)
            except Exception as _:
                raise ValueError("the given time str is illegal.") from _

        return time_str_2.strftime("%Y-%m-%d %H:%M:%S")

    def _init_members_part_two(self):
        self.year_regs = None
        self.month_reg = None
        self.month_num_reg = None
        self.span_month_reg = None
        self.solar_season_reg = None
        self.lunar_month_reg = None
        self.month_regs = None
        self.day_1_reg = None
        self.day_2_reg = None
        self.lunar_day_reg = None
        self.lunar_24st_reg = None
        self.lunar_season_reg = None
        self.week_1_reg = None
        self.week_2_reg = None
        self.week_3_reg = None
        self.week_4_reg = None
        self.week_5_reg = None
        self.ymd_segs = None
        self.week_num_reg = None
        self.day_regs = None
        self.hour_reg = None
        self.hour_limitation_reg = None
        self.hour_regs = None
        self.minute_reg = None
        self.limit_minute_reg = None
        self.minute_regs = None
        self.second_reg = None
        self.hms_segs = None
        self.second_regs = None
        self.first_1_span_reg = None
        self.first_2_span_reg = None
        self.first_3_span_reg = None
        self.first_4_span_reg = None
        self.first_5_span_reg = None
        self.second_0_span_reg = None
        self.second_1_span_reg = None
        self.second_2_span_reg = None
        self.second_3_span_reg = None
        self.fixed_solar_holiday_dict = None
        self.fixed_lunar_holiday_dict = None
        self.regular_solar_holiday_dict = None
        self.time_span_point_compensation = None
        self.special_time_span_reg = None

    def _init_members_part_one(self):
        self.cn_char_reg = None
        self.time_span_seg_standard_year_month_to_year_month = None
        self.time_span_no_seg_standard_year_month_day = None
        self.standard_year_month_day_reg = None
        self.standard_year_reg = None
        self.year_month_day_reg = None
        self.year_solar_season_reg = None
        self.limit_year_solar_season_reg = None
        self.limit_solar_season_reg = None
        self.year_span_month_reg = None
        self.limit_year_span_month_reg = None
        self.limit_month_day_reg = None
        self.limit_month_reg = None
        self.limit_year_month_day_reg = None
        self.enum_day_reg = None
        self.lunar_year_month_day_reg = None
        self.lunar_limit_year_month_day_reg = None
        self.year_lunar_season_reg = None
        self.limit_year_lunar_season_reg = None
        self.year_24st_reg = None
        self.standard_week_day_reg = None
        self.limit_week_reg = None
        self.year_month_week_reg = None
        self.limit_year_month_week_reg = None
        self.month_week_reg = None
        self.limit_month_week_reg = None
        self.year_week_reg = None
        self.limit_year_week_reg = None
        self.num_month_num_reg = None
        self.year_fixed_solar_festival_reg = None
        self.limit_year_fixed_solar_festival_reg = None
        self.year_fixed_lunar_festival_reg = None
        self.limit_year_fixed_lunar_festival_reg = None
        self.year_regular_solar_festival_reg = None
        self.limit_year_regular_solar_festival_reg = None
        self.limit_day_reg = None
        self.hour_minute_second_reg = None
        self.num_hour_minute_second_reg = None
        self.hour_limit_minute_reg = None
        self.single_num_reg = None
        self.year_reg = None
        self.limit_year_reg = None
        self.century_reg = None
        self.decade_reg = None
        self.year_num_reg = None

    def _init_members_pattern(self):
        # 中文字符判定
        self.chinese_char_pattern = None
        # **** 月 ****
        self.month_pattern = None
        self.month_num_pattern = None
        self.span_month_pattern = None
        self.solar_season_pattern = None
        self.blur_month_pattern = None
        self.lunar_month_pattern = None
        # `限定月`： `下个月`
        self.limit_month_pattern = None
        self.month_patterns = None
        # **** 日|星期 ****
        self.day_1_pattern = None
        self.day_2_pattern = None
        self.day_3_pattern = None
        self.lunar_day_pattern = None
        self.lunar_24st_pattern = None
        self.lunar_season_pattern = None
        self.week_1_pattern = None
        self.week_2_pattern = None
        self.week_3_pattern = None
        self.week_4_pattern = None
        self.week_5_pattern = None
        self.ymd_segs = None
        self.week_num_pattern = None
        self.day_patterns = None
        # **** 年 ****
        self.year_pattern = None
        self.limit_year_pattern = None
        self.blur_year_1_pattern = None
        self.blur_year_2_pattern = None
        self.blur_year_3_pattern = None
        self.lunar_year_pattern = None
        self.century_pattern = None
        self.decade_pattern = None
        self.year_num_pattern = None
        self.year_patterns = None
        # 将时间段转换为时间点
        self.day_delta_point_pattern = None
        self.day_delta_pattern = None
        self.delta_num_pattern = None

    def _preprocess_regular_expression(self):
        self._exec_preprocess_pattern()
        self._exec_preprocess_one()
        self._exec_preprocess_two()
        self._exec_preprocess_three()
        self._exec_preprocess_four()
        self._exec_preprocess_five()

    def _exec_preprocess_one(self):
        self.cn_char_reg = re.compile(Pattern.CN_CHAR)

        self.time_span_seg_standard_year_month_to_year_month = re.compile(
            r"((17|18|19|20|21)\d{2})[./](1[012]|[0]?\d)[\-]((17|18|19|20|21)\d{2})([./](1[012]|[0]?\d))?"
        )

        self.time_span_no_seg_standard_year_month_day = re.compile(
            r"((17|18|19|20|21)\d{2})\-(1[012]|[0]?\d)[\-./](30|31|[012]?\d)|((17|18|19|20|21)\d{2})[\-./]"
            r"(1[012]|[0]?\d)\-(30|31|[012]?\d)|(^\d)(1[012]|[0]?\d)\-(30|31|[012]?\d)(^\d)"
        )

        self.standard_year_month_day_reg = re.compile(
            r"((17|18|19|20|21)\d{2})[\-./](1[012]|[0]?\d)([\-./](30|31|[012]?\d))?[ \t\u3000\-./]?|((17|18|19|20|21)"
            r"\d{2} (1[012]|[0]?\d) (30|31|[012]?\d))|(1[012]|[0]?\d)[·\-/](30|31|[012]?\d)"
        )

        self.standard_year_reg = re.compile(r"(17|18|19|20|21)\d{2}")

        self.year_month_day_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.YEAR_STRING),
                    bracket_absence(Pattern.M_STR),
                    bracket_absence(Pattern.D_STR),
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.M_STR),
                    bracket_absence(Pattern.D_STR),
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.D_STR),
                ]
            )
        )

        self.year_solar_season_reg = re.compile(
            "".join(
                [
                    bracket_absence(Pattern.YEAR_STRING),
                    r"(([第前后头Qq]?[一二三四1-4两]|首)(个)?季度[初中末]?)",
                ]
            )
        )

        self.limit_year_solar_season_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    r"(([第前后头Qq]?[一二三四1-4两]|首)(个)?季度[初中末]?)",
                ]
            )
        )

        self.limit_solar_season_reg = re.compile(r"([上下](个)?|本|这)季度[初中末]?")

        self.year_span_month_reg = re.compile(
            "".join(
                [
                    bracket_absence(Pattern.YEAR_STRING),
                    r"(([第前后头]",
                    Pattern.M_NUM_STR,
                    r"|首)(个)?月(份)?)",
                ]
            )
        )

        self.limit_year_span_month_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    r"(([第前后头]",
                    Pattern.M_NUM_STR,
                    r"|首)(个)?月(份)?)",
                ]
            )
        )

        self.limit_month_day_reg = re.compile(
            "".join([bracket(Pattern.LIMIT_M_STR), bracket_absence(Pattern.D_STR)])
        )

        self.limit_month_reg = re.compile(Pattern.LIMIT_M_STR)

        self.limit_year_month_day_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    bracket_absence(Pattern.M_STR),
                    bracket_absence(Pattern.D_STR),
                ]
            )
        )

        self.enum_day_reg = re.compile(
            "".join(
                [
                    bracket_absence(Pattern.YEAR_STRING),
                    bracket_absence(Pattern.M_STR),
                    bracket(Pattern.D_STR),
                    bracket("[、，, ]" + bracket(Pattern.D_STR)),
                    "+",
                ]
            )
        )

        self.lunar_year_month_day_reg = re.compile(
            "".join(
                [
                    Pattern.LU_A,
                    bracket_absence(Pattern.LUNAR_Y_STR),
                    Pattern.LU_A,
                    bracket_absence(Pattern.LUNAR_M_STR),
                    Pattern.SELF_EVI_LUNAR_D_STR,
                    Pattern.VERTICAL_LINE,
                    Pattern.LU_A,
                    bracket_absence(Pattern.LUNAR_Y_STR),
                    Pattern.LU_A,
                    bracket(Pattern.SELF_EVI_LUNAR_M_STR),
                    absence(Pattern.LUNAR_SOLAR_D_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    bracket(Pattern.LUNAR_Y_STR),
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.LUNAR_Y_STR),
                    Pattern.LU,
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU_A,
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.LUNAR_D_STR,
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    bracket(Pattern.LUNAR_Y_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    Pattern.LUNAR_D_STR,
                ]
            )
        )

    def _exec_preprocess_two(self):
        self.lunar_limit_year_month_day_reg = re.compile(
            "".join(
                [
                    Pattern.LU_A,
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.LU_A,
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.SELF_EVI_LUNAR_D_STR,
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.LU_A,
                    bracket(Pattern.SELF_EVI_LUNAR_M_STR),
                    absence(Pattern.LUNAR_SOLAR_D_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU_A,
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.LU_A,
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.LUNAR_D_STR,
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.VERTICAL_LINE,
                    Pattern.LU,
                    bracket(Pattern.LIMIT_Y_STR),
                    bracket(Pattern.LUNAR_M_STR),
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.LU,
                    bracket(Pattern.LUNAR_M_STR),
                ]
            )
        )

        self.year_lunar_season_reg = re.compile(
            "".join(
                [
                    bracket_absence(Pattern.LUNAR_Y_STR),
                    r"[春夏秋冬][季天]|",
                    bracket(Pattern.LUNAR_Y_STR),
                    r"[春夏秋冬]",
                ]
            )
        )

        self.limit_year_lunar_season_reg = re.compile(
            "".join([bracket(Pattern.LIMIT_Y_STR), r"[春夏秋冬][季天]?"])
        )

        self.year_24st_reg = re.compile(
            "".join([bracket_absence(Pattern.LUNAR_Y_STR), Pattern.SOLAR_TERM_STR])
        )

        self.standard_week_day_reg = re.compile(
            "(上上|上|下下|下|本|这)?(一)?(个)?(周)?" + Pattern.W_STR + WEEKDAYS
        )

        self.limit_week_reg = re.compile(
            "".join(
                [bracket(Pattern.M_STR), OF_ZH, ONE_TO_FIVE_ZH, Pattern.W_STR, WEEKDAYS]
            )
        )

        self.year_month_week_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.YEAR_STRING),
                    bracket(Pattern.M_STR),
                    "的?",
                    ONE_TO_FIVE_ZH,
                    Pattern.W_STR,
                ]
            )
        )

        self.limit_year_month_week_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    bracket(Pattern.M_STR),
                    "的?",
                    ONE_TO_FIVE_ZH,
                    Pattern.W_STR,
                ]
            )
        )

        self.month_week_reg = re.compile(
            "".join([bracket(Pattern.M_STR), OF_ZH, ONE_TO_FIVE_ZH, Pattern.W_STR])
        )

        self.limit_month_week_reg = re.compile(
            "".join(
                [bracket(Pattern.LIMIT_M_STR), OF_ZH, ONE_TO_FIVE_ZH, Pattern.W_STR]
            )
        )

        self.year_week_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.YEAR_STRING),
                    "第",
                    bracket(Pattern.W_NUM_STR),
                    PIECE_ZH,
                    Pattern.W_STR,
                ]
            )
        )

        self.limit_year_week_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    "第",
                    bracket(Pattern.W_NUM_STR),
                    PIECE_ZH,
                    Pattern.W_STR,
                ]
            )
        )
        self.num_month_num_reg = re.compile(
            "".join(["^", Pattern.M_NUM_STR, "月", "([12]\\d|3[01]|[0]?[1-9])", "$"])
        )
        self.year_fixed_solar_festival_reg = re.compile(
            "".join(
                [bracket_absence(Pattern.YEAR_STRING), Pattern.FIXED_SOLAR_FESTIVAL]
            )
        )
        self.limit_year_fixed_solar_festival_reg = re.compile(
            bracket(Pattern.LIMIT_Y_STR) + Pattern.FIXED_SOLAR_FESTIVAL
        )

    def _exec_preprocess_three(self):
        self.year_fixed_lunar_festival_reg = re.compile(
            "".join(
                [
                    bracket_absence(Pattern.YEAR_STRING),
                    Pattern.LU_A,
                    Pattern.FIXED_LUNAR_FESTIVAL,
                ]
            )
        )

        self.limit_year_fixed_lunar_festival_reg = re.compile(
            "".join(
                [
                    bracket(Pattern.LIMIT_Y_STR),
                    Pattern.LU_A,
                    Pattern.FIXED_LUNAR_FESTIVAL,
                ]
            )
        )

        self.year_regular_solar_festival_reg = re.compile(
            bracket_absence(Pattern.YEAR_STRING) + Pattern.REG_FOREIGN_FESTIVAL
        )

        self.limit_year_regular_solar_festival_reg = re.compile(
            bracket_absence(Pattern.LIMIT_Y_STR) + Pattern.REG_FOREIGN_FESTIVAL
        )

        self.limit_day_reg = re.compile(
            r"(前|今|明|同一|当|后|大大前|大大后|大前|大后|昨|次|本)[天日晚]"
        )

        self.hour_minute_second_reg = re.compile(
            "".join(
                [
                    absence(Pattern.BLUR_H_STR),
                    bracket(Pattern.H_STR),
                    bracket_absence(Pattern.MIN_SEC_STR + "分?"),
                    bracket_absence(Pattern.MIN_SEC_STR + "秒"),
                    Pattern.VERTICAL_LINE,
                    bracket(Pattern.MIN_SEC_STR + "分"),
                    bracket_absence(Pattern.MIN_SEC_STR + "秒"),
                ]
            )
        )

        self.num_hour_minute_second_reg = re.compile(
            "".join(
                [
                    absence(Pattern.BLUR_H_STR),
                    r"([01]\d|2[01234]|\d)[:：]([012345]\d)([:：]([012345]\d))?",
                    r"(时)?",
                    Pattern.VERTICAL_LINE,
                    r"([012345]\d)[:：]([012345]\d)",
                    r"(时)?",
                ]
            )
        )

        self.hour_limit_minute_reg = re.compile(
            "".join(
                [
                    absence(Pattern.BLUR_H_STR),
                    bracket(Pattern.H_STR),
                    r"([123一二三]刻|半)",
                ]
            )
        )

        self.single_num_reg = re.compile(Pattern.SINGLE_NUM_STR)

        self.year_reg = re.compile(Pattern.YEAR_STRING[:-1] + r"(?=年)")
        self.limit_year_reg = re.compile(Pattern.LIMIT_Y_STR[:-1] + r"(?=年)")

        self.century_reg = re.compile(
            r"(\d{1,2}|((二)?十)?[一二三四五六七八九]|(二)?十|上)(?=世纪)"
        )
        self.decade_reg = re.compile(r"(\d0|[一二三四五六七八九]十)(?=年代)")
        self.year_num_reg = re.compile("[一二两三四五六七八九十百千0-9]{1,4}")

        self.year_regs = [self.year_reg, self.limit_year_reg]

        self.month_reg = re.compile(Pattern.M_STR)
        self.month_num_reg = re.compile(Pattern.M_NUM_STR)
        self.span_month_reg = re.compile(
            "([第前后头]([一二两三四五六七八九十]|十[一二]|[1-9]|1[012])|首)(个)?月(份)?"
        )
        self.solar_season_reg = re.compile(
            "((([第前后头Qq][一二三四1-4两]|首)(个)?|[一二三四1-4])季度[初中末]?)"
        )
        self.lunar_month_reg = re.compile(bracket(Pattern.LUNAR_M_STR[:-1]) + "(?=月)")

        self.month_regs = [
            self.month_reg,
            self.solar_season_reg,
            self.span_month_reg,
            self.lunar_month_reg,
            self.limit_month_reg,
        ]

        self.day_1_reg = re.compile(Pattern.D_STR)
        self.day_2_reg = re.compile(
            r"(前|今|明|同一|当|后|大大前|大大后|大前|大后|昨|次)(?=[天日晚])"
        )
        self.lunar_day_reg = re.compile(Pattern.LUNAR_D_STR + "(?!月)")
        self.lunar_24st_reg = re.compile(Pattern.SOLAR_TERM_STR)
        self.lunar_season_reg = re.compile("([春夏秋冬][季天]?)")

        self.week_1_reg = re.compile(
            "[前后][一二两三四五六七八九1-9](个)?" + Pattern.W_STR
        )
        self.week_2_reg = re.compile(
            "[一两三四五六七八九1-9](个)?" + Pattern.W_STR + "(之)?[前后]"
        )
        self.week_3_reg = re.compile(
            "(上上|上|下下|下|本|这)(一)?(个)?" + Pattern.W_STR
        )
        self.week_4_reg = re.compile(Pattern.W_STR + WEEKDAYS)
        self.week_5_reg = re.compile(
            "".join(["第", Pattern.W_NUM_STR, PIECE_ZH, Pattern.W_STR])
        )
        self.ymd_segs = re.compile(r"[\-.·/ ]")
        self.week_num_reg = re.compile(Pattern.W_NUM_STR)

    def _exec_preprocess_four(self):
        self.day_regs = [
            self.day_1_reg,
            self.lunar_day_reg,
            self.lunar_24st_reg,
            self.lunar_season_reg,
            self.week_1_reg,
            self.week_2_reg,
            self.week_3_reg,
            self.week_4_reg,
            self.week_5_reg,
            self.day_2_reg,
        ]

        self.hour_reg = re.compile(Pattern.H_STR.replace("[时点]", "") + r"(?=[时点])")
        self.hour_limitation_reg = re.compile(Pattern.BLUR_H_STR)

        self.hour_regs = [self.hour_reg, self.hour_limitation_reg]

        self.minute_reg = re.compile(r"(?<=[时点])" + Pattern.MIN_SEC_STR + "(?=分)?")
        self.limit_minute_reg = re.compile(r"(?<=[时点])([123一二三]刻|半)")

        self.minute_regs = [self.minute_reg, self.limit_minute_reg]

        self.second_reg = re.compile(r"(?<=分)" + Pattern.MIN_SEC_STR + "(?=秒)?")
        self.hms_segs = re.compile("[:：]")
        self.second_regs = [
            self.second_reg,
        ]

        self.first_1_span_reg = re.compile(
            r"(?<=(从|自))([^起到至\-—~～]+)(?=(起|到|至|以来|开始|—|－|-|~|～))|(?<=(从|自))([^起到至\-—~～]+)"
        )
        self.first_2_span_reg = re.compile(r"(.+)(?=(——|--|~~|－－|～～))")
        self.first_3_span_reg = re.compile(
            r"([^起到至\-—~～]+)(?=(起|到|至|以来|开始|－|—|-|~|～))"
        )
        self.first_4_span_reg = re.compile(r"(.+)(?=(之后|以后)$)")
        self.first_5_span_reg = re.compile(r"(.+)(?=(后)$)")

        self.second_0_span_reg = re.compile(r"(?<=(以来|开始|——|--|~~|－－|～～))(.+)")
        self.second_1_span_reg = re.compile(
            r"(?<=[起到至\-—~～－])([^起到至\-—~～－]+)(?=([之以]?前|止)$)"
        )
        self.second_2_span_reg = re.compile(
            r"(?<=[起到至\-—~～－])([^起到至\-—~～－]+)"
        )
        self.second_3_span_reg = re.compile(
            r"^((\d{1,2}|[一二两三四五六七八九十百千]+)[几多]?年(半)?(多)?|半年(多)?|几[十百千](多)?年)(?=([之以]?前|止)$)"
        )

        self.fixed_solar_holiday_dict = {
            "元旦": [1, 1],
            "妇女节": [3, 8],
            "女神节": [3, 8],
            "三八": [3, 8],
            "植树节": [3, 12],
            "五一": [5, 1],
            "劳动节": [5, 1],
            "青年节": [5, 4],
            "六一": [6, 1],
            "儿童节": [6, 1],
            "七一": [7, 1],
            "建党节": [7, 1],
            "八一": [8, 1],
            "建军节": [8, 1],
            "教师节": [9, 10],
            "国庆节": [10, 1],
            "十一": [10, 1],
            "国庆": [10, 1],
            "清明节": [4, 5],
            "情人节": [2, 14],
            "愚人节": [4, 1],
            "万圣节": [10, 31],
            "圣诞": [12, 25],
            "地球日": [4, 22],
            "护士节": [5, 12],
            "三一五": [3, 15],
            "消费者权益日": [3, 15],
            "三.一五": [3, 15],
            "三·一五": [3, 15],
            "双11": [11, 11],
            "双十一": [11, 11],
        }

        self.fixed_lunar_holiday_dict = {
            "春节": [1, 1],
            "大年初一": [1, 1],
            "大年初二": [1, 2],
            "大年初三": [1, 3],
            "大年初四": [1, 4],
            "大年初五": [1, 5],
            "大年初六": [1, 6],
            "大年初七": [1, 7],
            "大年初八": [1, 8],
            "大年初九": [1, 9],
            "大年初十": [1, 10],
            "元宵": [1, 15],
            "填仓节": [1, 25],
            "龙抬头": [2, 2],
            "上巳节": [3, 3],
            "寒食节": [4, 3],
            "浴佛节": [4, 8],
            "端午": [5, 5],
            "端阳": [5, 5],
            "姑姑节": [6, 6],
            "七夕": [7, 7],
            "中元": [7, 15],
            "财神节": [7, 22],
            "中秋": [8, 15],
            "重阳": [9, 9],
            "下元节": [10, 15],
            "寒衣节": [10, 1],
            "腊八": [12, 8],
            "除夕": [12, 30],
        }

    def _exec_preprocess_five(self):
        self.regular_solar_holiday_dict = {
            "母亲节": {MONTH: 5, WEEK_EN: 2, DAY_EN: 7},
            "父亲节": {MONTH: 6, WEEK_EN: 3, DAY_EN: 7},
            "感恩节": {MONTH: 11, WEEK_EN: 4, DAY_EN: 4},
        }

        self.time_span_point_compensation = re.compile(
            absence(Pattern.BLUR_H_STR)
            + r"(?!:)[\d一二三四五六七八九十零]{1,2}[月日号点时]?(到|至|——|－－|--|~~|～～|—|－|-|~|～)"
            r"([\d一二三四五六七八九十零]{1,2}[月日号点时]|[\d一二三四五六七八九十零]{2,4}年)"
        )

        self.special_time_span_reg = re.compile(r"(今明两[天年]|全[天月年])")

        self.ymd_reg_norm_funcs = [
            [self.enum_day_reg, self.normalize_enum_day_pattern],
            [self.standard_year_month_day_reg, self._norm_standard_year_month_day],
            [self.year_24st_reg, self.norm_year_24st],
            [self.limit_year_lunar_season_reg, self._norm_limit_year_lunar_season],
            [self.year_lunar_season_reg, self._norm_year_lunar_season],
            [self.limit_year_solar_season_reg, self._norm_limit_year_solar_season],
            [self.limit_solar_season_reg, self._norm_limit_solar_season],
            [self.year_solar_season_reg, self._norm_year_solar_season],
            [self.limit_month_week_reg, self._norm_limit_month_week],
            [self.month_week_reg, self._norm_month_week],
            [self.year_month_week_reg, self._norm_year_month_week],
            [self.limit_year_month_week_reg, self._norm_limit_year_month_week],
            [self.limit_year_week_reg, self._norm_limit_year_week],
            [self.year_week_reg, self._norm_year_week],
            [self.limit_week_reg, self._norm_limit_week],
            [self.standard_week_day_reg, self._norm_standard_week_day],
            [self.limit_month_day_reg, self._norm_limit_month_day],
            [self.limit_month_reg, self.norm_limit_month],
            [self.limit_year_span_month_reg, self._norm_limit_year_span_month],
            [self.year_span_month_reg, self._norm_year_span_month],
            [
                self.limit_year_fixed_solar_festival_reg,
                self._norm_limit_year_fixed_solar_festival,
            ],
            [
                self.limit_year_fixed_lunar_festival_reg,
                self._norm_limit_year_fixed_lunar_festival,
            ],
            [self.year_fixed_lunar_festival_reg, self._norm_year_fixed_lunar_festival],
            [
                self.limit_year_regular_solar_festival_reg,
                self._norm_limit_year_regular_solar_festival,
            ],
            [
                self.year_regular_solar_festival_reg,
                self._norm_year_regular_solar_festival,
            ],
            [
                self.lunar_limit_year_month_day_reg,
                self._norm_lunar_limit_year_month_day,
            ],
            [self.limit_year_month_day_reg, self._norm_limit_year_month_day],
            [self.limit_day_reg, self._norm_limit_day],
            [self.year_fixed_solar_festival_reg, self._norm_year_fixed_solar_festival],
            [self.lunar_year_month_day_reg, self._norm_lunar_year_month_day],
            [self.year_month_day_reg, self._norm_year_month_day],
            [self.standard_year_reg, self._norm_standard_year],
            [self.special_time_span_reg, self._norm_special_time_span],
            # time delta 2 point group
            [self.day_delta_point_pattern, self.normalize_day_delta_point],
        ]
        self.hms_reg_norm_funcs = [
            [self.hour_minute_second_reg, self._norm_hour_minute_second],
            [self.num_hour_minute_second_reg, self._norm_num_hour_minute_second],
            [self.hour_limit_minute_reg, self._norm_hour_limit_minute],
        ]

    def _exec_preprocess_pattern(self):
        # 中文字符判定
        self.chinese_char_pattern = re.compile(Pattern.CHINESE_CHAR_PATTERN)
        # **** 月 ****
        self.month_pattern = re.compile(Pattern.MONTH_STRING)
        self.month_num_pattern = re.compile(Pattern.MONTH_NUM_STRING)  # 1~12
        self.span_month_pattern = re.compile(
            "([第前后头]([一二两三四五六七八九十]|十[一二]|[1-9]|1[012])|首)(个)?月(份)?"
        )
        self.solar_season_pattern = re.compile(
            "((([第前后头Qq][一二三四1-4两]|首)(个)?|[一二三四1-4])季度[初中末]?)"
        )
        self.blur_month_pattern = re.compile(Pattern.BLUR_MONTH_STRING)
        self.lunar_month_pattern = re.compile(
            bracket(Pattern.LUNAR_MONTH_STRING[:-1]) + "(?=月)"
        )
        # `限定月`： `下个月`
        self.limit_month_pattern = re.compile(Pattern.LIMIT_MONTH_STRING)
        self.month_patterns = [
            self.month_pattern,
            self.solar_season_pattern,
            self.blur_month_pattern,
            self.span_month_pattern,
            self.lunar_month_pattern,
            self.limit_month_pattern,
        ]
        # **** 日|星期 ****
        self.day_1_pattern = re.compile(Pattern.DAY_STRING)
        self.day_2_pattern = re.compile(
            r"(前|今|明|同一|当|后|大大前|大大后|大前|大后|昨|次)(?=[天日晚])"
        )  # 昨晚9点
        self.day_3_pattern = re.compile(Pattern.BLUR_DAY_STRING)
        self.lunar_day_pattern = re.compile(Pattern.LUNAR_DAY_STRING + "(?!月)")
        self.lunar_24st_pattern = re.compile(Pattern.SOLAR_TERM_STR)
        self.lunar_season_pattern = re.compile("([春夏秋冬][季天]?)")
        self.week_1_pattern = re.compile(
            "[前后][一二两三四五六七八九1-9](个)?" + Pattern.WEEK_STRING
        )
        self.week_2_pattern = re.compile(
            "[一两三四五六七八九1-9](个)?" + Pattern.WEEK_STRING + "(之)?[前后]"
        )
        self.week_3_pattern = re.compile(
            "(上+|下+|本|这)(一)?(个)?" + Pattern.WEEK_STRING
        )
        self.week_4_pattern = re.compile(Pattern.WEEK_STRING + "[一二三四五六日末天]")
        self.week_5_pattern = re.compile(
            "".join(["第", Pattern.WEEK_NUM_STRING, "(个)?", Pattern.WEEK_STRING])
        )
        self.ymd_segs = re.compile(r"[\-.·/ ]")
        self.week_num_pattern = re.compile(Pattern.WEEK_NUM_STRING)
        self.day_patterns = [
            self.day_1_pattern,
            self.lunar_day_pattern,
            self.lunar_24st_pattern,
            self.lunar_season_pattern,
            self.day_3_pattern,
            self.week_1_pattern,
            self.week_2_pattern,
            self.week_3_pattern,
            self.week_4_pattern,
            self.week_5_pattern,
            self.day_2_pattern,
        ]
        # **** 年 ****
        self.year_pattern = re.compile(Pattern.YEAR_STRING[:-1] + r"(?=年)")
        self.limit_year_pattern = re.compile(Pattern.LIMIT_YEAR_STRING[:-1] + r"(?=年)")
        self.century_pattern = re.compile(
            r"(\d{1,2}|((二)?十)?[一二三四五六七八九]|(二)?十|上)(?=世纪)"
        )
        self.decade_pattern = re.compile(r"(\d0|[一二三四五六七八九]十)(?=年代)")
        self.blur_year_3_pattern = re.compile("几[十百千](多)?年[以之]?[前后]")
        self.year_num_pattern = re.compile("[一二两三四五六七八九十百千0-9]{1,4}")
        self.lunar_year_pattern = re.compile(
            "[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]年"
        )
        self.year_patterns = [
            self.year_pattern,
            self.limit_year_pattern,
            self.blur_year_1_pattern,
            self.blur_year_2_pattern,
            self.blur_year_3_pattern,
            self.lunar_year_pattern,
        ]
        self.blur_year_1_pattern = re.compile(
            r"([12]?\d{1,4}|(?<!几)[一二两三四五六七八九十百千])[几多]?年(半)?(多)?[以之]?[前后]"
        )
        self.day_delta_point_pattern = re.compile(
            "".join([bracket(Pattern.DAY_DELTA_STRING), Pattern.DELTA_SUB])
        )
        self.day_delta_pattern = re.compile(bracket(Pattern.DAY_DELTA_STRING))
        self.delta_num_pattern = re.compile(Pattern.DELTA_NUM_STRING)
        self.blur_year_2_pattern = re.compile("半年(多)?[以之]?[前后]")
