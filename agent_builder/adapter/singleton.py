# coding=utf-8
"""
Singleton metaclass: local replacement for jiuwen.common.utils.singleton.Singleton.

Ensures that only one instance of a class exists per process.
"""


class Singleton(type):
    """
    Thread-safe Singleton metaclass.

    Usage:
        class MyClass(metaclass=Singleton):
            pass
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def _reset(mcs, cls=None):
        """Reset singleton instance(s). Useful for testing."""
        if cls is not None:
            mcs._instances.pop(cls, None)
        else:
            mcs._instances.clear()
