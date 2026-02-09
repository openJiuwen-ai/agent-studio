openJiuwen Log System is a flexible, extensible log management framework that supports multiple logger implementations and configuration methods. The system adopts a layered architecture that separates core interfaces from specific implementations and provides a unified log management interface. It supports the following features:

* Default logger: Developers can import and use it directly for logging during development.
* Custom logger: Developers can implement loggers to meet their needs, with customizable output configuration, including output format, output destinations, file rotation count, and maximum size per log file.

# Default Logger

The default logger provided by openJiuwen is a light wrapper around Python’s standard logging library. You can directly import the openJiuwen `logger` module to use it. For usage details, refer to Python’s [logging](https://docs.python.org/3.13/library/logging.html#) standard library documentation.

```python
from openjiuwen.core.common.logging import logger

logger.info(f"Record info-level log")
```

Sample output:

```text
2025-09-29 03:04:20 | common | test.py | 3 | <module> |  | INFO | Record info-level log
```

# Custom Logger

openJiuwen provides the `LoggerProtocol` class for implementing custom loggers, and the `LogManager` class to handle registration and usage management of custom loggers, ensuring thread safety.

## Implement a Custom Logger

Developers can implement a custom logger by inheriting the `LoggerProtocol` class. It is recommended to create the logger object `_logger` using the core function `getLogger` from Python’s standard `logging` library and then configure it—for example, set the output format, output destinations (such as console or file), the number of rotated log files, and the maximum size of a single log file.

```python
import sys
import logging
from logging.handlers import RotatingFileHandler

from openjiuwen.core.common.logging.protocol import LoggerProtocol
from openjiuwen.core.common.logging.utils import get_log_max_bytes

class CustomLogger(LoggerProtocol):
    """Custom logger implementation"""

    def __init__(self, log_type: str, config: dict):
        self.log_type = log_type
        self.config = config
        self._logger = logging.getLogger(f"custom_{log_type}")
        self._setup_logger()

    def _setup_logger(self):
        """Configure the logger"""
        # Log level
        level = self.config.get('level', logging.INFO)
        self._logger.setLevel(level)
        
        # Output destinations
        output = self.config.get('output', ['console'])
        log_file = self.config.get('log_file', f'output.log')
        
        # Output format
        formatter = logging.Formatter(
            '%(asctime)s | [CUSTOM] | %(levelname)s | %(message)s'
        )
        
        if 'console' in output:
            stream_handler = logging.StreamHandler(stream=sys.stdout)  
            stream_handler.setFormatter(formatter)
            self._logger.addHandler(stream_handler)
        
        if 'file' in output:
            # Log file rotation count
            backup_count = self.config.get('backup_count', 20)
            # Max size per log file
            max_bytes = get_log_max_bytes(self.config.get('max_bytes', 20 * 1024 * 1024))
        
            file_handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
       

    # Implement all methods from the LoggerProtocol interface
    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        self._logger.log(level, msg, *args, **kwargs)

    def setLevel(self, level: int) -> None:
        self._logger.setLevel(level)

    def addHandler(self, handler: logging.Handler) -> None:
        self._logger.addHandler(handler)

    def removeHandler(self, handler: logging.Handler) -> None:
        self._logger.removeHandler(handler)

    def addFilter(self, filter) -> None:
        self._logger.addFilter(filter)

    def removeFilter(self, filter) -> None:
        self._logger.removeFilter(filter)

    def get_config(self) -> dict:
        return self.config.copy()

    def reconfigure(self, config: dict) -> None:
        self.config = config
        self._setup_logger()
```

## Register the Custom Logger

Use the `register_logger` method of the `LogManager` class to register the custom logger with `LogManager` for easier management.

```python
import logging
from openjiuwen.core.common.logging import LogManager

# Create a custom logger
custom_config = {
    'level': logging.INFO,
    'format': 'custom_format'
}

custom_logger = CustomLogger('my_app', custom_config)

# Register with LogManager
LogManager.register_logger('my_app', custom_logger)
```

## Use the Custom Logger

Use the `get_logger` method of the `LogManager` class to obtain the custom logger instance for use.

```python
from openjiuwen.core.common.logging import LogManager

# Use the custom logger
logger = LogManager.get_logger('my_app')
logger.info("This is a message from the custom logger")
```

Sample output:

```text
2025-09-29 03:07:04,789 | [CUSTOM] | INFO | This is a message from the custom logger
```