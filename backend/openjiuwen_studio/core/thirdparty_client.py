# clients/deepsearch_http.py
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, Union
import httpx
from httpx._models import Response
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.common.exceptions import DeepSearchClientError

logger = logging.getLogger(__name__)


class LazyDeepSearchHttpClient:
    """
    通用的、懒加载的 DeepSearch Agent HTTP 客户端。
    支持任意 GET/POST，流式/非流式，由调用方指定。
    """
    _instance: Optional["LazyDeepSearchHttpClient"] = None
    _client: Optional[httpx.AsyncClient] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _initialize(self) -> bool:
        try:
            if not settings.deepsearch_agent_host or not settings.deepsearch_agent_port:
                raise ValueError("DeepSearch agent host/port not configured")

            base_url = f"http://{settings.deepsearch_agent_host}:{settings.deepsearch_agent_port}"
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(
                    timeout=3600.0,
                    connect=10.0
                ),
                limits=httpx.Limits(max_connections=50),
                follow_redirects=True,
                verify=False
            )

            try:
                resp = await self._client.get("/", timeout=5.0)
                resp.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as ex:
                raise RuntimeError(f"DeepSearch service unreachable: {ex}") from ex

            self._initialized = True
            logger.info(f"DeepSearch HTTP client ready. Base URL: {base_url}")
            return True
        except Exception as e:
            self._client = None
            self._initialized = False
            logger.error(f"Failed to initialize DeepSearch HTTP client: {e}")
            raise DeepSearchClientError(
                error_code=StatusCode.TASK_SPACE_THIRDPARTY_CLIENT_ERROR.code,
                message=StatusCode.TASK_SPACE_THIRDPARTY_CLIENT_ERROR.errmsg.format(msg=str(e))
            ) from e

    async def request(
        self,
        method: str,
        url: str,
        *,
        jsons: Any = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ):
        """通用 HTTP 请求方法"""
        if not self._initialized or self._client is None:
            await self._initialize()
        try:
            resp = await self._client.request(method, url, json=jsons, params=params, headers=headers)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            # Let HTTP errors bubble up so caller can handle them meaningfully
            raise
        except Exception as e:
            # 可选：重置状态，允许下次重试
            self._client = None
            self._initialized = False
            raise RuntimeError(f"DeepSearch service call failed: {e}") from e

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False

    async def stream(self, method: str, url: str, **kwargs):
        """用于流式请求，返回异步上下文管理器"""
        if not self._initialized or self._client is None:
            await self._initialize()
        return self._client.stream(method, url, **kwargs)


class DeepSearchAgentClient:
    """
    业务层 client，封装具体 API 调用。
    清晰、可读、可测试。
    """

    def __init__(self):
        self._http = LazyDeepSearchHttpClient()

    async def run_deepsearch_stream(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """流式运行深度搜索"""
        async with (await self._http.stream("POST", "/api/v1/agent/deepsearch/run/", json=payload)) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                yield line

    async def import_templates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """导入模板"""
        resp = await self._http.request("POST", "/api/v1/agent/deepsearch/template", jsons=payload)
        return resp.json()

    async def list_templates(self, space_id: str) -> list:
        """列出模板"""
        resp = await self._http.request("GET", f"/api/v1/agent/deepsearch/template/{space_id}")
        return resp.json()

    async def get_templates(self, space_id: str, template_id: int) -> list:
        """列出模板"""
        resp = await self._http.request("GET", f"/api/v1/agent/deepsearch/template/{space_id}/{template_id}")
        return resp.json()

    async def delete_templates(self, space_id: str, template_id: int) -> list:
        """列出模板"""
        resp = await self._http.request("DELETE", f"/api/v1/agent/deepsearch/template/{space_id}/{template_id}")
        return resp.json()

    async def update_templates(self, payload: Dict[str, Any]) -> list:
        """列出模板"""
        resp = await self._http.request("PUT", "/api/v1/agent/deepsearch/template", jsons=payload)
        return resp.json()

    async def create_web_searchs(self, payload: Dict[str, Any]) -> list:
        """创建web搜索引擎"""
        resp = await self._http.request("POST", "/api/v1/agent/deepsearch/web_search/", jsons=payload)
        return resp.json()

    async def get_web_search_engines(self, space_id: str, web_search_engine_id: int) -> list:
        """列出模板"""
        resp = await self._http.request("GET",
                                        f"/api/v1/agent/deepsearch/web_search/{space_id}/{web_search_engine_id}")
        return resp.json()

    async def get_web_search_engine_lists(self, space_id: str) -> list:
        """列出模板"""
        resp = await self._http.request("GET", f"/api/v1/agent/deepsearch/web_search/{space_id}")
        return resp.json()

    async def delete_web_search_engines(self, space_id: str, web_search_engine_id: int) -> list:
        """删除模板"""
        resp = await self._http.request("DELETE",
                                        f"/api/v1/agent/deepsearch/web_search/{space_id}/{web_search_engine_id}")
        return resp.json()

    async def update_web_search_engines(self, payload: Dict[str, Any]) -> list:
        """更新模板"""
        resp = await self._http.request("PUT", "/api/v1/agent/deepsearch/web_search/", jsons=payload)
        return resp.json()

    async def access_web_search_engines(self, space_id: str, web_search_engine_id: int, query: str):
        """测试模板"""
        resp = await self._http.request("POST",
                                        f"/api/v1/agent/deepsearch/web_search/{space_id}/{web_search_engine_id}",
                                        jsons=query)
        return resp.json()

    async def report_converts(self, payload: Dict[str, Any]) -> list:
        """列出模板"""
        resp = await self._http.request("POST", "/api/v1/agent/deepsearch/reports/convert", jsons=payload)
        return resp.json()


class LazyRuntimeHttpClient:
    """
    通用的、懒加载的 Runtime Agent HTTP 客户端。
    支持任意 GET/POST，流式/非流式。
    租户上下文 (x-user-id, x-space-id) 由每次请求动态传入，不固化在 client 上。
    """
    _instance: Optional["LazyRuntimeHttpClient"] = None
    _client: Optional[httpx.AsyncClient] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


    async def _initialize(self) -> bool:
        """仅初始化 httpx client，不依赖 user/space id"""
        try:
            if not settings.runtime_host or not settings.runtime_port:
                raise ValueError("Runtime agent host/port not configured")

            base_url = f"http://{settings.runtime_host}:{settings.runtime_port}"

            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(timeout=60.0, connect=10.0),
                limits=httpx.Limits(max_connections=50),
                follow_redirects=True,
                verify=False,
            )

            # 健康检查不需要租户上下文（或确保 /health 不校验）
            try:
                resp = await self._client.get("/health", timeout=5.0)
                resp.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as ex:
                raise RuntimeError(f"Runtime service unreachable: {ex}") from ex

            self._initialized = True
            logger.info(f"Runtime HTTP client ready. Base URL: {base_url}")
            return True
        except Exception as e:
            self._client = None
            self._initialized = False
            logger.error(f"Failed to initialize Runtime HTTP client: {e}")
            raise DeepSearchClientError(
                error_code=StatusCode.RUNTIME_THIRDPARTY_CLIENT_ERROR.code,
                message=StatusCode.RUNTIME_THIRDPARTY_CLIENT_ERROR.errmsg.format(msg=str(e))
            ) from e


    async def request(
        self,
        method: str,
        url: str,
        *,
        jsons: Any = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        files: Any = None,
        user_id: Optional[str] = None,
        space_id: Optional[str] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        """通用 HTTP 请求方法，支持动态注入租户上下文"""
        if not self._initialized or self._client is None:
            await self._initialize()

        # 构建本次请求的 headers
        req_headers = dict(headers) if headers else {}
        if user_id is not None:
            req_headers["x-user-id"] = user_id
        if space_id is not None:
            req_headers["x-space-id"] = space_id

        req_kw: Dict[str, Any] = dict(
            method=method,
            url=url,
            json=jsons,
            params=params,
            headers=req_headers,
            files=files,
        )
        if timeout is not None:
            req_kw["timeout"] = timeout

        try:
            resp = await self._client.request(**req_kw)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            raise RuntimeError(f"Runtime service call failed: {e}") from e


    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False


    async def stream(
        self,
        method: str,
        url: str,
        *,
        user_id: Optional[str] = None,
        space_id: Optional[str] = None,
        **kwargs
    ):
        """用于流式请求，返回异步上下文管理器"""
        if not self._initialized or self._client is None:
            await self._initialize()

        # 注入租户上下文到 headers
        headers = dict(kwargs.pop("headers", {}))
        if user_id is not None:
            headers["x-user-id"] = user_id
        if space_id is not None:
            headers["x-space-id"] = space_id

        return self._client.stream(method, url, headers=headers, **kwargs)


class RuntimeAgentClient:
    """
    业务层 Runtime client，封装具体 API 调用。
    清晰、可读、可测试。
    """

    def __init__(self):
        self._http = LazyRuntimeHttpClient()


    async def deploy_agent(
            self, payload: Dict[str, Any], user_id: str = None, space_id: str = None) -> Dict[str, Any]:
        # 构建 form-data，file 字段需要特殊处理
        file_content = json.dumps(payload.get("file"), ensure_ascii=False)
        files = {"file": ("agent_ir.json", file_content.encode("utf-8"), "text/plain")}
        params = {"name": payload.get("name", ""), "deployer_type": "local_subprocess"}

        if payload.get("deployer_type") is not None and payload.get("deployer_type") != "":
            params["deployer_type"] = payload.get("deployer_type")

        if payload.get("port") is not None:
            params["port"] = str(payload.get("port"))
        try:
            resp = await self._http.request(
                "POST",
                "/api/v1/agents/deploy",
                files=files,
                params=params,
                user_id=user_id,
                space_id=space_id,
                timeout=httpx.Timeout(
                    settings.runtime_deploy_timeout_seconds,
                    connect=settings.runtime_deploy_connect_timeout_seconds,
                ),
            )
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500:
                response_text = e.response.text.lower()
                if "address already in use" in response_text:
                    logger.error(
                        f"[DEPLOY_AGENT] Port is already in use: Port={params.get('port', '8090')}")
                raise
            else:
                logger.error(f"[DEPLOY_AGENT] HTTP error: {e.response.status_code}, body={e.response.text}")
                raise


    async def delete_deploy_agent(
            self, deployment_id: str, user_id: str = None, space_id: str = None) -> Dict[str, Any]:
        try:
            resp = await self._http.request("DELETE", f"/api/v1/agents/{deployment_id}",
                                            user_id=user_id, space_id=space_id)
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                response_text = e.response.text.lower()
                if "not found" in response_text:
                    logger.warning(
                        f"[DELETE_AGENT] Deployment not found (may already be deleted): deployment_id={deployment_id}")
                    return Response(
                        status_code=202,
                        text=f"Already deleted or not found {deployment_id} in runtime",
                    )
                else:
                    logger.error(f"[DELETE_AGENT] 404 but unexpected error: {e.response.text}")
                    raise httpx.HTTPStatusError(f"[DELETE_AGENT] 404 but unexpected error: {e}") from e
            else:
                logger.error(f"[DELETE_AGENT] HTTP error: {e.response.status_code}, body={e.response.text}")
                raise RuntimeError(f"Failed to delete agent: {e}") from e


    async def get_deploy_list(
            self, deploy_status: str = None, user_id: str = None, space_id: str = None) -> Dict[str, Any]:
        params = {}
        if deploy_status is not None and deploy_status != "":
            params["status"] = deploy_status.lower()  # status 参数需要小写
        resp = await self._http.request("GET", f"/api/v1/agents",
                               params=params, user_id=user_id, space_id=space_id)
        if resp.status_code != httpx.codes.OK:
            logger.error(f"Failed to get deploy list")
            return ""
        return resp.json()


    async def get_deploy_detail(
            self, deployment_id: str, user_id: str = None, space_id: str = None) -> Dict[str, Any]:
        try:
            resp = await self._http.request("GET", f"/api/v1/agents/{deployment_id}",
                                   user_id=user_id, space_id=space_id)
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                response_text = e.response.text.lower()
                if "not found" in response_text:
                    logger.warning(
                        f"[GET_DEPLOY_DETAIL] runtime not found: deployment_id={deployment_id}")
                    return Response(
                        status_code=202,
                        text=f"Already deleted or not found {deployment_id} in runtime",
                    )
                else:
                    logger.error(f"[GET_DEPLOY_DETAIL] 404 but unexpected error: {e.response.text}")
                    raise httpx.HTTPStatusError(f"[GET_DEPLOY_DETAIL] 404 but unexpected error: {e}") from e
            else:
                logger.error(f"[GET_DEPLOY_DETAIL] HTTP error: {e.response.status_code}, body={e.response.text}")
                raise RuntimeError(f"Failed to get deploy detail: {e}") from e
