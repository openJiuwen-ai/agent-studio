# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access
"""SYNC-01 P3.3 Builder 入口/线程测试。

覆盖 COM-05/DEF-05/DEF-07 关键机制（adapt sync_01）：
- request_context_bridge: get_request_id 空槽/取值 + ContextSource
- inbound_context: select_ids(valid/missing/invalid) + valid_inbound_id
  + apply_platform_headers(不含 X-Execution-Id) + write_x_request_id
- concurrency: submit_with_log_vars 传播 trace_id + 恢复 worker + submit_with_contextvars
- log_init(DEF-05 adapt): request_id factory 幂等 + 注入空槽/上下文值
- server_fastapi(COM-05): X-Request-Id 回写(success/missing header) + select_ids + 异常收口 500

adapt：error 收口断言裸 internal_error 格式（COM-03 延 S3）；uuid 用 .hex（32 位）。
"""

import logging
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from agent_builder.adapter.logger_bridge import (
    get_session_id,
    reset_session_id,
    set_session_id,
)
from agent_builder.adapter.request_context_bridge import (
    ContextSource,
    RequestContext,
    _request_ctx,
    get_request_id,
)
from agent_builder.serve.common.concurrency import (
    submit_with_contextvars,
    submit_with_log_vars,
)
from agent_builder.serve.common.inbound_context import (
    apply_platform_headers,
    select_ids,
    valid_inbound_id,
    write_x_request_id,
)
from agent_builder.serve.common.logger.log_init import init_logger

# ─── request_context_bridge ───


class TestRequestContextBridge(unittest.TestCase):
    def test_request_id_defaults_empty_when_unset(self):
        self.assertEqual(get_request_id(), "")

    def test_request_id_slot_holds_and_returns_set_value(self):
        token = _request_ctx.set(RequestContext(request_id="req-1"))
        try:
            self.assertEqual(get_request_id(), "req-1")
        finally:
            _request_ctx.reset(token)

    def test_default_source_is_none(self):
        self.assertEqual(RequestContext().source, ContextSource.NONE)


# ─── inbound_context ───


class TestValidInboundId(unittest.TestCase):
    def test_valid_lengths(self):
        self.assertTrue(valid_inbound_id("a"))
        self.assertTrue(valid_inbound_id("a" * 64))

    def test_invalid_over_64(self):
        self.assertFalse(valid_inbound_id("a" * 65))

    def test_invalid_empty_and_chars(self):
        for bad in (None, "", "abc def", "abc/def", "abc#def", "abc\tdef"):
            self.assertFalse(valid_inbound_id(bad), f"{bad!r} 应非法")


class TestSelectIds(unittest.TestCase):
    def test_both_valid_used_as_is(self):
        rid, tid, ir, it = select_ids({"x-request-id": "r1", "traceid": "t1"})
        self.assertEqual((rid, tid, ir, it), ("r1", "t1", False, False))

    def test_missing_generates_hex_and_trace_falls_back(self):
        rid, tid, ir, it = select_ids({})
        self.assertTrue(rid)
        self.assertEqual(tid, rid)  # trace 回退 request
        self.assertEqual((ir, it), (False, False))

    def test_invalid_request_regenerates_and_marks_illegal(self):
        rid, tid, ir, it = select_ids({"x-request-id": "x" * 65})
        self.assertNotEqual(rid, "x" * 65)
        self.assertTrue(rid)
        self.assertTrue(ir)

    def test_invalid_trace_falls_back_to_request(self):
        rid, tid, ir, it = select_ids({"x-request-id": "r1", "traceid": "bad val"})
        self.assertEqual(tid, rid)
        self.assertTrue(it)


class TestApplyPlatformHeaders(unittest.TestCase):
    def test_excludes_execution_header(self):
        """Builder 契约：不收 X-Execution-Id。"""
        ctx = RequestContext()
        apply_platform_headers(
            ctx,
            {"X-Workspace-Id": "ws1", "x-execution-id": "should-not-enter", "x-language": "en"},
        )
        self.assertEqual(ctx.headers["X-Workspace-Id"], "ws1")
        self.assertNotIn("X-Execution-Id", ctx.headers)
        self.assertEqual(ctx.headers["x-language"], "en")

    def test_language_falls_back_to_accept_language_then_default(self):
        ctx = RequestContext()
        apply_platform_headers(ctx, {"accept-language": "zh-TW"})
        self.assertEqual(ctx.headers["x-language"], "zh-TW")
        ctx2 = RequestContext()
        apply_platform_headers(ctx2, {})
        self.assertEqual(ctx2.headers["x-language"], "zh-cn")


class TestWriteXRequestId(unittest.TestCase):
    def test_write_sets_header(self):
        resp = JSONResponse(content={}, status_code=200)
        write_x_request_id(resp, "rid-1")
        self.assertEqual(resp.headers["X-Request-Id"], "rid-1")


# ─── concurrency (DEF-07) ───


class TestSubmitWithLogVars(unittest.TestCase):
    """submit_with_log_vars：传播 trace_id + bridge，工作线程结束恢复。"""

    def test_propagates_trace_id_and_request_bridge(self):
        from concurrent.futures import ThreadPoolExecutor

        outer_trace = set_session_id("outer-trace")
        outer_bridge = _request_ctx.set(RequestContext(request_id="outer-req"))
        try:
            results = {}

            def worker():
                results["trace"] = get_session_id()
                results["req"] = get_request_id()
                return "ok"

            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = submit_with_log_vars(ex, worker)
                self.assertEqual(fut.result(), "ok")
            # 子线程持请求快照
            self.assertEqual(results["trace"], "outer-trace")
            self.assertEqual(results["req"], "outer-req")
        finally:
            _request_ctx.reset(outer_bridge)
            reset_session_id(outer_trace)

    def test_worker_state_restored_after_task_reuse(self):
        """同一 worker 线程任务结束后恢复进入前状态（worker 内断言，审视 §2.1）。

        不能只查父线程：在同一 worker（max_workers=1）先跑一个 log_vars 任务，
        再裸 submit 探针——任务期间持传播值，结束后（探针进入时）应为默认
        sentinel，证明线程复用无残留。
        """
        from concurrent.futures import ThreadPoolExecutor

        outer_trace = set_session_id("outer-trace")
        try:
            observed = []

            def task():
                observed.append(("during", get_session_id()))

            def probe():
                observed.append(("after", get_session_id()))

            with ThreadPoolExecutor(max_workers=1) as ex:
                submit_with_log_vars(ex, task).result()
                ex.submit(probe).result()  # 同一 worker 裸探针
            # 任务期间持传播值
            self.assertEqual(observed[0], ("during", "outer-trace"))
            # 任务结束后同线程恢复默认（无残留）
            self.assertEqual(observed[1][0], "after")
            self.assertIn(observed[1][1], ("default_trace_id", None))
        finally:
            reset_session_id(outer_trace)


class TestSubmitWithContextvars(unittest.TestCase):
    def test_propagates_trace_id(self):
        from concurrent.futures import ThreadPoolExecutor

        outer_trace = set_session_id("outer-trace")
        try:
            results = {}

            def worker():
                results["trace"] = get_session_id()
                return "ok"

            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = submit_with_contextvars(ex, worker)
                self.assertEqual(fut.result(), "ok")
            self.assertEqual(results["trace"], "outer-trace")
        finally:
            reset_session_id(outer_trace)


# ─── log_init (DEF-05 adapt: request_id factory) ───


class TestLogInitFactory(unittest.TestCase):
    def setUp(self):
        # 每个测试前确保 factory 已装（幂等）
        init_logger()

    def test_factory_idempotent_no_double_wrap(self):
        """重复 init_logger 不叠加包装（sentinel 防重复）。"""
        f1 = logging.getLogRecordFactory()
        init_logger()
        f2 = logging.getLogRecordFactory()
        self.assertIs(f1, f2)

    def test_factory_injects_empty_slot_without_context(self):
        """无请求上下文时 request_id 为空串（不回退 trace_id）。"""
        # 确保 _request_ctx 为默认
        rec = logging.getLogRecordFactory()("test", logging.INFO, __file__, 1, "m", (), None)
        self.assertEqual(getattr(rec, "request_id", "MISSING"), "")

    def test_factory_injects_value_from_context(self):
        token = _request_ctx.set(RequestContext(request_id="rid-log"))
        try:
            rec = logging.getLogRecordFactory()("test", logging.INFO, __file__, 1, "m", (), None)
            self.assertEqual(rec.request_id, "rid-log")
        finally:
            _request_ctx.reset(token)


class TestLogInitFullContract(unittest.TestCase):
    """DEF-05 完整契约：四类冻结文件 + workflow 别名 + propagate:false。

    依赖 agent_builder.app 导入时触发的 init_logger()（test 进程内其它测试已导入）。
    """

    def test_four_target_files_created_and_writable(self):
        import os

        from agent_builder.adapter.config_bridge import settings

        root = settings.logging.log_path
        for rel in (
            "run/jiuwen.log",
            "interface/jiuwen_interface.log",
            "interface/jiuwen_prompt_builder_interface.log",
            "performance/jiuwen_performance.log",
        ):
            path = os.path.join(root, rel)
            self.assertTrue(os.path.isfile(path), f"目标文件未创建: {path}")
            self.assertTrue(os.access(path, os.W_OK), f"目标文件不可写: {path}")

    def test_workflow_logger_aliased_to_common(self):
        from openjiuwen.core.common.logging import LogManager

        self.assertIs(LogManager.get_logger("workflow"), LogManager.get_logger("common"))

    def test_builtin_loggers_do_not_propagate(self):
        from openjiuwen.core.common.logging import LogManager

        for log_type in ("common", "interface", "prompt_builder", "performance"):
            logger = LogManager.get_logger(log_type)
            inner = getattr(logger, "_logger", None) or logger
            self.assertFalse(
                getattr(inner, "propagate", False), f"{log_type} 不应向 root 传播"
            )


class TestLogInitFailFast(unittest.TestCase):
    """DEF-05 fail-fast 负例（审视 9268880d §3.2 + b2072b7 §1 + c0aff17 §2 + c02bb52 §2）：非法配置阻断启动、不留半初始化。

    覆盖：预校验非法 LOG_LEVEL/output（状态变更前 raise）+ try 块内 initialize 失败回滚 +
    不可写阻断 + initialize 真实 populate 后 _alias 失败→reset 清非空 _loggers + **reset 调
    close 真关 Handler（DEF-05 §7.1#8，handlers 清空）** + snapshot 恢复失败兜底。后四者断言
    失败后**状态**（factory 同一/配置恢复/非空 _loggers 被清空/Handler close 被调且 handlers
    清空/_initialized False/re-raise 原异常），**不 mock 被验证的恢复函数**
    （_restore_factory/configure_log_config/LogManager.reset/close 真实运行），只 mock 故障注入点。
    fault 点选在 initialize 之后（_alias）使 _loggers 先 populate 再被 reset 清空，断言非平凡。
    """

    @staticmethod
    def _fresh_log_init():
        import importlib

        import agent_builder.serve.common.logger.log_init as li

        return importlib.reload(li)

    def test_invalid_level_rejected_and_not_initialized(self):
        from agent_builder.adapter import config_bridge

        li = self._fresh_log_init()
        with mock.patch.object(config_bridge.settings.server, "log_level", "BOGUS"):
            with self.assertRaises(ValueError):
                li.init_logger()
        # 失败后 _initialized 保持 False（不半初始化，可重试）
        self.assertFalse(li._initialized)

    def test_invalid_output_member_rejected(self):
        li = self._fresh_log_init()

        def bad_cfg():
            # 字面构造（不调原函数避免递归）：output 含非法成员 console
            return {
                "level": "INFO",
                "output": ["console"],
                "interface_output": ["file"],
                "performance_output": ["file"],
                "log_path": str(li.settings.logging.log_path),
            }

        with mock.patch.object(li, "_build_logging_config", bad_cfg):
            with self.assertRaises(ValueError):
                li.init_logger()
        self.assertFalse(li._initialized)

    def test_try_block_failure_restores_state(self):
        """故障注入（审视 c0aff17 §2）：try 块内 LogManager.initialize 失败 → 真实恢复后
        factory/配置状态回到失败前 + _initialized False + re-raise 原异常。

        只 mock 故障注入点（LogManager.initialize）；_restore_factory/configure_log_config 真实运行。
        mock log_path 使 cfg 与 prior_snapshot 有差异，配置恢复断言有区分力（非 trivially true）。
        _loggers 断言此处置于 test_post_initialize_failure_clears_populated_loggers（此处 initialize
        被 mock 不 populate，_loggers 断言无意义，故不声称）。
        """
        import shutil
        import tempfile
        li = self._fresh_log_init()
        tmp = tempfile.mkdtemp()
        original_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(logging.LogRecord)  # 强制非 wrapper prior，使 _install/_restore 有意义
        try:
            prior_factory = logging.getLogRecordFactory()
            prior_snapshot = li.get_log_config_snapshot()
            with mock.patch.object(li.settings.server, "log_level", "INFO"), \
                 mock.patch.object(li.settings.logging, "log_path", tmp), \
                 mock.patch.object(li.LogManager, "initialize", side_effect=RuntimeError("injected-init-failure")):
                with self.assertRaises(RuntimeError) as ctx:
                    li.init_logger()
            self.assertIn("injected-init-failure", str(ctx.exception))
            self.assertFalse(li._initialized)
            self.assertIs(logging.getLogRecordFactory(), prior_factory)  # factory 真实恢复
            # cfg.log_path=tmp ≠ prior，configure_log_config(cfg) 真实变更 → 恢复有区分力
            self.assertEqual(li.get_log_config_snapshot(), prior_snapshot)
        finally:
            logging.setLogRecordFactory(original_factory)
            shutil.rmtree(tmp)

    def test_unwritable_target_file_blocks_and_cleans_up(self):
        """不可写场景（审视 c0aff17 §2）：目标文件不可写 → 真实 _verify_target_files 命中
        + 真实恢复后 factory/配置回到失败前 + _initialized False + re-raise。

        mock 只限 try 块前置步骤（initialize/get_all_loggers）以达 _verify_target_files；
        _verify_target_files 与恢复函数真实运行。root 用户跳过（os.access 对 root 永真）。
        """
        import os
        import shutil
        import tempfile
        if getattr(os, "geteuid", lambda: -1)() == 0:
            self.skipTest("root bypasses file write permission; os.access(W_OK) always True for root")
        li = self._fresh_log_init()
        tmp = tempfile.mkdtemp()
        for rel in li._TARGET_FILES.values():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").close()
        unwritable = os.path.join(tmp, li._TARGET_FILES["common"])
        os.chmod(unwritable, 0o444)
        original_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(logging.LogRecord)
        try:
            prior_factory = logging.getLogRecordFactory()
            prior_snapshot = li.get_log_config_snapshot()
            with mock.patch.object(li.settings.server, "log_level", "INFO"), \
                 mock.patch.object(li.settings.logging, "log_path", tmp), \
                 mock.patch.object(li.LogManager, "initialize"), \
                 mock.patch.object(li.LogManager, "get_all_loggers", return_value=list(li._BUILTIN_LOG_TYPES)):
                with self.assertRaises(RuntimeError) as ctx:
                    li.init_logger()
            self.assertIn("不可写", str(ctx.exception))
            self.assertFalse(li._initialized)
            self.assertIs(logging.getLogRecordFactory(), prior_factory)
            self.assertEqual(li.get_log_config_snapshot(), prior_snapshot)
        finally:
            logging.setLogRecordFactory(original_factory)
            os.chmod(unwritable, 0o644)
            shutil.rmtree(tmp)

    def test_post_initialize_failure_clears_populated_loggers(self):
        """核心回滚不变量（审视 c0aff17 §2.3）：initialize 真实 populate 4 Logger 后 _alias 失败 →
        真实恢复 reset 清空非空 _loggers + factory/配置恢复 + _initialized False + re-raise。

        只 mock 故障注入点（_alias_non_builtin_loggers_to_common，在 initialize 之后）；
        initialize/_verify_target_files/_restore_factory/configure_log_config/LogManager.reset 真实运行。
        _loggers 断言非 trivially true——initialize 先 populate 使其非空，reset 必须清空，
        若 reset 实现失效（忘记清）则 _loggers 仍非空，断言失败。
        """
        import os
        import shutil
        import tempfile
        li = self._fresh_log_init()
        tmp = tempfile.mkdtemp()
        for rel in li._TARGET_FILES.values():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").close()
        original_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(logging.LogRecord)
        loggers_at_fault = {}
        close_called = {}
        handlers_at_fault = []
        handler_close_called = {}

        def alias_side_effect():
            snap = dict(li.LogManager._loggers)  # initialize populate 后、reset 前
            loggers_at_fault["snap"] = snap
            # 包装每个 logger 的 close 以 spy reset 是否调 close（DEF-05 §7.1#8 Handler 真关闭）
            for log_type, logger in snap.items():
                orig_close = getattr(logger, "close", None)
                if callable(orig_close):
                    close_called[log_type] = False

                    def make_spy(lt, oc):
                        def spy():
                            close_called[lt] = True
                            return oc()  # 调真实 close（内部 handler.close()+removeHandler）
                        return spy
                    logger.close = make_spy(log_type, orig_close)
                # 再包装每个 handler 的 close 以抓"default_impl.close 只 removeHandler 跳过 handler.close"退化
                for h in getattr(getattr(logger, "_logger", None), "handlers", [])[:]:
                    handlers_at_fault.append(h)
                    handler_close_called[id(h)] = False
                    orig_h_close = h.close

                    def make_h_spy(hid, oc):
                        def h_spy():
                            handler_close_called[hid] = True
                            return oc()
                        return h_spy
                    h.close = make_h_spy(id(h), orig_h_close)
            raise RuntimeError("_alias-injected")
        try:
            prior_factory = logging.getLogRecordFactory()
            prior_snapshot = li.get_log_config_snapshot()
            with mock.patch.object(li.settings.server, "log_level", "INFO"), \
                 mock.patch.object(li.settings.logging, "log_path", tmp), \
                 mock.patch.object(li, "_alias_non_builtin_loggers_to_common", side_effect=alias_side_effect):
                with self.assertRaises(RuntimeError) as ctx:
                    li.init_logger()
            self.assertIn("_alias-injected", str(ctx.exception))
            self.assertFalse(li._initialized)
            self.assertIs(logging.getLogRecordFactory(), prior_factory)  # factory 真实恢复
            self.assertEqual(li.get_log_config_snapshot(), prior_snapshot)  # 配置真实恢复
            # 非平凡证明：fault 时 _loggers 非空（initialize 真实 populate 了 4 个内建 Logger）
            self.assertTrue(loggers_at_fault["snap"], "initialize 应 populate _loggers 使 fault 时非空")
            self.assertEqual(set(loggers_at_fault["snap"].keys()), set(li._BUILTIN_LOG_TYPES))
            # 核心：reset 真实清空了 fault 时的非空 _loggers
            self.assertEqual(li.LogManager._loggers, {})
            # DEF-05 §7.1#8：reset 调了每个已创建 logger 的 close（Handler 真关闭，非仅 _loggers 清空）
            for log_type in li._BUILTIN_LOG_TYPES:
                self.assertTrue(close_called.get(log_type), f"{log_type}.close 未被 reset 调用")
            # close() 内部 removeHandler（default_impl:579-585）→ 各 logger 的 handlers 清空
            for log_type, logger in loggers_at_fault["snap"].items():
                self.assertEqual(logger._logger.handlers, [], f"{log_type} handlers 未清空（Handler 未真关闭）")
            # Gap A 闭合：每个 handler.close() 被调（抓 default_impl.close 只 removeHandler 跳过 handler.close 的退化）
            self.assertTrue(handlers_at_fault, "fault 时应有 handler 被捕获")
            for h in handlers_at_fault:
                self.assertTrue(handler_close_called.get(id(h)), f"handler {h} close 未被调（handler.close 跳过）")
        finally:
            logging.setLogRecordFactory(original_factory)
            shutil.rmtree(tmp)

    def test_snapshot_restore_failure_fallback_clears_populated_loggers(self):
        """兜底路径（审视 c0aff17 §2.3）：initialize populate 后 _alias 失败 + snapshot 恢复自身失败 →
        LogManager.reset() 兜底清空非空 _loggers + 原异常（_alias 非 snapshot-restore）re-raise + factory 恢复。

        故障注入：_alias raise（try 末）+ configure_log_config 条件 side_effect（第1次真实、第2次 raise）；
        被验证的兜底（LogManager.reset）+ _restore_factory 真实运行。config 不声称恢复（snapshot 恢复失败）。
        """
        import os
        import shutil
        import tempfile
        li = self._fresh_log_init()
        tmp = tempfile.mkdtemp()
        for rel in li._TARGET_FILES.values():
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").close()
        original_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(logging.LogRecord)
        real_configure = li.configure_log_config
        call_count = [0]

        def cfg_side_effect(cfg):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("snapshot-restore-fail")  # except 恢复时失败
            return real_configure(cfg)  # 第1次（try）真实运行（reset+load）
        loggers_at_fault = {}
        close_called = {}
        handlers_at_fault = []
        handler_close_called = {}

        def alias_side_effect():
            snap = dict(li.LogManager._loggers)  # populate 后、兜底 reset 前
            loggers_at_fault["snap"] = snap
            for log_type, logger in snap.items():
                orig_close = getattr(logger, "close", None)
                if callable(orig_close):
                    close_called[log_type] = False

                    def make_spy(lt, oc):
                        def spy():
                            close_called[lt] = True
                            return oc()
                        return spy
                    logger.close = make_spy(log_type, orig_close)
                for h in getattr(getattr(logger, "_logger", None), "handlers", [])[:]:
                    handlers_at_fault.append(h)
                    handler_close_called[id(h)] = False
                    orig_h_close = h.close

                    def make_h_spy(hid, oc):
                        def h_spy():
                            handler_close_called[hid] = True
                            return oc()
                        return h_spy
                    h.close = make_h_spy(id(h), orig_h_close)
            raise RuntimeError("_alias-injected")
        try:
            prior_factory = logging.getLogRecordFactory()
            with mock.patch.object(li.settings.server, "log_level", "INFO"), \
                 mock.patch.object(li.settings.logging, "log_path", tmp), \
                 mock.patch.object(li, "_alias_non_builtin_loggers_to_common", side_effect=alias_side_effect), \
                 mock.patch.object(li, "configure_log_config", side_effect=cfg_side_effect), \
                 mock.patch.object(li, "_emit_failure_to_stderr"):
                with self.assertRaises(RuntimeError) as ctx:
                    li.init_logger()
            # 原异常（_alias 的）被 re-raise，非 snapshot 恢复异常
            self.assertIn("_alias-injected", str(ctx.exception))
            self.assertNotIn("snapshot-restore-fail", str(ctx.exception))
            self.assertFalse(li._initialized)
            # _restore_factory 在 snapshot 恢复失败前真实运行 → factory 恢复
            self.assertIs(logging.getLogRecordFactory(), prior_factory)
            # 非平凡证明：fault 时 _loggers 非空（initialize populate）
            self.assertTrue(loggers_at_fault["snap"], "initialize 应 populate _loggers 使 fault 时非空")
            self.assertEqual(set(loggers_at_fault["snap"].keys()), set(li._BUILTIN_LOG_TYPES))
            # 兜底：snapshot 恢复失败时 LogManager.reset() 真实清空了非空 _loggers
            self.assertEqual(li.LogManager._loggers, {})
            # DEF-05 §7.1#8：兜底 reset 调了每个 logger 的 close + 每个 handler.close 被调
            for log_type in li._BUILTIN_LOG_TYPES:
                self.assertTrue(close_called.get(log_type), f"{log_type}.close 未被兜底 reset 调用")
            for log_type, logger in loggers_at_fault["snap"].items():
                self.assertEqual(logger._logger.handlers, [], f"{log_type} handlers 未清空")
            self.assertTrue(handlers_at_fault, "fault 时应有 handler 被捕获")
            for h in handlers_at_fault:
                self.assertTrue(handler_close_called.get(id(h)), f"handler {h} close 未被调")
        finally:
            logging.setLogRecordFactory(original_factory)
            shutil.rmtree(tmp)


# ─── server_fastapi COM-05 ───


def _make_app_with_middleware():
    """内联复刻 establish_inbound_context 的隔离测试 app（审视 §2.3 订正表述）。

    **非生产入口**——为隔离复刻选值/双 token/回写/异常收口核心片段；
    生产 server_fastapi.instance_app() 路径的测试见 TestRealInstanceApp。
    """
    from agent_builder.serve.common.error_response import build_unhandled_error_response

    app = FastAPI()

    @app.middleware("http")
    async def establish(request, call_next):
        request_id, trace_id, ir, it = select_ids(request.headers)
        ctx = RequestContext(request_id=request_id, source=ContextSource.FASTAPI_MOUNT)
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request_token = _request_ctx.set(ctx)
        try:
            trace_token = set_session_id(trace_id)
        except Exception:
            _request_ctx.reset(request_token)
            raise
        try:
            response = await call_next(request)
            write_x_request_id(response, request_id)
            return response
        except Exception as exc:
            err = build_unhandled_error_response(request, exc)
            write_x_request_id(err, request_id)
            return err
        finally:
            try:
                reset_session_id(trace_token)
            finally:
                _request_ctx.reset(request_token)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("route exploded")

    return app


class TestEstablishInboundContext(unittest.TestCase):
    def test_success_response_carries_x_request_id(self):
        client = TestClient(_make_app_with_middleware())
        resp = client.get("/ok", headers={"X-Request-Id": "rid-hw-1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-hw-1")

    def test_generated_request_id_echoed_when_header_missing(self):
        client = TestClient(_make_app_with_middleware())
        resp = client.get("/ok")
        echoed = resp.headers.get("X-Request-Id")
        self.assertTrue(echoed)  # 生成的非空且回写

    def test_trace_id_from_traceid_header(self):
        """TraceID 合法时 trace_id 跟随（不随 conversation/execution）。"""
        client = TestClient(_make_app_with_middleware())
        # 经 /ok 路由内 _request_ctx 验证 trace_id
        outer = set_session_id("outer-t")
        try:
            captured = {}

            app = _make_app_with_middleware()

            @app.get("/cap")
            async def cap():
                captured["trace"] = get_session_id()
                return {"ok": True}

            client = TestClient(app)
            client.get("/cap", headers={"X-Request-Id": "r1", "TraceID": "t-from-header"})
            self.assertEqual(captured["trace"], "t-from-header")
        finally:
            reset_session_id(outer)

    def test_unhandled_exception_caught_with_x_request_id(self):
        """未处理异常在 token 有效期内收口 500 + X-Request-Id + 裸 internal_error。"""
        client = TestClient(_make_app_with_middleware(), raise_server_exceptions=False)
        resp = client.get("/boom", headers={"X-Request-Id": "rid-exc"})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-exc")
        body = resp.json()
        # P5-R3b: COM-03 canonical8 五字段（openjiuwen.13100004 INTERNAL_ERROR）
        self.assertEqual(body["error_code"], "openjiuwen.13100004")
        for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
            self.assertTrue(body.get(f), f"{f} non-empty")


if __name__ == "__main__":
    unittest.main()


# ─── 真实生产入口 server_fastapi.instance_app()（审视 §2.3） ───


class TestRealInstanceApp(unittest.TestCase):
    """经生产 instance_app() 路径验证（移除生产中间件接线时这些测试失败）。

    instance_app() 含真实 establish_inbound_context 注册（最外层）+ normalize +
    路由 + Flask mount；本类测试经完整生产栈，不经内联复刻。
    """

    @staticmethod
    def _client(**kwargs):
        from agent_builder.serve.server_fastapi import instance_app
        return TestClient(instance_app(), **kwargs)

    def test_health_ok_with_x_request_id_writeback(self):
        resp = self._client(raise_server_exceptions=False).get(
            "/v1/health", headers={"X-Request-Id": "rid-real-1"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-real-1")

    def test_generated_request_id_echoed_when_header_missing(self):
        resp = self._client(raise_server_exceptions=False).get("/v1/health")
        self.assertTrue(resp.headers.get("X-Request-Id"))

    @staticmethod
    def _probe_app(endpoint, path):
        """真实 instance_app() + 探针路由插到 Flask "/" mount 之前（否则被 mount 遮蔽 404）。"""
        from starlette.routing import Route

        from agent_builder.serve.server_fastapi import instance_app

        app = instance_app()

        async def handler(request):
            await endpoint(request)
            return JSONResponse({"ok": True})

        app.router.routes.insert(0, Route(path, handler, methods=["GET"]))
        return app

    def test_workspace_query_fallback_reaches_request_headers(self):
        """§2.2：仅带 ?workspace_id= 的请求，model_service getter 读到回退值（真实入口）。"""
        from agent_builder.adapter.request_context_bridge import (
            _request_ctx,
            get_request_headers,
        )

        captured = {}

        async def endpoint(request):
            ctx = _request_ctx.get()
            captured["ctx_ws"] = ctx.headers.get("X-Workspace-Id", "")
            captured["getter_ws"] = get_request_headers().get("X-Workspace-Id", "")

        app = self._probe_app(endpoint, "/_probe_ws")
        resp = TestClient(app, raise_server_exceptions=False).get(
            "/_probe_ws?workspace_id=ws-from-query"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(captured["ctx_ws"], "ws-from-query")
        self.assertEqual(captured["getter_ws"], "ws-from-query")

    def test_workspace_header_takes_priority_over_query(self):
        from agent_builder.adapter.request_context_bridge import _request_ctx

        captured = {}

        async def endpoint(request):
            captured["ws"] = _request_ctx.get().headers.get("X-Workspace-Id", "")

        app = self._probe_app(endpoint, "/_probe_ws2")
        TestClient(app, raise_server_exceptions=False).get(
            "/_probe_ws2?workspace_id=ws-query", headers={"X-Workspace-Id": "ws-header"}
        )
        self.assertEqual(captured["ws"], "ws-header")

    def test_unhandled_exception_caught_in_real_app(self):
        """真实入口异常收口：500 + X-Request-Id + 裸 internal_error（COM-03 延 S3）。"""
        app = self._probe_app(lambda request: (_ for _ in ()).throw(RuntimeError("real boom")), "/_boom_real")
        resp = TestClient(app, raise_server_exceptions=False).get(
            "/_boom_real", headers={"X-Request-Id": "rid-real-exc"}
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.headers.get("X-Request-Id"), "rid-real-exc")
        # P5-R3b: COM-03 canonical8 五字段
        _body = resp.json()
        self.assertEqual(_body["error_code"], "openjiuwen.13100004")
        for f in ("error_msg", "error_reason", "error_suggestion", "request_id"):
            self.assertTrue(_body.get(f), f"{f} non-empty")

    def test_context_reset_after_request_in_real_app(self):
        """真实入口请求期间 trace_id 生效（establish 传播）+ 连续请求不串号。

        边界（审视 9268880d §3.3 如实限定）：TestClient 请求跑在 portal 线程，
        无法从测试协程断言"返回后清理"——该不变量由单元层同任务 dispatch 测试
        （Runtime test_request_context_def03_com05 同款）覆盖；此处验证请求期间
        传播正确 + 同 client 连续两请求各读各的 trace（若 establish 未每请求
        重建/清理，第二次会读到残留旧值之外的可观测异常路径）。
        """
        from openjiuwen.core.common.logging import get_session_id as core_get

        captured = {}

        async def endpoint(request):
            captured[request.query_params.get("tag")] = core_get()

        app = self._probe_app(endpoint, "/_probe_ctx")
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/_probe_ctx?tag=a", headers={"X-Request-Id": "r1", "TraceID": "t-a"})
        client.get("/_probe_ctx?tag=b", headers={"X-Request-Id": "r2", "TraceID": "t-b"})
        self.assertEqual(captured["a"], "t-a")
        self.assertEqual(captured["b"], "t-b")
