# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Compare barrier resolution with the pre-optimization revision.

Run from any directory with Python 3.11+ (no runtime dependencies required):
    python benchmark_nested_branch_barrier.py --baseline f80a12b65

Executes the actual patch functions in isolated namespaces, using lightweight
graph/router objects. Graph construction and framework initialization are not
timed. These synthetic measurements are not whole-workflow latency estimates.
"""
# pylint: disable=protected-access  # benchmark 须注入/调用内部方法（仓库既有惯例）
import argparse
import ast
import gc
import logging
import statistics
import subprocess
import tracemalloc
from pathlib import Path
from time import perf_counter_ns
from types import MethodType, SimpleNamespace

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

RUNTIME = Path(__file__).resolve().parents[2]
PATCH = RUNTIME / "jiuwen/extension/patches/nested_branch_barrier_patch.py"


def load_functions(source):
    tree = ast.parse(source)
    # The only external top-level import is the logger; no measured function
    # uses it. Keep the original algorithms, imports and type annotations.
    # G.EXP.04：多行条件推导式改显式循环
    body = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module.startswith("openjiuwen."):
            continue
        body.append(node)
    tree.body = body
    namespace = {}
    exec(compile(tree, str(PATCH), "exec"), namespace)
    return namespace


def topology(size, coexec):
    """Two equal lanes; conditional fallback chain adds serial diamonds."""
    edges = []
    starts, ends = [], []
    for lane in ("safe", "rag"):
        nodes = [f"{lane}{i}" for i in range(size // 2)]
        starts.append(nodes[0])
        ends.append(nodes[-1])
        edges.extend(zip(nodes, nodes[1:]))
        edges.append((nodes[-1], "JOIN"))
    branches, targets = {}, {}
    for i in range(4 if coexec else 1):
        name = f"branch{i}"
        fallback = [f"branch{i+1}"] if i < 3 else ["example"]
        paths = [starts, fallback] if coexec else [[starts[0]], [starts[1]]]
        conditions = [SimpleNamespace(branch_id=f"{name}-{j}", target=path)
                      for j, path in enumerate(paths)]
        branches[name] = {"router": SimpleNamespace(
            condition=SimpleNamespace(_branches=conditions))}
        targets[name] = {target for path in paths for target in path}
    if coexec:
        edges.extend(("example", start) for start in starts)
    return dict(edges=edges, branches=branches, branch_targets=targets), [{n} for n in ends]


def graph(namespace, data):
    result = SimpleNamespace(**data)
    result._forward_reachable = MethodType(namespace["_forward_reachable_patched"], result)
    result._branch_root = namespace["_branch_root_patched"]
    return result


def resolve(namespace, data, sources, repeats, barriers):
    elapsed = []
    normalized = None
    for _ in range(repeats):
        instance = graph(namespace, data)
        gc.collect()
        start = perf_counter_ns()
        for _ in range(barriers):
            resolved = namespace["_resolve_barrier_groups_nested_patched"](
                instance, "JOIN", sources)
        elapsed.append((perf_counter_ns() - start) / 1e6)
        normalized = {frozenset(group) for group in resolved}
    return statistics.median(elapsed), normalized


def cache_memory(namespace, getter, size, cycle):
    adj = {str(i): [str(i + 1)] for i in range(size - 1)}
    adj[str(size - 1)] = ["0"] if cycle else []
    instance = SimpleNamespace(_adj_cache=adj)
    gc.collect()
    tracemalloc.start()
    namespace[getter](instance)
    # Exclude temporary tuples retained by Python's allocator free lists.
    gc.collect()
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return retained / 1024, peak / 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="f80a12b65")
    parser.add_argument("--repeats", type=int, default=21)
    args = parser.parse_args()
    baseline = subprocess.check_output(
        ["git", "show", f"{args.baseline}:agent-runtime/jiuwen/extension/patches/"
         "nested_branch_barrier_patch.py"], cwd=RUNTIME, encoding="utf-8")
    before = load_functions(baseline)
    after = load_functions(PATCH.read_bytes())
    logger.info("Barrier resolution: median milliseconds, fresh graph caches per sample")
    logger.info("lane_nodes,coexec,barriers,before_ms,after_ms,reduction_pct")
    for size in (100, 1000, 10000):
        for coexec in (False, True):
            data, sources = topology(size, coexec)
            for barriers in (1, 20):
                # Warm code paths and check semantic equivalence before timing.
                # G.TES.01：assert 改显式 if+raise（优化字节码下不丢失）
                _, old_groups = resolve(before, data, sources, 2, barriers)
                _, new_groups = resolve(after, data, sources, 2, barriers)
                if old_groups != new_groups:
                    raise RuntimeError(
                        f"Semantic equivalence failed at size={size}, "
                        f"coexec={coexec}, barriers={barriers}: "
                        f"before={old_groups} after={new_groups}")
                # Alternate order to reduce systematic timing bias.
                old_times, new_times = [], []
                for i in range(args.repeats):
                    order = [(before, old_times), (after, new_times)]
                    for ns, times in order if i % 2 == 0 else reversed(order):
                        value, _ = resolve(ns, data, sources, 1, barriers)
                        times.append(value)
                old = statistics.median(old_times)
                new = statistics.median(new_times)
                logger.info(
                    "%d,%s,%d,%.4f,%.4f,%.1f",
                    size, coexec, barriers, old, new, (1 - new / old) * 100)
    logger.info("Cycle cache memory: retained KiB / peak KiB, adjacency excluded")
    for cycle in (False, True):
        old = cache_memory(before, "_get_scc", 10000, cycle)
        new = cache_memory(after, "_get_cyclic_nodes", 10000, cycle)
        logger.info("10000 nodes, cycle=%s: before=%s, after=%s", cycle, old, new)


if __name__ == "__main__":
    main()
