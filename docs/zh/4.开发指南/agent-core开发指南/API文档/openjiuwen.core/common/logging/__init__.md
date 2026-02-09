# openjiuwen.core.common.logging

## openjiuwen.core.common.logging.logger

openJiuwen提供的默认日志器是对Python logging标准库的一层封装，具体使用方式可参考Python的[logging](https://docs.python.org/3.13/library/logging.html#)标准库文档。

**样例**：

```python
>>> import logging
>>> 
>>> from openjiuwen.core.common.logging import logger
>>> logger.set_level(logging.DEBUG)
>>> 
>>> logger.debug(f"记录调试级别日志")
2025-09-29 03:04:20 | common | default_impl.py | 172 | info |  | DEBUG | 记录信息级别日志

>>> logger.info(f"记录信息级别日志")
2025-09-29 03:04:20 | common | default_impl.py | 172 | info |  | INFO | 记录信息级别日志

>>> logger.warning(f"记录警告级别日志")
2025-09-29 03:04:20 | common | default_impl.py | 176 | warning |  | WARNING | 记录警告级别日志

>>> logger.error(f"记录错误级别日志")
2025-09-29 03:04:20 | common | default_impl.py | 180 | error |  | ERROR | 记录错误级别日志

>>> logger.critical(f"记录严重级别日志")
2025-09-29 03:04:20 | common | default_impl.py | 184 | critical |  | CRITICAL | 记录严重级别日志
```
