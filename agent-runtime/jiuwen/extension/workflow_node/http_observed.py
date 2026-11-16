# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""EI.http 节点的可观测性包装组件。

背景：HTTP 组件调用 aiohttp 得到 4xx/5xx 时，按协议语义是"合法响应"，openjiuwen
的 HTTPRequestExecutable 会正常返回 {ok:false, statusCode:500, body:...} 的业务
结果，错误事实不会进入 trace 的 error 语义（Jaeger 上无显示）。

本 wrapper 不改任何业务行为：父类完全照常返回结果、流程与节点输出不变；仅在
返回结果为 ok=false（业务失败）时，额外向 trace 上报一条 business_error 标记，
由 openjiuwen tracer_otel 扩展将该 span 标红并保留错误信息（纯观测增强）。
"""

from openjiuwen.core.common.logging import workflow_logger

from openjiuwen.core.workflow.components.tool.http.http_request_component import (
    HTTPRequestComponent,
    HTTPRequestExecutable,
)


class HttpObservedExecutable(HTTPRequestExecutable):
    """包装 HTTP 请求执行体：业务失败仅上报标记，不改变结果与流程。"""

    async def invoke(self, inputs, session, context):
        result = await super().invoke(inputs, session, context)
        if isinstance(result, dict) and result.get("ok") is False:
            await self._report_business_error(session, result)
        return result

    @staticmethod
    async def _report_business_error(session, result):
        try:
            body = result.get("body")
            if isinstance(body, bytes):
                body_preview = body[:500].decode("utf-8", errors="replace")
            elif isinstance(body, str):
                body_preview = body[:500]
            else:
                body_preview = str(body)[:500]
            raw_url = str(result.get("url") or "")
            try:
                from urllib.parse import urlsplit, urlunsplit

                parts = urlsplit(raw_url)
                # 脱敏：仅保留 scheme/host/port/path，丢弃 query、fragment 与
                # netloc 中的 userinfo（user:pass@host），防签名/凭据随 trace
                # 落库。注意不能用 parts.hostname 重建 netloc——该属性会剥掉
                # IPv6 字面量的方括号（[::1]:8080 会变成非法的 ::1:8080），故
                # 按最后一个 "@" 切掉 userinfo、netloc 其余部分原样保留。
                netloc = parts.netloc.rsplit("@", 1)[-1]
                raw_url = urlunsplit((parts.scheme, netloc, parts.path, "", ""))
            except Exception:
                raw_url = ""
            await session.trace(
                {
                    "business_error": {
                        "status_code": result.get("statusCode"),
                        "body": body_preview,
                        "url": raw_url,
                    }
                }
            )
        except Exception as exc:  # 观测失败不得影响业务流转
            workflow_logger.debug(
                "HttpObservedExecutable report business_error failed: %s", exc
            )


class HttpObservedComponent(HTTPRequestComponent):
    """EI.http 节点组件：to_executable 返回业务失败可观测的执行体。"""

    def to_executable(self) -> HttpObservedExecutable:
        return HttpObservedExecutable(self.config)