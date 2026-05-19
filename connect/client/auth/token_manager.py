"""
Token verification and silent refresh — no platform dependencies.
"""
from typing import Optional, Tuple

import requests as _requests
from openjiuwen.core.common.logging import logger

from .verify_token import verify_token
from .refresh_token import refresh_token as api_refresh_token
from .token_storage import get_user_space_id, set_user_data


def verify_and_refresh(
    client,
    user_id,
    current_refresh_token: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """
    Verify the client's current token.  If it has expired, attempt a silent
    refresh using *current_refresh_token*.

    Returns:
        (success: bool, new_token: str | None)
        - (True,  None)       — token was already valid, no refresh needed
        - (True,  new_token)  — token was refreshed; caller should persist it
        - (False, None)       — token is confirmed expired and refresh also failed
    """
    logger.info('[TOKEN] user=%s — calling verify_token', user_id)
    try:
        result = verify_token(client)
        logger.info('[TOKEN] user=%s — verify_token OK result=%s', user_id, result)
        return True, None
    except _requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        body = ''
        try:
            body = e.response.text[:200] if e.response is not None else ''
        except Exception as e2:
            raise e from e2
        logger.warning('[TOKEN] user=%s — verify_token HTTPError status=%s body=%s', user_id, status, body)
        if status != 401:
            # Non-401 (e.g. 500, 404, or backend temporarily down) — not a
            # token-expiry issue, so don't force logout.
            logger.warning('[TOKEN] user=%s — non-401 HTTP error, treating as valid (optimistic)', user_id)
            return True, None
        # 401 — token is genuinely expired, fall through to refresh attempt
        logger.info('[TOKEN] user=%s — got 401, token expired, attempting refresh', user_id)
    except Exception as e:
        # Network error, timeout, SSL, etc. — cannot confirm expiry, proceed optimistically.
        logger.warning('[TOKEN] user=%s — verify_token raised %s: %s — treating as valid (optimistic)', user_id,
                       type(e).__name__, e)
        return True, None

    logger.info('[TOKEN] user=%s — refresh_token_present=%s', user_id, bool(current_refresh_token))
    if not current_refresh_token:
        logger.error('[TOKEN] user=%s — 401 and no refresh token → returning False', user_id)
        return False, None

    try:
        result = api_refresh_token(client, current_refresh_token)
        new_token: Optional[str] = (
            result.get('access_token') or
            result.get('data', {}).get('access_token') or
            result.get('data', {}).get('token')
        )
        logger.info('[TOKEN] user=%s — refresh result keys=%s new_token_present=%s', user_id, list(result.keys())
        if isinstance(result, dict) else type(result).__name__, bool(new_token))
        if new_token:
            client.set_token(new_token)
            set_user_data(user_id, new_token, get_user_space_id(user_id), current_refresh_token)
            return True, new_token
    except Exception as e:
        logger.warning('[TOKEN] user=%s — refresh request raised %s: %s', user_id, type(e).__name__, e)

    logger.error('[TOKEN] user=%s — refresh failed → returning False', user_id)
    return False, None
