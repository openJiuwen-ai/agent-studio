# openjiuwen.core.utils.config.user_config

## class openjiuwen.core.utils.config.user_config.UserConfig

Reads a user's INI-style configuration file (e.g., config.ini). Currently supports configuring whether to log privacy-sensitive data and specifying a blacklist of unsafe paths.

### classmethod set_config_path

```python
set_config_path(path: Path)
```

Specify the path to the user's INI-style configuration file. Currently, it is used only for the following settings:

* Whether to log privacy-sensitive data.
* Specify unsafe paths. If the logging configuration file path resides under an unsafe path, validation fails and an exception is thrown.

Note: This method must be called at the very start of the program to take effect, and the configuration file should be under the same root directory as the script being executed.

**Parameters**:

*** path** (Path): The file path to the INI-format configuration file. The path must not be sensitive (e.g., /etc/passwd, /etc/shadow, /etc/hosts, /etc/hostname).

**Exceptions**:

* **JiuWenBaseException**: The base exception class for openJiuwen. For details and troubleshooting, see [StatusCode](../../common/exception/status_code.md).

**Example**:

```python
>>> # Before running business logic, specify via the config file whether to log entries containing privacy-sensitive data
>>> # If not configured, logging privacy-sensitive data is disabled by default
>>> config_path = Path("./config.ini")
>>> UserConfig.set_config_path(config_path)
```