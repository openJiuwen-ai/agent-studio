# agent_builder Microservice Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull `agent_builder` out of the `agent_runtime` process into its own independently-deployed FastAPI microservice (port 31015, own Docker image), while stripping agent_runtime's 3 hosting edges so the two share only Redis/OBS/DB infra.

**Architecture:** New `agent_builder/serve/server_fastapi.py` mirrors `agent_runtime/serve/server.py` — a FastAPI shell that mounts the existing single Flask `agent_builder.app` via `WSGIMiddleware` and includes a new `builder_router` (moved n2l endpoint + health) BEFORE the Flask mount. New `EIBuilder.py`/`EIBuilder_base.py` run it under uvicorn. agent_runtime's 3 edges (Flask mount import, `ContextManager` lifespan, n2l endpoint) are removed. New `docker/studio-builder/Dockerfile` builds only `agent_builder + jiuwen + agent-core`; `studio-runtime` Dockerfile drops the `agent_builder/` COPY.

**Tech Stack:** Python 3.11 (`agent-runtime/.venv`), FastAPI 0.115.7, Flask 3.1.3, uvicorn 0.34.0, pydantic 2.10.6, openjiuwen/jiuwen (agent-core), Docker.

## Global Constraints

- **Interpreter:** all test/run commands use `agent-runtime/.venv/Scripts/python.exe` (Python 3.11.15) from the repo root `C:\work\code\agent-studio`. It already imports `agent_builder` + `openjiuwen` + `fastapi.testclient` successfully.
- **No agent_runtime imports from agent_builder after completion:** the precise check is `grep -rnE "^\s*(from agent_builder|import agent_builder)\b" agent-runtime/agent_runtime/ --include="*.py" | grep -v __pycache__` must return empty. (Do NOT grep for the bare substring `agent_builder` — `agent_builder_error_handler` and `AgentBuilderError` in `agent_runtime` are unrelated to the package.) Final acceptance gate is Task 4 Step 5.
- **agent_builder must not import agent_runtime:** confirmed already zero `from agent_runtime`/`import agent_runtime` (excluding the `agent_rl` local module). Do not add any.
- **Builder port: 31015** (set via `SERVER_PORT=31015` env at deploy). Runtime stays 31014.
- **Logging:** use agent_builder's own `set_thread_session`/`get_thread_session` (from `agent_builder.adapter.logger_bridge`) + `init_logger`. Do NOT import `agent_runtime.common.logging_context`, `RequestContextMiddleware`, or `_request_ctx`.
- **Flask app shape:** `agent_builder.app.app` is the SINGLE Flask app; it already has `prompt.manager` + `mmapo.manager` blueprints registered (via `ServerApp` in `agent_builder/serve/server.py`). Mount only this one Flask app; do NOT mount `mmapo_app` separately.
- **FastAPI routers before Flask mount:** preserve `# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)` — `apps_map` lists the FastAPI `builder_router` before the Flask app.
- Commit after each task. Branch `studio-2.0-dev` (already checked out — not the default `develop`).

---

### Task 1: Move the n2l endpoint into a new agent_builder FastAPI router

**Files:**
- Create: `agent_builder/serve/apis/n2l_api.py`
- Test: `agent_builder/tests/test_n2l_api.py`

**Interfaces:**
- Consumes: `from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat` (already exist; signatures unchanged — `_n2l_json_wapper(project_id, agent_type, cid, dict, request) -> dict`, `async def _chat(req_json: dict) -> StreamingResponse`).
- Produces: `builder_router` — a `fastapi.APIRouter` named `builder_router` with two routes: `GET /v1/health` and `POST /v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat`. Later tasks import `from agent_builder.serve.apis.n2l_api import builder_router`.

- [ ] **Step 1: Write the failing test**

Create `agent_builder/tests/test_n2l_api.py`:
```python
"""Tests for the builder FastAPI router (route registration only)."""
from agent_builder.serve.apis.n2l_api import builder_router


def _paths(router):
    return {getattr(r, "path", None) for r in router.routes}


def test_builder_router_has_health():
    assert "/v1/health" in _paths(builder_router)


def test_builder_router_has_n2l_chat():
    n2l = "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
    assert n2l in _paths(builder_router)


def test_n2l_chat_methods_include_post():
    n2l = "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
    methods = set()
    for r in builder_router.routes:
        if getattr(r, "path", None) == n2l:
            methods.update(r.methods or [])
    assert "POST" in methods
```

- [ ] **Step 2: Run test to verify it fails**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_n2l_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_builder.serve.apis.n2l_api'`

- [ ] **Step 3: Write minimal implementation**

Create `agent_builder/serve/apis/n2l_api.py`:
```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""agent_builder FastAPI router — n2l chat + health (moved out of agent_runtime)."""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat

builder_router = APIRouter(tags=["builder"])


@builder_router.get("/v1/health", response_class=PlainTextResponse)
async def health():
    """Restful API for server health."""
    return "the health is good"


@builder_router.post(
    "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"
)
async def chat_n2l(
    project_id: str,
    agent_type: str,
    cid: str,
    body: N2LRequestBody,
    request: Request,
) -> StreamingResponse:
    """NL2 chat — natural-language to agent generation (moved from
    agent_runtime/serve/apis/orchestration.py)."""
    payload = _n2l_json_wapper(
        project_id,
        agent_type,
        cid,
        body.model_dump(exclude_unset=True),
        request,
    )
    return await _chat(payload)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_n2l_api.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add agent_builder/serve/apis/n2l_api.py agent_builder/tests/test_n2l_api.py
git commit -m "feat(agent_builder): move n2l chat endpoint into builder FastAPI router"
```

---

### Task 2: Build the agent_builder FastAPI server shell

**Files:**
- Create: `agent_builder/serve/server_fastapi.py`
- Test: `agent_builder/tests/test_server_fastapi.py`

**Interfaces:**
- Consumes: `from agent_builder.app import app as prompt_manage_app` (the single Flask app); `from agent_builder.serve.apis.n2l_api import builder_router` (Task 1); `from agent_builder.adapter.logger_bridge import set_thread_session, get_thread_session`; `from agent_builder.adapter.exception_bridge import JiuWenException`; `from agent_builder.adapter.config_bridge import settings`; `from agent_builder.adapter.redis_bridge import RedisClientManager` (replica, has `get_instance().init()` + `get_client()` + `is_initialized`); `from agent_builder.prompt.tune.base.context_manager import ContextManager`.
- Produces: module-level `app` (a `fastapi.FastAPI`) at `agent_builder.serve.server_fastapi:app` — consumed by Task 3's uvicorn entrypoint and by tests.

- [ ] **Step 1: Write the failing test**

Create `agent_builder/tests/test_server_fastapi.py`:
```python
"""Tests for the agent_builder FastAPI shell — route surface only.

Uses TestClient WITHOUT entering lifespan (no `with`), so startup hooks
(ContextManager set_store / Redis ping) do not run and no infra is required.
"""
from fastapi.testclient import TestClient

from agent_builder.serve.server_fastapi import app


def _client():
    # No `with` → lifespan does not run → no Redis/DB needed.
    return TestClient(app, raise_server_exceptions=False)


def test_health_returns_200_without_lifespan():
    r = _client().get("/v1/health")
    assert r.status_code == 200
    assert r.text == "the health is good"


def test_n2l_route_is_registered():
    routes = {getattr(r, "path", None) for r in app.routes}
    assert "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat" in routes


def test_flask_app_mounted_at_root():
    # The Flask app is mounted at "/" via WSGIMiddleware → a Flask route
    # (e.g. /flask/...) should be reachable through the FastAPI app.
    # We only assert the mount exists (Flask catch-all), not a specific payload.
    mounts = [r for r in app.routes if getattr(r, "path", None) == "/"]
    assert len(mounts) >= 1, "Flask app should be mounted at '/'"


def test_flask_path_normalization_middleware_present():
    # normalize_flask_path rewrites /v1/prompt/... -> /flask/v1/prompt/...
    # Assert it does not crash on a /v1/prompt/ request (Flask returns 404
    # for unknown sub-paths, but must not 500).
    r = _client().get("/v1/prompt/__nonexistent__")
    assert r.status_code != 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_server_fastapi.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_builder.serve.server_fastapi'`

- [ ] **Step 3: Write minimal implementation**

Create `agent_builder/serve/server_fastapi.py`:
```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
agent_builder FastAPI server — mirrors agent_runtime/serve/server.py structure.

FastAPI shell that mounts the existing single Flask `agent_builder.app` via
WSGIMiddleware and includes the builder_router (n2l + health) BEFORE the
Flask mount (Flask catches all routes).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from flask import Flask
from starlette.middleware.wsgi import WSGIMiddleware

from agent_builder.adapter.config_bridge import settings
from agent_builder.adapter.exception_bridge import JiuWenException
from agent_builder.adapter.logger_bridge import get_thread_session, set_thread_session

# Single Flask app (already has prompt.manager + mmapo.manager blueprints
# registered via ServerApp in agent_builder/serve/server.py).
from agent_builder.app import app as prompt_manage_app
from agent_builder.serve.apis.n2l_api import builder_router

logger = logging.getLogger("agent_builder.server_fastapi")

# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)
apps_map = [builder_router, prompt_manage_app]


async def _ping_redis() -> None:
    """Best-effort Redis ping at startup (fail-fast on misconfig).

    n2l history.py creates its client lazily from the same config_bridge
    settings; this only validates config at boot. Warn-and-continue on failure.
    """
    try:
        from agent_builder.adapter.redis_bridge import RedisClientManager

        mgr = RedisClientManager.get_instance()
        mgr.init()
        if not mgr.is_initialized:
            logger.warning("Redis client not initialized (non-critical)")
            return
        client = mgr.get_client()
        await client.ping()
        logger.info("Redis connection check passed")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Redis connection check failed (non-critical): {e}")


async def _init_prompt_store() -> None:
    """Initialize prompt-optimization DB store (moved from agent_runtime lifespan)."""
    try:
        from agent_builder.prompt.tune.base.context_manager import ContextManager

        ContextManager().set_store()
        logger.info("Prompt optimization store initialized")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Prompt optimization store init failed (non-critical): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: redefined-outer-name
    await _init_prompt_store()
    await _ping_redis()
    try:
        yield
    finally:
        logger.info("agent_builder shutdown")


def instance_app(config: dict | None = None) -> FastAPI:
    """Build the agent_builder FastAPI server."""
    app = FastAPI(
        lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )

    @app.middleware("http")
    async def set_trace_id(request: Request, call_next):
        trace_id = request.headers.get("TraceID", "")
        set_thread_session(trace_id)
        return await call_next(request)

    # Flask 路径规范化中间件：OptimizationTemplateService 调用 /v1/prompt/...
    # 而 Flask blueprint 注册了 url_prefix="/flask"，需要统一补上前缀
    @app.middleware("http")
    async def normalize_flask_path(request: Request, call_next):
        path = request.url.path
        if path.startswith("/v1/prompt/") and not path.startswith("/flask"):
            prefixed = f"/flask{path}"
            request = Request(request.scope, request.receive)
            request.scope["path"] = prefixed
        return await call_next(request)

    for i in apps_map:
        if isinstance(i, Flask):
            app.mount("/", WSGIMiddleware(i))
        else:
            app.include_router(i)

    @app.exception_handler(JiuWenException)
    async def builder_exception_handler(request: Request, exc: JiuWenException):
        trace_id = get_thread_session()
        logger.error(
            f"JiuWenException: {exc}, trace_id={trace_id}", exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": getattr(exc, "error_code", -1),
                    "message": str(exc),
                    "trace_id": trace_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        trace_id = get_thread_session()
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}, trace_id={trace_id}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "trace_id": trace_id,
                }
            },
        )

    return app


# Create the app instance at module level
app = instance_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_server_fastapi.py -v`
Expected: PASS (4 tests). If `test_flask_path_normalization_middleware_present` returns 500, inspect the WSGIMiddleware mount order — Flask must be last in `apps_map` (it is).

- [ ] **Step 5: Commit**

```bash
git add agent_builder/serve/server_fastapi.py agent_builder/tests/test_server_fastapi.py
git commit -m "feat(agent_builder): FastAPI server shell mounting Flask app + builder_router"
```

---

### Task 3: Add the EIBuilder uvicorn entrypoint

**Files:**
- Create: `agent_builder/EIBuilder.py`
- Create: `agent_builder/EIBuilder_base.py`
- Test: `agent_builder/tests/test_eibuilder.py`

**Interfaces:**
- Consumes: `from agent_builder.adapter.config_bridge import settings` (has `settings.server.host`/`port`/`workers`/`nginx_load_balancing`/`https`/`tls_*` — see `ServerSettings` in `config_bridge.py`); `app` at `agent_builder.serve.server_fastapi:app`.
- Produces: a CLI `python -m agent_builder.EIBuilder --help` and a `main()` that runs uvicorn on `agent_builder.serve.server_fastapi:app` at `settings.server.host:settings.server.port`.

- [ ] **Step 1: Write the failing test**

Create `agent_builder/tests/test_eibuilder.py`:
```python
"""Tests for the EIBuilder entrypoint — CLI surface + import safety."""

import subprocess
import sys


VENV_PY = "agent-runtime/.venv/Scripts/python.exe"


def test_eibuilder_module_imports():
    import importlib

    mod = importlib.import_module("agent_builder.EIBuilder_base")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_eibuilder_cli_help_exits_zero():
    # `--help` must exit 0 and mention --host/--port/--log-level.
    proc = subprocess.run(
        [VENV_PY, "-m", "agent_builder.EIBuilder", "--help"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr
    assert "--host" in proc.stdout
    assert "--port" in proc.stdout
    assert "--log-level" in proc.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_eibuilder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_builder.EIBuilder_base'`

- [ ] **Step 3: Write minimal implementation**

Create `agent_builder/EIBuilder_base.py` (mirrors `agent_runtime/agent_runtime/EIStart_base.py`):
```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""uvicorn launcher for the agent_builder service (mirrors EIStart_base)."""

import os

import uvicorn

from agent_builder.adapter.config_bridge import settings


def _get_workers() -> int:
    """计算 uvicorn worker 数量。优先 GUNICORN_WORK_NUM；未设置回退 CPU+1；
    nginx 负载均衡时强制 1。"""
    if getattr(settings.server, "nginx_load_balancing", False):
        return 1
    configured = getattr(settings.server, "workers", None)
    if configured is not None:
        return configured
    return (os.cpu_count() or 1) + 1


def get_ssl_cert_config() -> dict:
    """读取 HTTPS 配置（参考 agent_runtime EIStart_base）。"""
    if not getattr(settings.server, "https", False):
        return {}
    password = (
        settings.server.tls_key_password.encode("utf-8")
        if getattr(settings.server, "tls_key_password", "")
        else None
    )
    return {
        "ssl_certfile": getattr(settings.server, "tls_cert_path", None),
        "ssl_keyfile": getattr(settings.server, "tls_key_path", None),
        "ssl_keyfile_password": password,
        "ssl_ciphers": getattr(settings.server, "tls_ciphers", None),
    }


def main():
    host = settings.server.host
    port = settings.server.port
    log_level = getattr(settings.server, "log_level", "info").lower()

    app_path = "agent_builder.serve.server_fastapi:app"
    ssl_config = get_ssl_cert_config()

    uvicorn.run(
        app_path,
        host=host,
        port=port,
        log_level=log_level,
        workers=_get_workers(),
        **ssl_config,
    )


if __name__ == "__main__":
    main()
```

> **Note:** `config_bridge.ServerSettings` currently defines `host`/`port`/`https` (verify `tls_*` fields exist by grepping `config_bridge.py` — if absent, `get_ssl_cert_config` returns `{}` because `https` defaults false; that is fine for the initial HTTP-only builder image). If you find `ServerSettings` lacks `workers`/`log_level`/`nginx_load_balancing`, the `getattr(..., default)` calls make this safe — no edit needed.

Create `agent_builder/EIBuilder.py` (mirrors `agent_runtime/agent_runtime/EIStart.py`):
```python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""CLI entry point for the agent_builder service."""

import argparse

from agent_builder.EIBuilder_base import main as start_server


def main():
    parser = argparse.ArgumentParser(
        description="agent_builder microservice (prompt/mmapo/n2l)"
    )
    parser.add_argument("--host", default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Bind port")
    parser.add_argument("--log-level", default=None, help="Log level")

    args = parser.parse_args()

    from agent_builder.adapter.config_bridge import settings

    if args.host is not None:
        settings.server.host = args.host
    if args.port is not None:
        settings.server.port = args.port
    if args.log_level is not None:
        # ServerSettings may not have log_level; set via env-style attr if present.
        if hasattr(settings.server, "log_level"):
            settings.server.log_level = args.log_level

    start_server()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_eibuilder.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add agent_builder/EIBuilder.py agent_builder/EIBuilder_base.py agent_builder/tests/test_eibuilder.py
git commit -m "feat(agent_builder): add EIBuilder uvicorn entrypoint (port via SERVER_PORT)"
```

---

### Task 4: Strip agent_runtime's 3 hosting edges

**Files:**
- Modify: `agent-runtime/agent_runtime/serve/server.py` (lines 62-70, 109, 192-198)
- Modify: `agent-runtime/agent_runtime/serve/apis/orchestration.py` (lines 36, 329-347)
- Test: `agent_builder/tests/test_runtime_decoupled.py`

**Interfaces:**
- Consumes: none new.
- Produces: an agent_runtime that no longer imports `agent_builder` at all.

- [ ] **Step 1: Write the failing test**

Create `agent_builder/tests/test_runtime_decoupled.py`:
```python
"""Assert agent_runtime no longer imports agent_builder (full decoupling)."""

import subprocess

VENV_PY = "agent-runtime/.venv/Scripts/python.exe"


def test_runtime_server_imports_without_agent_builder():
    # agent_runtime.serve.server must import cleanly (no removed-name errors).
    proc = subprocess.run(
        [VENV_PY, "-c", "import agent_runtime.serve.server"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr


def test_no_agent_builder_imports_in_runtime_source():
    # Assert no real import of the agent_builder package remains.
    # (Substring "agent_builder" alone is a false positive — agent_runtime has
    # an unrelated local `agent_builder_error_handler` function and an
    # `AgentBuilderError` exception. We check actual import statements instead.)
    import pathlib
    import re

    runtime_root = pathlib.Path("agent-runtime/agent_runtime")
    pattern = re.compile(r"^\s*(from\s+agent_builder|import\s+agent_builder)\b", re.M)
    hits = []
    for p in runtime_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        for m in pattern.finditer(text):
            hits.append(f"{p}: {m.group(0).strip()}")
    assert not hits, f"agent_runtime still imports agent_builder: {hits}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_runtime_decoupled.py -v`
Expected: FAIL — `test_no_agent_builder_references_in_runtime_source` lists `server.py` and `orchestration.py`.

- [ ] **Step 3: Strip orchestration.py (n2l endpoint + import)**

In `agent-runtime/agent_runtime/serve/apis/orchestration.py`:

- Delete line 36:
  ```python
  from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat
  ```
- Delete the entire `chat_n2l` endpoint (the `@execution_app.post("/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat")` function, ~lines 329-347 including the `chat_n2l` `async def` and its body through the `return chat_response` line).
- Scan the file for any remaining use of `N2LRequestBody`/`_n2l_json_wapper`/`_chat` and confirm none remain (they were only used by the deleted endpoint). If `json`/`StreamingResponse`/`request` imports become unused, leave them — other endpoints in the file still use them; verify with the import in Step 4.

- [ ] **Step 4: Strip server.py (Flask mount import + ContextManager lifespan)**

In `agent-runtime/agent_runtime/serve/server.py`:

- Delete lines 69-70 (the comment + import):
  ```python
  # 导入 Flask prompt 子应用（agent_builder 构建侧）
  from agent_builder.app import app as prompt_manage_app
  ```
- Change `apps_map` (line 109) from:
  ```python
  apps_map = [execution_app, user_variable_router, memory_internal_router, prompt_manage_app]
  ```
  to:
  ```python
  apps_map = [execution_app, user_variable_router, memory_internal_router]
  ```
- Delete the `ContextManager` lifespan block (~lines 192-198):
  ```python
      # 初始化提示词优化任务的数据库持久化存储
      try:
          from agent_builder.prompt.tune.base.context_manager import ContextManager
          ContextManager().set_store()
          logger.info("Prompt optimization store initialized")
      except Exception as e:
          logger.warning(f"Prompt optimization store init failed (non-critical): {e}")
  ```
- Leave `AgentBuilderError` (the agent_runtime exception, not the agent_builder package) and its handler untouched — `agent_runtime.common.exception.errors.AgentBuilderError` is unrelated to the `agent_builder` package despite the name.

- [ ] **Step 5: Run test to verify it passes (acceptance gate)**

Run: `agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_runtime_decoupled.py -v`
Expected: PASS (2 tests). This confirms `grep`-equivalent decoupling AND that `agent_runtime.serve.server` still imports cleanly.

- [ ] **Step 6: Commit**

```bash
git add agent-runtime/agent_runtime/serve/server.py agent-runtime/agent_runtime/serve/apis/orchestration.py agent_builder/tests/test_runtime_decoupled.py
git commit -m "refactor(agent_runtime): remove 3 agent_builder hosting edges (mount, lifespan, n2l)"
```

---

### Task 5: Docker — new studio-builder image; lean studio-runtime

**Files:**
- Create: `docker/studio-builder/Dockerfile`
- Modify: `docker/studio-runtime/Dockerfile` (drop `COPY agent_builder/`)
- Modify: `docker/build.sh`
- Modify: `docker/build_arm.sh`

**Interfaces:** none (build infra).

- [ ] **Step 1: Inspect the runtime Dockerfile's builder-relevant lines**

Run:
```bash
grep -n "agent_builder\|agent_runtime\|agent-core\|jiuwen\|requirements.txt\|CMD\|ENTRYPOINT\|FROM\|BASE_IMAGE" docker/studio-runtime/Dockerfile
```
Capture the exact `COPY` lines and base-image pattern to mirror.

- [ ] **Step 2: Create the studio-builder Dockerfile**

Create `docker/studio-builder/Dockerfile` (mirror `studio-runtime/Dockerfile` but omit `agent_runtime/` and its execution-only deps):
```dockerfile
ARG BASE_IMAGE
FROM $BASE_IMAGE

# Same user setup as studio-runtime
RUN groupadd -g 1000 service && useradd -u 1000 -g service -s /bin/bash -m service

ENV SERVICE_HOME=/opt/cloud/agent-builder
ENV PACKAGES_HOME=/usr/local/lib/python3.11/site-packages
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib64

WORKDIR $SERVICE_HOME

# Mirror the apt mirror config + base packages from studio-runtime
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
    fi \
    && apt-get update && apt-get install -y curl tar unzip net-tools wget vim procps gawk hostname sed coreutils findutils bash \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Builder requirements (Flask/FastAPI/uvicorn + jiuwen client deps)
COPY agent_builder/requirements.txt $SERVICE_HOME/app/agent_builder/requirements.txt
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip3 config set global.trusted-host mirrors.aliyun.com \
    && pip3 install -r $SERVICE_HOME/app/agent_builder/requirements.txt

# agent-core (jiuwen/openjiuwen) — same as runtime
COPY agent-core/ $SERVICE_HOME/app/agent-core/
RUN pip3 install $SERVICE_HOME/app/agent-core/ \
    && rm -rf $SERVICE_HOME/app/agent-core/

# Builder source + shared jiuwen prompt templates
COPY agent_builder/ $SERVICE_HOME/app/agent_builder/
COPY jiuwen/ $SERVICE_HOME/app/jiuwen/

WORKDIR $SERVICE_HOME/app

RUN mkdir -p /opt/cloud/logs/agent-builder/run \
    && touch /opt/cloud/logs/agent-builder/run/agent-builder.pid \
    && chown -R service:service /opt/cloud/logs $SERVICE_HOME \
    && chmod 700 $SERVICE_HOME/..

USER service

ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=31015

CMD ["/bin/bash", "-c", "cd ${SERVICE_HOME}/app; exec python -m agent_builder.EIBuilder --host ${SERVER_HOST} --port ${SERVER_PORT}"]
```

> **Note:** Verify the `agent_builder/requirements.txt` already includes `uvicorn`, `fastapi`, `redis`, `aiohttp`, `pydantic` — it does (confirmed in spec). If the build reports a missing dep that agent_runtime pulls in via its own `requirements.txt`, add that pin to `agent_builder/requirements.txt`.

- [ ] **Step 3: Lean the studio-runtime Dockerfile (drop agent_builder COPY)**

In `docker/studio-runtime/Dockerfile`, delete the line:
```dockerfile
COPY agent_builder/ $SERVICE_HOME/app/agent_builder/
```
Leave the `agent_runtime/`, `jiuwen/`, `tests/`, `bin/` COPYs intact. (If a later `RUN` references `agent_builder`, also remove that — none found in the tail inspected.)

- [ ] **Step 4: Add builder image build to build.sh / build_arm.sh**

Open `docker/build.sh`. Find the section that stages `agent_builder/`, `agent_runtime/`, `jiuwen/`, `agent-core/` into `docker/studio-runtime/` and builds `AgentBuilder.tar.gz`. Add a parallel block that stages `agent_builder/`, `jiuwen/`, `agent-core/` into `docker/studio-builder/` and builds a `StudioBuilder.tar.gz`:

```bash
# Stage builder image context
STAGE_BUILDER=docker/studio-builder
mkdir -p "$STAGE_BUILDER"
cp -r agent_builder "$STAGE_BUILDER/"
cp -r jiuwen "$STAGE_BUILDER/"
cp -r agent-core "$STAGE_BUILDER/" 2>/dev/null || true
cp agent_builder/requirements.txt "$STAGE_BUILDER/agent_builder/requirements.txt"

# Build builder image
docker build -t studio-builder:"$TAG" -f "$STAGE_BUILDER/Dockerfile" "$STAGE_BUILDER"
docker save studio-builder:"$TAG" -o StudioBuilder.tar.gz
```

Mirror the same in `docker/build_arm.sh` (ARM tag), producing `StudioBuilder-arm64.tar.gz`. Preserve the existing runtime build block untouched.

- [ ] **Step 5: Lint the Dockerfiles**

Run:
```bash
docker build --check docker/studio-builder 2>/dev/null || docker run --rm -v "$(pwd)/docker/studio-builder:/ctx" hadolint/hadolint:latest-alpine Dockerfile 2>/dev/null || echo "no hadolint; skipping lint"
```
Expected: no hard errors (a missing hadolint is acceptable). If `docker build --check` is unavailable, proceed — Task 6 does the real build.

- [ ] **Step 6: Commit**

```bash
git add docker/studio-builder/Dockerfile docker/studio-runtime/Dockerfile docker/build.sh docker/build_arm.sh
git commit -m "build: add studio-builder image; drop agent_builder from studio-runtime image"
```

---

### Task 6: End-to-end smoke test (builder boots; runtime unaffected)

**Files:** none (verification only).

- [ ] **Step 1: Boot the builder service locally**

Run (background, with Redis reachable — if Redis is not up, lifespan warns and continues):
```bash
SERVER_HOST=127.0.0.1 SERVER_PORT=31015 agent-runtime/.venv/Scripts/python.exe -m agent_builder.EIBuilder --host 127.0.0.1 --port 31015
```
Expected: uvicorn logs `Uvicorn running on http://127.0.0.1:31015`, `Prompt optimization store initialized` (or warn), `Redis connection check passed` (or warn). No traceback.

- [ ] **Step 2: Curl health**

Run:
```bash
curl -s http://127.0.0.1:31015/v1/health
```
Expected: `the health is good`

- [ ] **Step 3: Curl a Flask (prompt) route to confirm WSGIMiddleware mount works**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:31015/flask/health 2>/dev/null || \
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:31015/v1/prompt/__nonexistent__
```
Expected: a non-502/non-500 status (Flask responds, even if 404). A 404 here proves the Flask app is mounted and routing through WSGIMiddleware.

- [ ] **Step 4: Stop the builder**

`Ctrl-C` the uvicorn process, or:
```bash
pkill -f "agent_builder.EIBuilder" || true
```

- [ ] **Step 5: Confirm agent_runtime still boots (no agent_builder dependency)**

Run:
```bash
agent-runtime/.venv/Scripts/python.exe -c "import agent_runtime.serve.server as s; print('runtime imports OK, app=', type(s.app).__name__)"
```
Expected: `runtime imports OK, app= FastAPI` — no `ModuleNotFoundError` for `agent_builder`.

- [ ] **Step 6: Run the full new test suite**

Run:
```bash
agent-runtime/.venv/Scripts/python.exe -m pytest agent_builder/tests/test_n2l_api.py agent_builder/tests/test_server_fastapi.py agent_builder/tests/test_eibuilder.py agent_builder/tests/test_runtime_decoupled.py -v
```
Expected: all PASS.

- [ ] **Step 7: Build the builder Docker image (if Docker is available)**

Run:
```bash
docker build -t studio-builder:smoke -f docker/studio-builder/Dockerfile docker/studio-builder
docker run --rm -e SERVER_PORT=31015 -p 31015:31015 studio-builder:smoke &
sleep 8 && curl -s http://127.0.0.1:31015/v1/health && pkill -f "agent_builder.EIBuilder"
```
Expected: `the health is good`. If Docker is unavailable in this environment, mark this step skipped and rely on Steps 1-6.

- [ ] **Step 8: Commit final state (if any test/docs touched)**

```bash
git add -A
git commit -m "test: end-to-end smoke for agent_builder microservice extraction" 2>/dev/null || echo "nothing to commit"
```

---

## Self-Review Notes

- **Spec coverage:** spec §1 (server_fastapi.py) → Tasks 2; §2 (n2l_api.py) → Task 1; §3 (EIBuilder) → Task 3; §4 (strip 3 edges) → Task 4; §5 (Docker) → Task 5; §6 (config/infra) → embedded in Task 5/6 env vars; §7 (error handling) → Task 2 exception handlers; §8 (testing) → Task 6. Resolved points #1-4 → Global Constraints + Tasks 2/4/5. No spec gap.
- **Placeholder scan:** none; all code blocks complete. `ServerSettings` field uncertainty is handled with `getattr` defaults (Task 3 note), not TODOs.
- **Type/name consistency:** `builder_router` (Task 1) consumed by Task 2 import — match. `app` module-level (Task 2) consumed as `agent_builder.serve.server_fastapi:app` (Task 3) — match. `main`/`start_server` (Task 3) — match. `_ping_redis`/`_init_prompt_store` internal — no cross-task consumers. `apps_map` shape `[builder_router, prompt_manage_app]` matches spec.
