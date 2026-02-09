# openjiuwen.core.common.logging.protocol

## class openjiuwen.core.common.logging.protocol.LoggerProtocol

```python
LoggerProtocol(Protocol)
```

开发者继承`LoggerProtocol`类，可实现自定义日志器。

### get_config()

```python
get_config() -> Dict[str, Any]
```

获取日志配置信息。

**返回**：

**Dict[str,  Any]**：日志配置信息。

**样例**：

```python
>>> 
>>> from openjiuwen.core.common.logging.protocol import LoggerProtocol
>>> import logging
>>> 
>>> class CustomLogger(LoggerProtocol):
...     """自定义日志器实现"""
... 
...     def __init__(self, log_type: str, config: dict):
...         '''自定义日志器初始化'''
...         self.log_type = log_type
...         self.config = config
...         self._logger = logging.getLogger(f"custom_{log_type}")
...         self._setup_logger()
... 
...     def _setup_logger(self):
...         '''自定义日志器设置'''
...         level = self.config.get('level', logging.INFO)
...         self._logger.setLevel(level)
... 
...         # 添加自定义格式
...         formatter = logging.Formatter(
...             '%(asctime)s | [CUSTOM] | %(levelname)s | %(message)s'
...         )
... 
...         handler = logging.StreamHandler()
...         handler.setFormatter(formatter)
...         self._logger.addHandler(handler)
... 
...     # 实现 LoggerProtocol 接口的所有方法
...     def get_config(self) -> dict:
...         """获取日志配置"""
...         return self.config.copy()
... 
>>> from openjiuwen.core.common.logging import LogManager
>>> 
>>> # 创建自定义日志器
>>> custom_config = {
...     'level': logging.INFO,
...     'format': 'custom_format'
... }
... 
>>> custom_logger = CustomLogger('my_app', custom_config)
>>> 
>>> # 注册到 LogManager
>>> LogManager.register_logger('my_app', custom_logger)
>>> 
>>> # 使用日志器
>>> logger = LogManager.get_logger('my_app')
>>> print(logger.get_config())
{"level": 20, "format": "custom_format"}
```

### reconfigure

```
reconfigure(config: Dict[str, Any]) -> None
```

重新设置日志配置信息。

**参数**：

**config**(Dict[str, Any])：日志配置信息。

**样例**：

```python
>>> from openjiuwen.core.common.logging.protocol import LoggerProtocol
>>> import logging
>>> 
>>> class CustomLogger(LoggerProtocol):
...     """自定义日志器实现"""
... 
...     def __init__(self, log_type: str, config: dict):
...         '''自定义日志器初始化'''
...         self.log_type = log_type
...         self.config = config
...         self._logger = logging.getLogger(f"custom_{log_type}")
...         self._setup_logger()
... 
...     def _setup_logger(self):
...         '''自定义日志器设置'''
...         level = self.config.get('level', logging.INFO)
...         self._logger.setLevel(level)
... 
...         # 添加自定义格式
...         formatter = logging.Formatter(
...             '%(asctime)s | [CUSTOM] | %(levelname)s | %(message)s'
...         )
... 
...         handler = logging.StreamHandler()
...         handler.setFormatter(formatter)
...         self._logger.addHandler(handler)
... 
...     # 实现 LoggerProtocol 接口的所有方法
...     def get_config(self) -> dict:
...         """获取日志配置"""
...         return self.config.copy()
... 
...     def reconfigure(self, config: dict) -> None:
...         """重新配置日志记录器"""
...         self.config = config
...         self._setup_logger()
... 
>>> from openjiuwen.core.common.logging import LogManager
>>> 
>>> # 创建自定义日志器
>>> custom_config = {
...     'level': logging.INFO,
...     'format': 'custom_format'
... }
... 
>>> custom_logger = CustomLogger('my_app', custom_config)
>>> 
>>> # 新的配置
>>> new_custom_config = {
...     'level': logging.DEBUG,
...     'format': 'new_custom_format'
... }
... 
>>> # 注册到 LogManager
>>> LogManager.register_logger('my_app', custom_logger)
>>> 
>>> # 使用日志器
>>> logger = LogManager.get_logger('my_app')
>>> logger.reconfigure(new_custom_config)
>>> print(logger.get_config())
{"level": 10, "format": "new_custom_format"}
```
