import logging

from jiuwen.common.log.base import MaskingFormatter


class TestMaskingFormatter:
    @staticmethod
    def _format(msg, sensitive_words=None, sensitive_patterns=None):
        formatter = MaskingFormatter(
            fmt="%(message)s",
            sensitive_words=sensitive_words,
            sensitive_patterns=sensitive_patterns,
            truncate_for_console=False,
        )
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return formatter.format(record)

    def test_no_masking(self):
        assert self._format("hello world") == "hello world"

    def test_sensitive_words_whole_line(self):
        result = self._format("选择的银行卡号6123456789012345，开始转账", sensitive_words=["银行卡号"])
        assert result == "选择的*****"

    def test_sensitive_patterns_only_mask_matched(self):
        result = self._format(
            "选择的银行卡号6123456789012345，开始转账",
            sensitive_patterns=[r"\d{16,19}"],
        )
        assert result == "选择的银行卡号****************，开始转账"

    def test_sensitive_patterns_phone(self):
        result = self._format(
            "用户手机号13812345678已验证",
            sensitive_patterns=[r"1[1-9]\d{9}"],
        )
        assert result == "用户手机号***********已验证"

    def test_sensitive_patterns_multiple(self):
        result = self._format(
            "手机13812345678卡号6123456789012345",
            sensitive_patterns=[r"\d{16,19}", r"1[1-9]\d{9}"],
        )
        assert result == "手机***********卡号****************"

    def test_sensitive_patterns_no_match(self):
        result = self._format("hello world", sensitive_patterns=[r"\d{16,19}"])
        assert result == "hello world"

    def test_both_words_and_patterns(self):
        result = self._format(
            "银行卡号6123456789012345手机13812345678",
            sensitive_words=["银行卡号"],
            sensitive_patterns=[r"1[1-9]\d{9}"],
        )
        assert result == "*****"

    def test_patterns_before_words(self):
        result = self._format(
            "卡号6123456789012345手机13812345678",
            sensitive_words=["银行卡号"],
            sensitive_patterns=[r"\d{16,19}", r"1[1-9]\d{9}"],
        )
        assert result == "卡号****************手机***********"

    def test_empty_patterns(self):
        assert self._format("hello", sensitive_patterns=[]) == "hello"

    def test_mask_length_preserved(self):
        result = self._format(
            "卡号12345678",
            sensitive_patterns=[r"\d{8}"],
        )
        assert result == "卡号********"
        assert len(result) == len("卡号12345678")

    def test_pattern_boundary_no_false_match_in_node_id(self):
        result = self._format(
            "node_1781511436918",
            sensitive_patterns=[r"1[1-9]\d{9}"],
        )
        assert result == "node_1781511436918"

    def test_pattern_boundary_phone_still_matched(self):
        result = self._format(
            "手机号13812345678已验证",
            sensitive_patterns=[r"1[1-9]\d{9}"],
        )
        assert result == "手机号***********已验证"

    def test_pattern_boundary_test_phone_11111112231(self):
        result = self._format(
            "转账100元给我手机号为11111112231",
            sensitive_patterns=[r"1[1-9]\d{9}"],
        )
        assert result == "转账100元给我手机号为***********"

    def test_pattern_boundary_bank_card_no_false_match_in_uuid(self):
        result = self._format(
            "id_a1234567890123456end",
            sensitive_patterns=[r"\d{16,19}"],
        )
        assert result == "id_a1234567890123456end"

    def test_pattern_boundary_bank_card_still_matched(self):
        result = self._format(
            "卡号6123456789012345完成",
            sensitive_patterns=[r"\d{16,19}"],
        )
        assert result == "卡号****************完成"

    def test_pattern_id_card(self):
        id_card_pattern = (
            r"[1-9]\d{5}(?:19|20)\d{2}"
            r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
            r"\d{3}[0-9Xx]"
        )
        result = self._format(
            "身份证号110108200001010001已验证",
            sensitive_patterns=[id_card_pattern],
        )
        assert result == "身份证号******************已验证"

    def test_pattern_id_card_in_node_id_not_matched(self):
        id_card_pattern = (
            r"[1-9]\d{5}(?:19|20)\d{2}"
            r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
            r"\d{3}[0-9Xx]"
        )
        result = self._format(
            "node_110108200001010001",
            sensitive_patterns=[id_card_pattern],
        )
        assert result == "node_110108200001010001"

    def test_pattern_email(self):
        result = self._format(
            "邮箱john@example.com已确认",
            sensitive_patterns=[r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
        )
        assert result == "邮箱****************已确认"
        assert "john@example.com" not in result

    def test_pattern_email_in_url_not_matched(self):
        result = self._format(
            "url_user@example.com_path",
            sensitive_patterns=[r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
        )
        assert result == "url_user@example.com_path"


class TestMaskingEnabledSwitch:
    @staticmethod
    def _format(msg, sensitive_words=None, sensitive_patterns=None):
        formatter = MaskingFormatter(
            fmt="%(message)s",
            sensitive_words=sensitive_words,
            sensitive_patterns=sensitive_patterns,
            truncate_for_console=False,
        )
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return formatter.format(record)

    def test_all_disabled_no_masking(self):
        result = self._format(
            '手机号为13812345678 卡号6123456789012345',
            sensitive_words=None,
            sensitive_patterns=None,
        )
        assert result == '手机号为13812345678 卡号6123456789012345'

    def test_all_enabled_all_masking(self):
        result = self._format(
            '手机号为13812345678 卡号6123456789012345',
            sensitive_words=None,
            sensitive_patterns=[
                r"1[1-9]\d{9}",
                r"\d{16,19}",
            ],
        )
        assert '***********' in result
        assert '****************' in result
        assert '13812345678' not in result
        assert '6123456789012345' not in result
