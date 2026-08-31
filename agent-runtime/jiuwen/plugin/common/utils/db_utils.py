#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
Plugin Database Utilities
"""

import datetime
import json
from contextlib import contextmanager
from functools import wraps

import psycopg2
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.plugin.common import constant
from jiuwen.plugin.common import exception


@contextmanager
def exception_handler():
    """exception handler"""
    try:
        yield
    except psycopg2.OperationalError as e:
        raise exception.PluginDatabaseException(message=map_pg_error_msg(e.pgcode))
    except psycopg2.Error as e:
        raise exception.PluginExecuteSqlException(message=map_pg_error_msg(e.pgcode))
    except Exception:
        raise exception.PluginCommonException(message="sql error")


def map_pg_error_msg(pg_code: str):
    """get pgsql error message by pgcode"""
    if pg_code in constant.PG_CODE_DICT:
        return constant.PG_CODE_DICT.get(pg_code)
    return pg_code


def do_db_connect(func):
    """database connect"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 在方法执行前执行的代码
        try:
            self.init()
        except Exception as e:
            logger.error("Database connection error.")
            raise exception.PluginCommonException(
                code=StatusCode.PLUGIN_DATABASE_EXCEPTION,
                message=exception.ExceptionsMessage.DatabaseConnectionErrorJson,
            ) from e
        # 调用原始函数
        return func(self, *args, **kwargs)

    return wrapper


def get_current_datetime(
    timezone=constant.TIMEZONE_NAME, format_time="%Y-%m-%d %H:%M:%S"
):
    """get current datetime according to timezone and specified format"""
    return datetime.datetime.now(tz=timezone).strftime(format_time)


def load_json(file_path):
    """read json file"""
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return config_dict
    except Exception as _:
        raise exception.PluginCommonException(
            code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
            message="load json failed",
        )
