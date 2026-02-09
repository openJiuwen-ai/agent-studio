# openjiuwen.core.utils.config.user_config

## class openjiuwen.core.utils.config.user_config.UserConfig

读取用户的`ini`格式的配置文件，例如`config.ini`，当前支持配置是否打印隐私敏感数据的日志、以及指定非安全路径的黑名单。

### classmethod set_config_path

```python
set_config_path(path: Path)
```

指定用户的`ini`格式的配置文件的路径，当前仅用于配置以下内容：

* 是否打印隐私敏感数据的日志。
* 指定非安全的路径，如果日志配置文件的路径在非安全路径下，则校验失败，将抛出异常。

注意：该方法必须在程序最开始的位置执行，才能生效；并且配置文件应当与执行脚本属于同个根目录下。

**参数**：

* **path**(Path)：表示`ini`格式的配置文件的文件路径，路径不得为敏感路径，例如`/etc/passwd`、`/etc/shadow`、`/etc/hosts`、`/etc/hostname`。

**异常**：

* **JiuWenBaseException**：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../../common/exception/status_code.md)。

**样例**：

```python
>>> # 在执行业务逻辑前，通过配置文件指定是否打印包含隐私敏感数据的日志
>>> # 如果不配置，则默认不打印包含隐私敏感数据的日志
>>> config_path = Path("./config.ini")
>>> UserConfig.set_config_path(config_path)
```
