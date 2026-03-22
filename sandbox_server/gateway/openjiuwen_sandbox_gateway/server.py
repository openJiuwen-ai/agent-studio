#!/usr/bin/env python3
import os
import sys
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openjiuwen_sandbox_gateway.app.gateway import remote_server

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

app = FastAPI()


@app.post("/run")
async def run_code(request: Request):
    data = await request.json() or {}
    lang = data.get("language", "python")
    code = data.get("code", "")
    inputs = data.get("inputs", {})
    timeout = float(data.get("timeout", 10))
    session = data.get("session", "default")

    if lang in ["python", "javascript"]:
        result = await remote_server(lang, code, inputs, session, timeout)
    else:
        result = {"return": None, "error": f"Unsupported language: {lang}"}

    return JSONResponse({"output": result})


@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok"})

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8188))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()