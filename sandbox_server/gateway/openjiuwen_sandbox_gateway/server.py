#!/usr/bin/env python3
import os
import sys
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.sandbox import SandboxConfig, get_sandbox
from app.util import get_base_code, parse_result
from openjiuwen_sandbox_gateway.app.gateway import remote_python, remote_javascript


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

ENABLE_LINUX_SANDBOX = (os.getenv("ENABLE_LINUX_SANDBOX", "false").lower() == "true")

app = FastAPI()

arch = sys.platform
if arch == "linux" and ENABLE_LINUX_SANDBOX:
    config = SandboxConfig.init_from_file(os.path.join(os.path.dirname(__file__), './conf/sandbox_config.yaml'))


@app.post("/run")
async def run_code(request: Request):
    data = await request.json() or {}

    if arch == "linux" and ENABLE_LINUX_SANDBOX:
        result = await run_sandbox(data)
    else:
        result = await run_process(data)
    return JSONResponse({"output": result})


async def run_sandbox(data: dict):
    lang = data.get("language", "python")
    code = data.get("code", "")
    inputs = data.get("inputs", {})
    timeout = float(data.get("timeout", 10))
    session = data.get("session", "default")

    if lang != "python" and lang != "javascript":
        result = {"return": None, "error": f"Unsupported language: {lang}"}

    sandbox = get_sandbox(config)
    base_code = get_base_code(inputs, lang)
    exec_res = sandbox.run(code, base_code, lang, timeout)

    if exec_res.retcode == 0:
        result = {"return": parse_result(exec_res.stdout), "error": None}
    else:
        result = {"return": "", "error": exec_res.stderr}
    return result


async def run_process(data: dict):
    lang = data.get("language", "python")
    code = data.get("code", "")
    inputs = data.get("inputs", {})
    timeout = float(data.get("timeout", 10))
    session = data.get("session", "default")

    if lang == "python":
        result = await remote_python(code, inputs, session, timeout)
    elif lang == "javascript":
        result = await remote_javascript(code, inputs, session, timeout)
    else:
        result = {"return": None, "error": f"Unsupported language: {lang}"}
    return result


@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok"})

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8188))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()