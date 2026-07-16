#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""abstract plan and conversation memory"""

from abc import ABC
from typing import List


class BaseConversationMemory(ABC):
    """abstract conversation memory"""

    def add(self, key: object, value: object) -> bool:
        """
        Add a k-v pair to the store
        """
        pass

    def get(self, key: object) -> object:
        """
        Get the value of given key.

        Returns:
            object: item of given key in the store
        """
        pass

    def get_nearest_k(self, key: object, k: int) -> List[object]:
        """
        Get the nearest k items in the value of given key.

        Returns:
            List[object]: k items in the value of given key.
        """
        pass

    def get_all(self, key: object) -> List[object]:
        """
        Get all the items in the value of given key.

        Returns:
            List[object]: all the items in the value of given key.
        """
        pass

    def contains(self, key: object) -> bool:
        """
        Determine whether the key exists.

        Returns:
            bool: whether the key is in the store.
        """
        pass

    def delete(self, key: object) -> bool:
        """
        Delete key and return number of entries deleted (``True`` or ``False``).

        Args:
            key: Cache key to delete.

        Returns:
            bool: True if key was deleted, False if key didn't exist.
        """
        pass
