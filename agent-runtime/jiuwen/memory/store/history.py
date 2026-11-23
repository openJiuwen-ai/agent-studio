#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""conversation memory, store in gaussdb-vector"""

import datetime
import json
import os
from abc import ABC
from typing import Dict

from jiuwen.common.configs.env_constants import DATASOURCE_REDIS_TTL_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.store.redis import get_redis_instance
from jiuwen.memory.store.base import BaseConversationMemory

EXPIRATION_TIME = 3 * 24 * 60 * 60

BJ_TZ = datetime.timezone(
    datetime.timedelta(hours=8),
    name="Asia/Beijing",
)


class HistoryInRedisConversation(BaseConversationMemory, ABC):
    """
    history conversation memory in redis
    """

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.redis_db = get_redis_instance()

    def add(self, inputs: object, outputs: object) -> bool:
        """
        Add a k-v pair to the store
        """
        user_input = {
            "role": "user",
            "content": inputs,
            "timestamp": datetime.datetime.now(tz=BJ_TZ).isoformat(),
        }
        assistant_output = {
            "role": "assistant",
            "content": outputs,
            "timestamp": datetime.datetime.now(tz=BJ_TZ).isoformat(),
        }
        ttl = int(os.getenv(DATASOURCE_REDIS_TTL_KEY, EXPIRATION_TIME))
        self.redis_db.list_append(
            self.conversation_id, json.dumps(user_input, ensure_ascii=False), ttl=ttl
        )
        self.redis_db.list_append(
            self.conversation_id,
            json.dumps(assistant_output, ensure_ascii=False),
            ttl=ttl,
        )
        return True

    def get_all(self) -> Dict[object, object]:
        """
        Get all items in the store.

        Returns:
            Dict[object, object]: all items in the store.
        """
        data = self.redis_db.list_get(self.conversation_id)
        if data:
            return {self.conversation_id: data}
        return {}

    def get_nearest_k(self, k: int) -> Dict[object, object]:
        """
        Get the nearest k items in the store.

        Returns:
            Cache: all items in cache.
        """
        if k <= 0:
            return {}

            # Gets the current length of the list
        length = self.redis_db.list_length(self.conversation_id)

        # If the number of requested elements is greater than the list length, k is adjusted to the list length.
        if k > length:
            k = length

        # Calculate the start index. The Redis index starts from 0. Therefore, the Redis index needs to be
        # decremented by 1.
        start = length - k

        # The end index of LRANGE is inclusive, so use -1 to indicate the last element of the list.
        return self.redis_db.list_get(self.conversation_id, start, -1)

    def get(self, key: object) -> object:
        """
        Get the value of given key.

        Returns:
            object: item of given key in the store
        """
        raise JiuWenBaseException(
            StatusCode.FUNCTION_RESERVED_ERROR.code,
            StatusCode.FUNCTION_RESERVED_ERROR.errmsg,
        )

    def contains(self, key: object) -> bool:
        """
        Get all items in the store.

        Returns:
            bool: whether the key is in the store.
        """
        raise JiuWenBaseException(
            StatusCode.FUNCTION_RESERVED_ERROR.code,
            StatusCode.FUNCTION_RESERVED_ERROR.errmsg,
        )

    def on_delete(self) -> int:
        """
        Delete expired keys and return number of entries deleted.

        Returns:
            int: Number of entries deleted.
        """
        raise JiuWenBaseException(
            StatusCode.FUNCTION_RESERVED_ERROR.code,
            StatusCode.FUNCTION_RESERVED_ERROR.errmsg,
        )

    def delete(self, key: object) -> bool:
        """
        Delete key and return number of entries deleted (``1`` or ``0``).

        Args:
            key: Cache key to delete.

        Returns:
            int: True if key was deleted, False if key didn't exist.
        """
        raise JiuWenBaseException(
            StatusCode.FUNCTION_RESERVED_ERROR.code,
            StatusCode.FUNCTION_RESERVED_ERROR.errmsg,
        )

    def memorize(self, ttl: int, typed=False):
        raise JiuWenBaseException(
            StatusCode.FUNCTION_RESERVED_ERROR.code,
            StatusCode.FUNCTION_RESERVED_ERROR.errmsg,
        )
