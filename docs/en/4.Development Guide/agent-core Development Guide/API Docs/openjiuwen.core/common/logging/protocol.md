# openjiuwen.core.common.logging.protocol

## class openjiuwen.core.common.logging.protocol.LoggerProtocol

```python
LoggerProtocol(Protocol)
```

Developers can implement custom loggers by inheriting from the `LoggerProtocol` class.

### get_config()

```python
get_config() -> Dict[str, Any]
```

Retrieves the logger configuration.

**Returns**:

* **Dict[str, Any]**: Logger configuration information.

**Example**:

```python
>>> 
>>> from openjiuwen.core.common.logging.protocol import LoggerProtocol
>>> import logging
>>> 
>>> class CustomLogger(LoggerProtocol):
...     """Custom logger implementation"""
... 
...     def __init__(self, log_type: str, config: dict):
...         '''Custom logger initialisation'''
...         self.log_type = log_type
...         self.config = config
...         self._logger = logging.getLogger(f"custom_{log_type}")
...         self._setup_logger()
... 
...     def _setup_logger(self):
...         '''Custom logger setup'''
...         level = self.config.get('level', logging.INFO)
...         self._logger.setLevel(level)
... 
...         # Add a custom format
...         formatter = logging.Formatter(
...             '%(asctime)s | [CUSTOM] | %(levelname)s | %(message)s'
...         )
... 
...         handler = logging.StreamHandler()
...         handler.setFormatter(formatter)
...         self._logger.addHandler(handler)
... 
...     # Implement all methods required by LoggerProtocol
...     def get_config(self) -> dict:
...         """Get logger configuration"""
...         return self.config.copy()
... 
>>> from openjiuwen.core.common.logging import LogManager
>>> 
>>> # Create a custom logger
>>> custom_config = {
...     'level': logging.INFO,
...     'format': 'custom_format'
... }
... 
>>> custom_logger = CustomLogger('my_app', custom_config)
>>> 
>>> # Register with LogManager
>>> LogManager.register_logger('my_app', custom_logger)
>>> 
>>> # Use the logger
>>> logger = LogManager.get_logger('my_app')
>>> print(logger.get_config())
{"level": 20, "format": "custom_format"}
```

### reconfigure

```python
reconfigure(config: Dict[str, Any]) -> None
```

Reconfigures the logger.

**Parameters**:

* **config** (Dict[str, Any]): Logger configuration.

**Example**:

```python
>>> from openjiuwen.core.common.logging.protocol import LoggerProtocol
>>> import logging
>>> 
>>> class CustomLogger(LoggerProtocol):
...     """Custom logger implementation"""
... 
...     def __init__(self, log_type: str, config: dict):
...         '''Custom logger initialisation'''
...         self.log_type = log_type
...         self.config = config
...         self._logger = logging.getLogger(f"custom_{log_type}")
...         self._setup_logger()
... 
...     def _setup_logger(self):
...         '''Custom logger setup'''
...         level = self.config.get('level', logging.INFO)
...         self._logger.setLevel(level)
... 
...         # Add a custom format
...         formatter = logging.Formatter(
...             '%(asctime)s | [CUSTOM] | %(levelname)s | %(message)s'
...         )
... 
...         handler = logging.StreamHandler()
...         handler.setFormatter(formatter)
...         self._logger.addHandler(handler)
... 
...     # Implement all methods required by LoggerProtocol
...     def get_config(self) -> dict:
...         """Get logger configuration"""
...         return self.config.copy()
... 
...     def reconfigure(self, config: dict) -> None:
...         """Reconfigure the logger"""
...         self.config = config
...         self._setup_logger()
... 
>>> from openjiuwen.core.common.logging import LogManager
>>> 
>>> # Create a custom logger
>>> custom_config = {
...     'level': logging.INFO,
...     'format': 'custom_format'
... }
... 
>>> custom_logger = CustomLogger('my_app', custom_config)
>>> 
>>> # New configuration
>>> new_custom_config = {
...     'level': logging.DEBUG,
...     'format': 'new_custom_format'
... }
... 
>>> # Register with LogManager
>>> LogManager.register_logger('my_app', custom_logger)
>>> 
>>> # Use the logger
>>> logger = LogManager.get_logger('my_app')
>>> logger.reconfigure(new_custom_config)
>>> print(logger.get_config())
{"level": 10, "format": "new_custom_format"}
```
