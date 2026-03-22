#!/usr/bin/env python3
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.sandbox import get_sandbox_class
from app.sandbox_config import SandboxConfig
from app.dependency_manager import DependencyManager
from app.util import get_base_code, parse_result

app = FastAPI()

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

ENABLE_LINUX_SANDBOX = os.getenv("ENABLE_LINUX_SANDBOX", "false").lower() == "true"

sandbox_type = None if (sys.platform == "linux" and ENABLE_LINUX_SANDBOX) else 'local'
sandbox_config = SandboxConfig()
dep_mgr = DependencyManager()
sandbox_class = get_sandbox_class(sandbox_type, sandbox_config)
sandbox_class.pre_init(sandbox_config)


@app.post("/run")
async def run_code(request: Request):
    data = await request.json() or {}
    lang = data.get("language", "python")
    code = data.get("code", "")
    inputs = data.get("inputs", {})
    timeout = float(data.get("timeout", 10))

    if lang not in ("python", "javascript"):
        return JSONResponse({"output": {"return": None, "error": f"Unsupported language: {lang}"}})

    sandbox = sandbox_class(sandbox_config, dep_mgr)
    base_code = get_base_code(inputs, lang)
    exec_res = sandbox.run(code, base_code, lang, timeout)

    if exec_res.retcode == 0:
        result = {"return": parse_result(exec_res.stdout), "error": None}
    else:
        result = {"return": "", "error": exec_res.stderr}
    return result


@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok"})


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
