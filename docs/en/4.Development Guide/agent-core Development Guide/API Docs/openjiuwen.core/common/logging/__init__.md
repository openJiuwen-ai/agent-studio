# openjiuwen.core.common.logging

## openjiuwen.core.common.logging.logger

The default logger provided by openJiuwen is a thin wrapper around Python’s standard `logging` library. For detailed usage, refer to Python’s `logging` documentation: https://docs.python.org/3.13/library/logging.html

**Example**:

```python
>>> import logging
>>> 
>>> from openjiuwen.core.common.logging import logger
>>> logger.set_level(logging.DEBUG)
>>> 
>>> logger.debug(f"Log a DEBUG-level message")
2025-09-29 03:04:20 | common | default_impl.py | 172 | info |  | DEBUG | Log an INFO-level message

>>> logger.info(f"Log an INFO-level message")
2025-09-29 03:04:20 | common | default_impl.py | 172 | info |  | INFO | Log an INFO-level message

>>> logger.warning(f"Log a WARNING-level message")
2025-09-29 03:04:20 | common | default_impl.py | 176 | warning |  | WARNING | Log a WARNING-level message

>>> logger.error(f"Log an ERROR-level message")
2025-09-29 03:04:20 | common | default_impl.py | 180 | error |  | ERROR | Log an ERROR-level message

>>> logger.critical(f"Log a CRITICAL-level message")
2025-09-29 03:04:20 | common | default_impl.py | 184 | critical |  | CRITICAL | Log a CRITICAL-level message
```