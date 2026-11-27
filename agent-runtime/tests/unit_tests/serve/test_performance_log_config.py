"""PERFORMANCE_LOG_LEVEL 接线测试：settings 级别 → configure_log_config 注入。"""

from agent_runtime.serve.server import _build_log_config


def test_build_log_config_injects_info_to_performance():
    """PERFORMANCE_LOG_LEVEL=INFO 时 performance 日志器级别应为 INFO。"""
    cfg = _build_log_config("WARNING", "WARNING", "WARNING", "INFO")
    assert cfg["loggers"]["performance"] == {"level": "INFO"}


def test_build_log_config_default_warning_keeps_silent():
    """默认 WARNING 时 performance 日志器级别应为 WARNING（perf 静默）。"""
    cfg = _build_log_config("WARNING", "WARNING", "WARNING", "WARNING")
    assert cfg["loggers"]["performance"] == {"level": "WARNING"}


def test_build_log_config_preserves_levels_by_logger():
    """workflow/graph/llm/sys_operation 级别按参数逐项透传，互不串扰。"""
    cfg = _build_log_config("DEBUG", "INFO", "WARNING", "INFO")
    assert cfg["loggers"]["workflow"] == {"level": "DEBUG"}
    assert cfg["loggers"]["graph"] == {"level": "INFO"}
    assert cfg["loggers"]["llm"] == {"level": "WARNING"}
    assert cfg["loggers"]["sys_operation"] == {"level": "WARNING"}
    assert cfg["level"] == "INFO"
    assert cfg["backend"] == "default"