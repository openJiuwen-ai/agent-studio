"""统一日志配置测试：单一全局级别 + 仅 console 输出。

进程内只有 common.log 一个日志文件——console handler 写 stdout，由启动脚本重定向
进 ``${LOGGING_LOG_PATH}/common.log``。因此配置里既不应有 per-namespace 的文件
输出，也不应有 per-namespace 的级别覆盖。
"""

from agent_runtime.serve.server import _build_log_config


def test_build_log_config_uses_given_level():
    cfg = _build_log_config("DEBUG")
    assert cfg["level"] == "DEBUG"
    assert cfg["backend"] == "default"


def test_build_log_config_outputs_console_only():
    """三个输出位都只留 console，保证不产生任何额外日志文件。"""
    cfg = _build_log_config("INFO")
    assert cfg["output"] == ["console"]
    assert cfg["interface_output"] == ["console"]
    assert cfg["performance_output"] == ["console"]


def test_build_log_config_has_no_logger_overrides():
    """统一级别下不再下发 loggers.*.level，避免命名空间级别与 LOG_LEVEL 分叉。"""
    cfg = _build_log_config("INFO")
    assert "loggers" not in cfg
