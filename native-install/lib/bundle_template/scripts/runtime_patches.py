#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runtime_patches.py — 可移植的第三方包补丁（替代容器内 docker/studio-runtime/script/init.sh 的 sed hack）

为什么需要：原 init.sh 用 `sed -i` 改 /usr/local/lib/python3.11/site-packages/ 下若干第三方包源码
（SpiffWorkflow 循环支持、jionlp 敏感信息、mcp SSL 关闭）。原生环境无该硬编码路径，sed 会静默失效，
导致工作流循环等功能损坏。本脚本用 site.getsitepackages() 解析真实 venv site-packages，跨 Windows/Linux 通用。

忠实复刻：每个补丁与 init.sh 的 sed 语义逐条等价（含 95a 行号插入、/for task in tasks/a 锚点插入、
s%...%...%g 字符串替换、/.../d 行删除），并通过 .bak 备份保证幂等。补丁目标对应 spiffworkflow==2.0.1
（requirements.txt 锁定版本）；如检测到其它版本会对位置插入型补丁告警但 best-effort 执行。

用法：由 venv 的 python 运行 ——
  Linux:   run/venv/bin/python scripts/runtime_patches.py
  Windows: run\\venv\\Scripts\\python.exe scripts\\runtime_patches.py
"""
import os
import sys
import site
import shutil
import pathlib

def resolve_site_packages() -> pathlib.Path:
    paths = site.getsitepackages()
    # 优先取不含 site-packages 字面量的纯路径；通常第一个即 venv site-packages
    for p in paths:
        if "site-packages" in p:
            return pathlib.Path(p)
    return pathlib.Path(paths[0])

def backup_once(p: pathlib.Path):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(p, bak)

def patch_text(p: pathlib.Path, transform, guard_bak=True):
    """对单个文件做文本变换；文件不存在则告警跳过（等价 init.sh 的 || true）。"""
    if not p.exists():
        print(f"[patch] SKIP (missing): {p}")
        return
    if guard_bak:
        backup_once(p)
    try:
        t = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        t = p.read_text(encoding="utf-8", errors="replace")
    new = transform(t)
    if new != t:
        p.write_text(new, encoding="utf-8")
        print(f"[patch] OK   : {p}")
    else:
        print(f"[patch] noop : {p} (already patched or pattern not found)")

def insert_after_line(p: pathlib.Path, lineno_1based: int, block_lines: list):
    """复刻 sed '95a\\n...' —— 在指定行（1-based）之后插入 block_lines（已含前导空行等）。
    受 .bak 守卫保护，幂等。"""
    if not p.exists():
        print(f"[patch] SKIP (missing): {p}")
        return
    bak = p.with_suffix(p.suffix + ".bak")
    if bak.exists():
        print(f"[patch] skip : {p} (.bak exists, already patched)")
        return
    shutil.copy2(p, bak)
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = lineno_1based  # 插入点：第 lineno 行之后 → 索引 lineno（0-based）
    if idx > len(lines):
        print(f"[patch] WARN: {p} only {len(lines)} lines, cannot insert after line {lineno_1based}")
        return
    block = "".join(l if l.endswith("\n") else l + "\n" for l in block_lines)
    new = "".join(lines[:idx]) + block + "".join(lines[idx:])
    p.write_text(new, encoding="utf-8")
    print(f"[patch] OK   : {p} (inserted {len(block_lines)} lines after line {lineno_1based})")

def insert_after_match(p: pathlib.Path, anchor_substring: str, block_lines: list, guard_bak=True):
    """复刻 sed '/anchor/a ...' —— 在每个含 anchor_substring 的行之后插入 block_lines。"""
    if not p.exists():
        print(f"[patch] SKIP (missing): {p}")
        return
    if guard_bak:
        backup_once(p)
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    block = [l if l.endswith("\n") else l + "\n" for l in block_lines]
    inserted = 0
    for l in lines:
        out.append(l)
        if anchor_substring in l:
            out.extend(block)
            inserted += 1
    if inserted:
        p.write_text("".join(out), encoding="utf-8")
        print(f"[patch] OK   : {p} (inserted after {inserted} match(es) of '{anchor_substring}')")
    else:
        print(f"[patch] noop : {p} (anchor '{anchor_substring}' not found)")

def delete_lines_with(p: pathlib.Path, substring: str):
    """复刻 sed '/.../d' —— 删除所有含 substring 的行。幂等。"""
    if not p.exists():
        print(f"[patch] SKIP (missing): {p}")
        return
    backup_once(p)
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [l for l in lines if substring not in l]
    if len(kept) != len(lines):
        p.write_text("".join(kept), encoding="utf-8")
        print(f"[patch] OK   : {p} (deleted {len(lines)-len(kept)} line(s) with '{substring}')")
    else:
        print(f"[patch] noop : {p} (no line with '{substring}')")

def main():
    sp = resolve_site_packages()
    print(f"[patch] site-packages = {sp}")
    if not sp.exists():
        print("[patch] FATAL: site-packages not found", file=sys.stderr)
        sys.exit(1)

    # spiffworkflow 版本告警（位置插入型补丁针对 2.0.1）
    ig = sp / "SpiffWorkflow" / "bpmn" / "specs" / "mixins" / "inclusive_gateway.py"
    try:
        import importlib.metadata as md
        ver = md.version("spiffworkflow")
        if ver != "2.0.1":
            print(f"[patch] WARN: spiffworkflow=={ver} (patches target 2.0.1; line-position insert may misalign)")
    except Exception:
        pass

    # 1) inclusive_gateway.py：READY|WAITING → +STARTED（字符串替换）
    patch_text(
        ig,
        lambda t: t.replace(
            "tasks = my_task.workflow.get_tasks(TaskState.READY | TaskState.WAITING, workflow=my_task.workflow)",
            "tasks = my_task.workflow.get_tasks(TaskState.READY | TaskState.WAITING | TaskState.STARTED, workflow=my_task.workflow)  # STARTED /NOT_YET_COMPLETED 也算活跃状态",
        ),
        guard_bak=False,
    )

    # 2) inclusive_gateway.py：95a 插入 check() 循环覆盖（位置插入，受 .bak 守卫）
    insert_after_line(ig, 95, [
        "",
        "            # 覆盖原有 check 函数，允许循环",
        "            import copy",
        "            def check(spec, path_history=None):",
        "                path_history = [] if not isinstance(path_history, list) else path_history",
        "                for parent in spec.inputs:",
        "                    if parent is self or parent in path_history:",
        "                        continue",
        "                    if parent in sources:",
        "                        return parent",
        "                    path_history_continue = copy.copy(path_history)",
        "                    path_history_continue.append(spec)",
        "                    found = check(parent, path_history=path_history_continue)",
        "                    if found:",
        "                        return found",
        "                return None",
    ])

    # 3) unstructured_join.py：/for task in tasks/a 插入 CANCELLED|COMPLETED 跳过
    uj = sp / "SpiffWorkflow" / "bpmn" / "specs" / "mixins" / "unstructured_join.py"
    insert_after_match(uj, "for task in tasks", [
        "            if task._has_state(TaskState.CANCELLED | TaskState.COMPLETED):",
        "                continue",
    ])

    # 4) jionlp/util/help_search.py：删除含 微信公众号 的行
    jionlp = sp / "jionlp" / "util" / "help_search.py"
    delete_lines_with(jionlp, "微信公众号")

    # 5) mcp/client/sse.py：httpx.AsyncClient(headers=headers) → (..., verify=False)
    mcp_sse = sp / "mcp" / "client" / "sse.py"
    patch_text(
        mcp_sse,
        lambda t: t.replace(
            "async with httpx.AsyncClient(headers=headers)",
            "async with httpx.AsyncClient(headers=headers, verify=False)",
        ),
        guard_bak=False,
    )

    # 6) mcp/shared/_httpx_utils.py：return httpx.AsyncClient(**kwargs) → (verify=False, **kwargs)
    mcp_httpx = sp / "mcp" / "shared" / "_httpx_utils.py"
    patch_text(
        mcp_httpx,
        lambda t: t.replace(
            "return httpx.AsyncClient(**kwargs)",
            "return httpx.AsyncClient(verify=False, **kwargs)",
        ),
        guard_bak=False,
    )

    print("[patch] done.")

if __name__ == "__main__":
    main()
