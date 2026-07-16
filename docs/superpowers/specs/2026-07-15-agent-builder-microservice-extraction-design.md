# Design: Extract agent_builder as an independent microservice

**Date:** 2026-07-15
**Approach:** A — Surgical mirror (replicate `agent_runtime/serve/server.py` pattern for agent_builder; strip agent_runtime's 3 hosting edges; new `studio-builder` Docker image).

## Goal

Pull `agent_builder` out of the `agent_runtime` process into its own independently-deployed microservice (own Docker image, own port), while preserving the FastAPI-shell-wrapping-Flask pattern that `agent_runtime/serve/server.py` already uses (`apps_map` with `# FastAPI routers must be included BEFORE Flask app mount`).

## Verified dependency map

The coupling is **one-way**. agent_builder has zero runtime imports from agent_runtime:

- `agent_builder/adapter/*_bridge.py` (`config_bridge`, `crypto_bridge`, `logger_rt_bridge`, `model_bridge`, `redis_bridge`) are **full replicas** of agent_runtime modules, not imports.
- `agent_builder/agent_evolving/agent_rl/.../adaptor.py` imports `agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.agent_runtime` — a **local module**, not the agent-runtime package.
- `agent_builder/nl_to_agent/storage/history.py` references "agent_runtime's Redis config" in comments but reads it through `agent_builder.adapter.config_bridge` (the replica), not via `import agent_runtime`.

agent_runtime hosts agent_builder through exactly **3 edges** (all in `serve/`):

| Edge | File:line | What |
|---|---|---|
| 1 | `agent_runtime/serve/server.py:70` | `from agent_builder.app import app as prompt_manage_app` — mounts Flask app via `WSGIMiddleware` |
| 2 | `agent_runtime/serve/server.py:194` | `from agent_builder.prompt.tune.base.context_manager import ContextManager` — `ContextManager().set_store()` in lifespan |
| 3 | `agent_runtime/serve/apis/orchestration.py:36` | `from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat` — the `/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat` (n2l) endpoint |

**n2l path is self-contained:** `_chat` uses `agent_builder.nl_to_agent.agent_creator.controller.Executor`, which imports only from `agent_builder.*` and `agent_builder.adapter.jiuwen_bridge` — it does **not** pull in openjiuwen's `Runner`/`Checkpointer`/`SysOperation`. Therefore agent_builder's lifespan is much lighter than agent_runtime's.

## Architecture after extraction

```
┌──────────────────────────┐        ┌──────────────────────────┐
│  studio-runtime image    │        │  studio-builder image    │
│  (port 31014)            │        │  (port 31015)            │
│                          │        │                          │
│  EIStart.py → uvicorn    │        │  EIBuilder.py → uvicorn  │
│  agent_runtime.serve     │        │  agent_builder.serve     │
│  .server:app             │        │  .server_fastapi:app     │
│                          │        │                          │
│  FastAPI routers:        │        │  FastAPI router:         │
│   execution_app          │        │   builder_router (n2l)   │
│   user_variable_router   │        │  Flask (WSGIMiddleware): │
│   memory_internal_router │        │   prompt_manage_app      │
│                          │        │    (prompt + mmapo bp)   │
└──────────────────────────┘        └──────────────────────────┘
            │                                   │
            └──────────┬────────────────────────┘
                       │  shared infra (no inter-service HTTP)
              ┌────────┴────────┐
              │  Redis / OBS / DB│
              └─────────────────┘
```

The two services are **fully independent at runtime** — they share Redis/OBS/DB as common infrastructure and make no HTTP calls to each other. The only former cross-call (n2l) moves into the builder service.

## Components

### 1. `agent_builder/serve/server_fastapi.py` (new)

Mirrors `agent_runtime/serve/server.py`. Contents:

**Top-level patches:** none from agent_runtime. agent_builder uses its own `init_logger` (already invoked in `agent_builder/app.py`) and its own trace-id mechanism. No `JiuWenCrypt` patch (n2l/prompt doesn't touch jiuwen OBS). No `init_prompt`/`component_class_pool` registration (Executor path doesn't need them).

**`apps_map`:**
```python
from agent_builder.app import app as prompt_manage_app   # single Flask app
from agent_builder.serve.apis.n2l_api import builder_router

# FastAPI routers must be included BEFORE Flask app mount (Flask catches all routes)
apps_map = [builder_router, prompt_manage_app]
```
`prompt_manage_app` is the single Flask app built by `agent_builder.app` — it already has both `prompt.manager` and `mmapo.manager` blueprints registered (via `ServerApp` in `agent_builder/serve/server.py`). `instance_app()` iterates `apps_map` and branches on `isinstance(i, Flask)` (Flask → `app.mount("/", WSGIMiddleware(i))`, else → `app.include_router(i)`) — same pattern, and same single-Flask-app shape, as agent_runtime's `[execution_app, user_variable_router, memory_internal_router, prompt_manage_app]`. FastAPI `builder_router` must precede the Flask app so its routes aren't swallowed by the Flask catch-all mount.

**`lifespan` (light subset):**
- `agent_builder.prompt.tune.base.context_manager.ContextManager().set_store()` (prompt-optimization DB store) — needed.
- Best-effort Redis ping (fail-fast at startup): build a sync `redis.Redis`/`RedisCluster` from `agent_builder.adapter.config_bridge` settings and `ping()`, warn-and-continue on failure. (n2l `history.py` creates its client lazily from the same `config_bridge` settings, so this ping only validates config.)
- **No** `configure_log_config`, **no** S3 (grep confirms agent_builder has zero `S3StorageProvider`/`get_storage_provider` usage), **no** checkpointer, **no** `init_ltm`, **no** OTEL, **no** SysOperation.

**`instance_app(config)`:**
- `FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)`.
- `@app.middleware("http")` trace-id middleware: `set_thread_session(request.headers.get("TraceID", ""))` (from `agent_builder.adapter.logger_bridge`). Covers FastAPI router routes; Flask routes also set it via Flask's existing `_set_trace_id_from_request` before_request (double-set harmless).
- `normalize_flask_path` middleware — same `/v1/prompt/` → `/flask` rewrite (prompt blueprint keeps `url_prefix="/flask"`).
- Loop `apps_map`: `if isinstance(i, Flask): app.mount("/", WSGIMiddleware(i)) else: app.include_router(i)`.
- Exception handlers: `JiuWenException` → JSON 500 with `get_thread_session()` trace id; generic `Exception` → `internal_error`. (Mirror agent_runtime's handler shape, but read trace id from `get_thread_session()` instead of `request.state.*`.)
- module-level `app = instance_app()`.

### 2. `agent_builder/serve/apis/n2l_api.py` (new)

FastAPI APIRouter holding the **moved** n2l endpoint + a health endpoint:
```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from agent_builder.nl_to_agent.nl2 import N2LRequestBody, _n2l_json_wapper, _chat

builder_router = APIRouter(tags=["builder"])

@builder_router.get("/v1/health")
async def health():
    return "the health is good"

@builder_router.post("/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat")
async def chat_n2l(project_id: str, agent_type: str, cid: str,
                   body: N2LRequestBody, request: Request) -> StreamingResponse:
    payload = _n2l_json_wapper(project_id, agent_type, cid,
                               body.model_dump(exclude_unset=True), request)
    return await _chat(payload)
```
`N2LRequestBody`, `_n2l_json_wapper`, `_chat` already live in `agent_builder.nl_to_agent.nl2` — only the endpoint *registration* moves out of `orchestration.py`.

### 3. `agent_builder/EIBuilder.py` + `agent_builder/EIBuilder_base.py` (new)

Mirror `EIStart.py` / `EIStart_base.py`:
- `EIBuilder.py`: argparse (`--host`, `--port`, `--log-level`) → set on builder settings → `start_server()`.
- `EIBuilder_base.py`: `uvicorn.run("agent_builder.serve.server_fastapi:app", host=..., port=..., workers=..., **ssl_config)` — same worker/SSL logic as `EIStart_base.py`. Default port **31015**.
- Builder reads host/port/Redis/OBS/DB from `agent_builder/serve/settings.yaml` + `agent_builder/config.yaml` (already present).

### 4. Strip agent_runtime's 3 edges (full decoupling)

- `agent_runtime/serve/server.py`:
  - Remove line 70 `from agent_builder.app import app as prompt_manage_app`.
  - `apps_map` → `[execution_app, user_variable_router, memory_internal_router]` (drop `prompt_manage_app`).
  - Remove the `ContextManager().set_store()` lifespan block (lines ~193-198).
- `agent_runtime/serve/apis/orchestration.py`:
  - Remove line 36 `from agent_builder.nl_to_agent.nl2 import ...`.
  - Remove the `chat_n2l` endpoint (lines ~329-347).
- **Success criterion:** `grep -rnE "^\s*(from agent_builder|import agent_builder)\b" agent-runtime/agent_runtime/ --include="*.py" | grep -v __pycache__` returns empty. (Bare-substring grep is a false positive — `agent_builder_error_handler`/`AgentBuilderError` in agent_runtime are unrelated to the package.)

### 5. Docker — new `studio-builder` image; lean `studio-runtime`

- **`docker/studio-builder/Dockerfile`** (new):
  - `FROM` same base as `studio-runtime` (reuse `Dockerfile.base`/base image).
  - `COPY agent_builder/ + jiuwen/ + agent-core/` into `$SERVICE_HOME/app/` (NOT `agent_runtime/`).
  - `pip install -r app/agent_builder/requirements.txt` + `pip install app/agent-core/`.
  - `CMD` runs `EIBuilder.py` on port 31015. No nginx LB for builder initially (single process).
  - Create a `docker/studio-builder/` staging dir mirroring `docker/studio-runtime/` layout, or build straight from repo root via build context.
- **`docker/studio-runtime/Dockerfile`** (lean): remove the `COPY agent_builder/ $SERVICE_HOME/app/agent_builder/` line — runtime image no longer carries builder source. Update `build.sh`/`build_arm.sh` staging accordingly.
- `docker/build.sh` / `build_arm.sh`: add a builder-image build step (copy `agent_builder/ jiuwen/ agent-core/` into `docker/studio-builder/` staging, build the new image). Update `AgentBuilder.tar.gz`/`AgentBuilder-arm64.tar.gz` naming as appropriate.

### 6. Config, infra, data flow

- Both services connect to the **same** Redis, OBS, DB — no inter-service HTTP.
- Builder port 31015, runtime port 31014. TLS via `agent_builder/serve/common/ssl_ctx.py`.
- Builder config source: `agent_builder/serve/settings.yaml` (host/port/connection/tls) + `agent_builder/config.yaml` (logging/prompt). The `config_bridge` replica already mirrors agent_runtime's env-var names, so the same deployment env vars work for both.

### 7. Error handling

- `server_fastapi.py` registers FastAPI exception handlers mirroring agent_runtime's: `JiuWenException` (from `agent_builder.adapter.exception_bridge`) → `{"error": {...}}` JSON 500 with trace_id; generic `Exception` → `{"error": {"code": "internal_error", ...}}`.
- n2l's `_chat` already wraps its own errors into an SSE error stream (`_error_sse_generator`); the FastAPI handler is the outer fallback.

### 8. Testing

- **Builder image:** builds cleanly; `curl http://localhost:31015/v1/health` → `the health is good`.
- **n2l:** POST a representative `N2LRequestBody` payload to `/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat` → returns an SSE stream.
- **agent_runtime regression:** `python -c "import agent_runtime.serve.server"` succeeds; runtime boots on 31014; `grep -rn agent_builder agent-runtime/ --include="*.py"` empty.
- **Existing tests:** `agent_builder/tests/` pass; `agent-runtime` tests unaffected.

## Resolved verification points

1. **Builder port: 31015** — confirmed.
2. **n2l/prompt touches jiuwen OBS? / needs `init_prompt`/`component_class_pool`?** — confirmed not needed; builder lifespan skips them (Executor path imports only `agent_builder.*` + `jiuwen_bridge`).
3. **Logging / trace-id — use agent_builder's own, do NOT replicate `logging_context`.** Inspection of `logging_context.py` showed it is mostly workflow-execution trace-masking (`mask_secret_envs_in_obj`, `apply_template_masking_patch`, `mask_debug_data`, observer callbacks) the builder doesn't use, and the two candidate helpers (`install_request_id_log_record_factory`, `install_log_formatter_patch`) depend on `_request_ctx` + `RequestContextMiddleware` from `agent_runtime.context.*` — replicating them would drag in the whole ContextVar chain. agent_builder already has its own trace-id mechanism (`set_thread_session`/`get_thread_session` in `agent_builder.adapter.logger_bridge`, reading the `TraceID` header) and its own `init_logger` (a no-op today). So `server_fastapi.py`:
   - does **not** import `RequestContextMiddleware`, `_request_ctx`, `install_request_id_log_record_factory`, `install_log_formatter_patch`, `COMMON_LOG_FORMAT`, or `configure_log_config` from agent_runtime;
   - adds its own `@app.middleware("http")` that calls `set_thread_session(request.headers.get("TraceID", ""))` (covers FastAPI router routes; Flask routes also get it via Flask's existing `_set_trace_id_from_request` before_request — double-set is harmless);
   - exception handlers read `get_thread_session()` for the trace id instead of `request.state.execution_id`/`request_id`.
4. **Builder-specific startup in `docker/studio-runtime/bin/start.sh`/`init.sh`?** — confirmed none exists; no cleanup needed there beyond dropping the `agent_builder/` COPY from the runtime Dockerfile.

## Out of scope / follow-ups

- Approach B (extract shared lifespan/patch module) — possible future cleanup if duplication bothers; not needed now.
- nginx load-balancing for builder — add later if multi-instance needed.
- The `studio-runtime` image's `bin/start.sh`/`init.sh` may reference agent_builder startup; verify no builder-specific init remains there after the lean split.
