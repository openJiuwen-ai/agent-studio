# coding=utf-8
"""
CheckInfo: local replacement for jiuwen.prompt.common.check.CheckInfo.

Provides input parameter validation utilities used by pydantic field validators
and API request validation.
"""


class ParamCheckFailedException(ValueError):
    """Exception raised when parameter validation fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CheckInfo:
    """Utility class for validating input parameters."""

    @staticmethod
    def check_str_content(value, field_name):
        """check str content"""
        if not isinstance(value, str):
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! "
                f"value type not correct, expected string"
            )
        if not value:
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! value is empty"
            )
        return value

    @staticmethod
    def check_dict_content(value, field_name):
        """check dict content"""
        if not isinstance(value, dict):
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! "
                f"value type not correct, expected dict"
            )
        if not value:
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! value is empty"
            )
        return value

    @staticmethod
    def check_list_content(value, field_name):
        """check list content"""
        if not isinstance(value, list):
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! "
                f"value type not correct, expected list"
            )
        if not value:
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! value is empty"
            )
        return value

    @staticmethod
    def check_message_list_content(value, field_name):
        """check message list content"""
        if not isinstance(value, list):
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! "
                f"value type not correct, expected list"
            )
        if not value:
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! value is empty"
            )
        if value[-1].get("role", "") != "assistant":
            raise ParamCheckFailedException(
                f"the role of 'assistant' is not in the {field_name} field"
            )
        return value

    @staticmethod
    def check_int_content(value, field_name):
        """check int content"""
        if not isinstance(value, int):
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! "
                f"value type not correct, expected int"
            )
        if not value:
            raise ParamCheckFailedException(
                f"input value field name: {field_name} check failed! value is empty"
            )
        return value
