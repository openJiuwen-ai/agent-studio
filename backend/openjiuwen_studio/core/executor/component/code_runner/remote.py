#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import os
import textwrap
from typing import Any, Dict
import httpx

from openjiuwen_studio.core.executor.component.code_runner.base import CodeRunner


class RemoteCodeRunner(CodeRunner):
    def __init__(self, code_sandbox_url: str) -> None:
        self.code_sandbox_url: str = code_sandbox_url

    async def run(self, code_language: str, code_str: str, timeout: float, params: Dict[str, Any]) -> Any:
        dedented_code = textwrap.dedent(code_str)
        payload = {"language": code_language, "code": dedented_code, "inputs": params, "timeout": timeout}
        
        # Use AsyncClient for non-blocking HTTP requests
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.code_sandbox_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout
            )
        
        response.raise_for_status()
        response_data = response.json().get("output")

        if response_data.get("error") is not None:
            raise RuntimeError(f"Sandbox run error: {response_data['error']}")

        result_dict = response_data.get("return")
        return result_dict

remote_code_runner: RemoteCodeRunner = RemoteCodeRunner(
    os.getenv("CODE_SANDBOX_URL", default=""))
