#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
Authorization module
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable
from zoneinfo import ZoneInfo

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.security.sts_service import decrypt_sensitive_config
from flask import g, request
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.common.logging.base import logger

DEFAULT_PROJECT_ID = "0"
DEFAULT_DOMAIN_ID = "0"

X_TS_KEY = "X-Ts"
X_SIGN_KEY = "X-Sign"
X_AK_KEY = "X-Ak"


class Auth:
    """
    An authorization class for providing decorators for the RESTful API authorization.
    """

    @staticmethod
    def authenticate(func: Callable):
        """Decorator of restful api for authorization."""

        @wraps(func)
        def decorator(*args, **kwargs):
            g.domain_id = DEFAULT_DOMAIN_ID
            g.project_id = DEFAULT_PROJECT_ID
            if (
                os.getenv("SERVICE_TYPE", "xiaoyi") == "xiaoyi"
                and os.getenv("STS_API_AUTH_ENABLE") == "true"
            ):
                if not is_valide_sign():
                    raise JiuWenBaseException(
                        error_code=StatusCode.AUTHENTICATION_ERROR.code,
                        message=StatusCode.AUTHENTICATION_ERROR.errmsg,
                    )
            return func(*args, **kwargs)

        return decorator


def is_valid_ts(ts: str) -> bool:
    """is valide timestamp
    Args:
        ts: Timestamp in seconds, represented as an integer string.
    return:
        Check if the time is within 5 minutes before or after the current time.
    """
    if not ts.isdigit() or len(ts) < 10:
        return False
    ts = ts[:10] if len(ts) > 10 else ts
    now = datetime.now(ZoneInfo("UTC"))
    ts_dt = datetime.fromtimestamp(int(ts), ZoneInfo("UTC"))
    time_difference = abs(now - ts_dt)
    return time_difference <= timedelta(minutes=5)


def get_sign_from_sk(string_to_sign: str) -> str:
    """get signature from string to sign"""
    origin_sk = os.environ.get("STS_SK")
    if not origin_sk:
        raise JiuWenBaseException(
            error_code=StatusCode.AUTHENTICATION_ERROR.code,
            message=StatusCode.AUTHENTICATION_ERROR.errmsg,
        )
    origin_sk = decrypt_sensitive_config(origin_sk)
    hmac_signature = hmac.new(
        origin_sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    )
    signature = base64.b64encode(hmac_signature.digest()).decode("utf-8")
    return signature


def prepare_auth_params() -> tuple:
    """prepare auth parameters from request headers"""
    ts = request.headers.get(X_TS_KEY, "")
    sign = request.headers.get(X_SIGN_KEY, "")
    ak = request.headers.get(X_AK_KEY, "")
    if not ts or not sign or not ak:
        raise JiuWenBaseException(
            error_code=StatusCode.AUTHENTICATION_ERROR.code,
            message=StatusCode.AUTHENTICATION_ERROR.errmsg,
        )
    return ts, ak, sign


def is_valide_sign() -> bool:
    """is valide sign"""
    ts, ak, sign = prepare_auth_params()
    string_to_sign = f"{ak}_{ts}"
    if not is_valid_ts(ts):
        logger.error("Check request timestamp error with request ts.")
        return False

    try:
        signd = get_sign_from_sk(string_to_sign)
    except JiuWenBaseException as e:
        logger.error(f"Check request signature error: {e.error_code}")
        return False
    if sign != signd:
        logger.error("Check request signature error")
        return False
    return True
