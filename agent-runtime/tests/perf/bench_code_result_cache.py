#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""代码执行节点结果缓存时延基准。

对比同一代码节点重复执行时，缓存关闭 vs 开启的单次 invoke 时延：
    python tests/perf/bench_code_result_cache.py

说明：
- 使用真实 InprocessCodeRunner（LOCAL_CODE_EXEC_MODE=inprocess 默认路径），mock 掉 session。
- 缓存通过 patch get_code_result_cache 开/关，与生产开关
  CODE_EXECUTION_RESULT_CACHE_ENABLE 行为一致。
"""

import asyncio
import os
import statistics
import sys
import time
from unittest.mock import MagicMock, patch

# 与 tests/unit_tests/extension/workflow_node/conftest.py 相同的 path 修正：
# 脚本直跑时 common_utils（editable 依赖）不在 sys.path，需手动补上
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_COMMON_UTILS = os.path.join(_REPO_ROOT, "packages", "common_utils")
if os.path.isdir(_COMMON_UTILS) and _COMMON_UTILS not in sys.path:
    sys.path.append(_COMMON_UTILS)

from agent_runtime.extension.workflow_node.flow_code import FlowCode, FlowCodeConfig

# 模拟典型业务代码节点：解析 + 字段抽取 + 拼装（纯函数，幂等）
USER_CODE = """
import json

def main(args):
    text = args.get("text", "")
    items = [i.strip() for i in text.split(",") if i.strip()]
    summary = {
        "count": len(items),
        "upper": [i.upper() for i in items],
        "joined": "-".join(items),
    }
    print("processed", len(items), "items")
    return summary
"""

INPUTS = {
    "text": "alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa"
}

WARMUP = 5
N = 200


def _make_session():
    from unittest.mock import AsyncMock

    session = MagicMock()
    session.get_component_id.return_value = "bench_code"
    session.get_session_id.return_value = "bench"
    session.get_workflow_id.return_value = "bench_wf"
    # trace 打桩为 no-op，排除 tracer 开销干扰
    session.trace = AsyncMock()
    return session


async def _invoke(flow_code):
    from openjiuwen.core.common.constants.constant import USER_FIELDS

    result = await flow_code.invoke(
        inputs={USER_FIELDS: dict(INPUTS)},
        session=_make_session(),
        context=MagicMock(),
    )
    return result


async def _run_bench(label, cache_enabled):
    flow_code = FlowCode(FlowCodeConfig(code=USER_CODE, exec_env="local"))
    cache = None
    if cache_enabled:
        from agent_runtime.extension.workflow_node.code_runner.result_cache import (
            CodeResultCache,
        )

        cache = CodeResultCache(maxsize=256)

    with patch(
        "agent_runtime.extension.workflow_node.flow_code.get_code_result_cache",
        return_value=cache,
    ):
        # 预热（首次执行含懒加载等固定开销）
        for _ in range(WARMUP):
            await _invoke(flow_code)

        latencies = []
        for _ in range(N):
            start = time.perf_counter()
            await _invoke(flow_code)
            latencies.append((time.perf_counter() - start) * 1000.0)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    avg = statistics.fmean(latencies)
    print(
        f"{label:<28} avg={avg:8.3f}ms  p50={p50:8.3f}ms  "
        f"p95={p95:8.3f}ms  min={latencies[0]:8.3f}ms  max={latencies[-1]:8.3f}ms"
    )
    if cache is not None:
        print(f"{'':28} cache stats: {cache.stats()}")
    return avg


async def main():
    print(f"iterations={N} (after {WARMUP} warmup), exec_mode=inprocess\n")
    avg_off = await _run_bench("cache OFF (baseline)", cache_enabled=False)
    avg_on = await _run_bench("cache ON (hit path)", cache_enabled=True)
    print(
        f"\nhit-path saving: {avg_off - avg_on:.3f}ms "
        f"({(avg_off - avg_on) / avg_off * 100:.1f}% of baseline avg)"
    )


if __name__ == "__main__":
    asyncio.run(main())
