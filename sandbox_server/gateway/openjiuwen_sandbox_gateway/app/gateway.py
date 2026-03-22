#!/usr/bin/env python3
import os

import httpx

SANDBOX_SERVER_URL = os.getenv("SANDBOX_SERVER_URL", "http://localhost:5001/run")

TIMEOUT = 10   # 建立连接超时


async def remote_server(lang, code, inputs, session, timeout: float = 10.0):
    payload = {"session": session, "language": lang, "code": code, "timeout": timeout, "inputs": inputs or {}}
    async with httpx.AsyncClient() as cli:
        try:
            r = await cli.post(SANDBOX_SERVER_URL, json=payload,
                               timeout=httpx.Timeout(TIMEOUT + timeout, connect=TIMEOUT))
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"return": None, "error": str(e)}