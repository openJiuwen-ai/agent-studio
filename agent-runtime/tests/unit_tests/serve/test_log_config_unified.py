"""统一日志配置测试：单一全局级别 + 仅 console 输出。

进程内只有 common.log 一个日志文件——console handler 写 stdout，由启动脚本重定向
进 ``${LOGGING_LOG_PATH}/common.log``。因此配置里既不应有 per-namespace 的文件
输出，也不应有 per-namespace 的级别覆盖。
"""

from unittest.mock import patch

from agent_runtime.serve.server import (
    _DEPRECATED_LOG_ENV_VARS,
    _build_log_config,
    _warn_deprecated_log_env_vars,
)


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


def test_warn_deprecated_env_vars_reports_configured_ones(monkeypatch):
    from agent_runtime.serve import server

    monkeypatch.setenv("WORKFLOW_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PERFORMANCE_LOG_LEVEL", "INFO")
    monkeypatch.delenv("GRAPH_LOG_LEVEL", raising=False)
    monkeypatch.delenv("LLM_LOG_LEVEL", raising=False)

    with patch.object(server, "logger") as mock_logger:
        _warn_deprecated_log_env_vars()

    mock_logger.warning.assert_called_once()
    reported = mock_logger.warning.call_args[0][1]
    assert "WORKFLOW_LOG_LEVEL" in reported
    assert "PERFORMANCE_LOG_LEVEL" in reported
    assert "GRAPH_LOG_LEVEL" not in reported


def test_warn_deprecated_env_vars_silent_when_unset(monkeypatch):
    from agent_runtime.serve import server

    for name in _DEPRECATED_LOG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # 空字符串在部署模板里等同于未配置，同样不该告警
    monkeypatch.setenv("LLM_LOG_LEVEL", "")

    with patch.object(server, "logger") as mock_logger:
        _warn_deprecated_log_env_vars()

    mock_logger.warning.assert_not_called()
