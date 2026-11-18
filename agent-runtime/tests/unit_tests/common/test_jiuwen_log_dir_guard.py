"""legacy jiuwen logger 的日志目录预建行为。

默认配置下三个输出通道都是 console，日志只走 stdout（由启动脚本重定向进
common.log），因此不应在进程工作目录里凭空留下空的 logs/ 目录。
"""

from jiuwen.common.log.base import _ensure_log_dir


def _log_path(tmp_path):
    """与 jiuwen/config.yaml 同形：log_path 带结尾斜杠。"""
    return str(tmp_path / "logs") + "/"


def test_no_dir_when_all_outputs_console(tmp_path):
    _ensure_log_dir(
        {
            "output": "console",
            "interface_output": "console",
            "performance_output": "console",
        },
        _log_path(tmp_path),
    )
    assert not (tmp_path / "logs").exists()


def test_dir_created_when_common_output_writes_file(tmp_path):
    _ensure_log_dir({"output": "console,log"}, _log_path(tmp_path))
    assert (tmp_path / "logs").is_dir()


def test_dir_created_when_interface_output_writes_file(tmp_path):
    _ensure_log_dir({"interface_output": "log"}, _log_path(tmp_path))
    assert (tmp_path / "logs").is_dir()


def test_missing_outputs_default_to_console(tmp_path):
    """配置里没有 output 键（或值为 null）时按 console 处理，不建目录。"""
    _ensure_log_dir({"output": None}, _log_path(tmp_path))
    assert not (tmp_path / "logs").exists()
