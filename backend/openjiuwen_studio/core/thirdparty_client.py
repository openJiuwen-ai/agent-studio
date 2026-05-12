# clients/deepsearch_http.py
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List, Tuple, Union
import httpx
from httpx._models import Response
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.common.exceptions import DeepSearchClientError, RuntimeClientError

logger = logging.getLogger(__name__)


class LazyDeepSearchHttpClient:
    """
    通用的、懒加载的 DeepSearch Agent HTTP 客户端。
    支持任意 GET/POST，流式/非流式，由调用方指定。
    """
    _instance: Optional["LazyDeepSearchHttpClient"] = None
    _clients: Dict[str, httpx.AsyncClient]
    _initialized: Dict[str, bool]
    _base_urls: Dict[str, str]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clients = {}
            cls._instance._initialized = {"search": False, "research": False}
            cls._instance._base_urls = {}
        return cls._instance

    @staticmethod
    def _resolve_target(url: str) -> Tuple[str, str, int]:
        if url.startswith("/runs") or url.startswith("/telemetry/"):
            return "search", settings.deepsearch_telemetry_host, settings.deepsearch_telemetry_port
        return "research", settings.deepsearch_agent_host, settings.deepsearch_agent_port

    async def _initialize(self, mode: str, host: str, port: int) -> bool:
        try:
            if not host or not port:
                raise ValueError(f"DeepSearch {mode} host/port not configured")

            base_url = f"http://{host}:{port}"
            client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(
                    timeout=3600.0,
                    connect=10.0
                ),
                limits=httpx.Limits(max_connections=50),
                follow_redirects=False,
                verify=False
            )

            try:
                resp = await client.get("/", timeout=5.0)
                resp.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as ex:
                await client.aclose()
                raise RuntimeError(f"DeepSearch service unreachable: {ex}") from ex

            previous_client = self._clients.get(mode)
            if previous_client:
                await previous_client.aclose()

            self._clients[mode] = client
            self._base_urls[mode] = base_url
            self._initialized[mode] = True
            logger.info(f"DeepSearch HTTP client ready. mode={mode}, base_url={base_url}")
            return True
        except Exception as e:
            stale_client = self._clients.pop(mode, None)
            if stale_client:
                await stale_client.aclose()
            self._base_urls.pop(mode, None)
            self._initialized[mode] = False
            logger.error(f"Failed to initialize DeepSearch HTTP client for mode={mode}: {e}")
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
        mode, host, port = self._resolve_target(url)
        target_base_url = f"http://{host}:{port}"
        client = self._clients.get(mode)
        if (
            not self._initialized.get(mode, False)
            or client is None
            or self._base_urls.get(mode) != target_base_url
        ):
            await self._initialize(mode, host, port)
            client = self._clients.get(mode)
        if client is None:
            raise RuntimeError(f"DeepSearch client initialization failed for mode={mode}")
        try:
            resp = await client.request(method, url, json=jsons, params=params, headers=headers)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            # Let HTTP errors bubble up so caller can handle them meaningfully
            raise
        except Exception as e:
            # 可选：重置状态，允许下次重试
            failed_client = self._clients.pop(mode, None)
            if failed_client:
                await failed_client.aclose()
            self._base_urls.pop(mode, None)
            self._initialized[mode] = False
            raise RuntimeError(f"DeepSearch service call failed: {e}") from e

    async def request_multipart(
        self,
        method: str,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[List[Tuple[str, Tuple[str, bytes, str]]]] = None,
    ):
        """发送 multipart/form-data 请求（用于文件上传）"""
        mode, host, port = self._resolve_target(url)
        target_base_url = f"http://{host}:{port}"
        client = self._clients.get(mode)
        if (
            not self._initialized.get(mode, False)
            or client is None
            or self._base_urls.get(mode) != target_base_url
        ):
            await self._initialize(mode, host, port)
            client = self._clients.get(mode)
        if client is None:
            raise RuntimeError(f"DeepSearch client initialization failed for mode={mode}")
        try:
            resp = await client.request(method, url, data=data, files=files)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            failed_client = self._clients.pop(mode, None)
            if failed_client:
                await failed_client.aclose()
            self._base_urls.pop(mode, None)
            self._initialized[mode] = False
            raise RuntimeError(f"DeepSearch service call failed: {e}") from e

    async def close(self):
        for mode, client in list(self._clients.items()):
            await client.aclose()
            self._initialized[mode] = False
        self._clients.clear()
        self._base_urls.clear()

    async def stream(self, method: str, url: str, **kwargs):
        """用于流式请求，返回异步上下文管理器"""
        mode, host, port = self._resolve_target(url)
        target_base_url = f"http://{host}:{port}"
        client = self._clients.get(mode)
        if (
            not self._initialized.get(mode, False)
            or client is None
            or self._base_urls.get(mode) != target_base_url
        ):
            await self._initialize(mode, host, port)
            client = self._clients.get(mode)
        if client is None:
            raise RuntimeError(f"DeepSearch client initialization failed for mode={mode}")
        return client.stream(method, url, **kwargs)


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

    async def create_deepsearch_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """创建 Search-mode run。"""
        resp = await self._http.request("POST", "/runs", jsons=payload)
        return resp.json()

    async def cancel_deepsearch_run(self, run_id: str) -> Dict[str, Any]:
        """取消 Search-mode run。"""
        resp = await self._http.request("POST", f"/runs/{run_id}/cancel")
        return resp.json()

    async def get_deepsearch_telemetry_recent(self, n: int = 1, run_id: Optional[str] = None) -> Dict[str, Any]:
        """读取最近的 telemetry 事件。"""
        params: Dict[str, Any] = {"n": n}
        if run_id:
            params["run_id"] = run_id
        resp = await self._http.request("GET", "/telemetry/recent", params=params)
        return resp.json()

    async def get_deepsearch_telemetry_range(
        self,
        run_id: str,
        start_seq: int,
        end_seq: int,
    ) -> Dict[str, Any]:
        """按 seq 范围读取 telemetry 事件。"""
        resp = await self._http.request(
            "GET",
            "/telemetry/range",
            params={"run_id": run_id, "start_seq": start_seq, "end_seq": end_seq},
        )
        return resp.json()

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

    # ---------- DeepSearch 知识库 API（/api/kb） ----------

    async def create_knowledge_base(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """创建 DeepSearch 知识库，返回响应 body"""
        resp = await self._http.request("POST", "/api/kb/create", jsons=payload)
        return resp.json()

    async def update_knowledge_base(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """更新 DeepSearch 知识库（含 embed_model_config、llm_config 等 config）"""
        resp = await self._http.request("POST", "/api/kb/update", jsons=payload)
        return resp.json()

    async def delete_knowledge_base(self, space_id: str, ds_kb_id: str) -> Dict[str, Any]:
        """删除 DeepSearch 知识库"""
        resp = await self._http.request(
            "POST", "/api/kb/delete", jsons={"space_id": space_id, "kb_id": ds_kb_id}
        )
        return resp.json()

    async def upload_knowledge_base_files(
        self,
        space_id: str,
        ds_kb_id: str,
        files: List[Tuple[str, bytes, str]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """上传文件到 DeepSearch 知识库。files: [(filename, file_bytes, content_type), ...]"""
        data = {"space_id": space_id, "kb_id": ds_kb_id}
        if metadata is not None:
            data["metadata"] = json.dumps(metadata)
        file_parts = [
            ("files", (fn, content, ct)) for fn, content, ct in files
        ]
        resp = await self._http.request_multipart(
            "POST", "/api/kb/upload", data=data, files=file_parts
        )
        return resp.json()

    async def process_knowledge_base_documents(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """触发 DeepSearch 知识库文档处理/建索引"""
        resp = await self._http.request("POST", "/api/kb/process", jsons=payload)
        return resp.json()

    async def list_knowledge_bases(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """查询 DeepSearch 知识库列表（含索引状态等）"""
        resp = await self._http.request("POST", "/api/kb/list", jsons=payload)
        return resp.json()

    async def list_embedding_configs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """查询 DeepSearch 侧当前空间可用的 Embedding 配置（供同步时选择嵌入模型）"""
        resp = await self._http.request("POST", "/api/kb/embedding-configs/list", jsons=payload)
        return resp.json()

    async def list_documents(
        self,
        space_id: str,
        kb_id: str,
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """查询 DeepSearch 知识库文档列表（用于仅存在于 DeepSearch 的知识库，如同步产生的 deepsearch_xxx）"""
        resp = await self._http.request(
            "POST",
            "/api/kb/documents/list",
            jsons={"space_id": space_id, "kb_id": kb_id, "page": page, "size": size},
        )
        return resp.json()

    async def get_document_status(
        self,
        space_id: str,
        kb_id: str,
        doc_id_list: list,
    ) -> Dict[str, Any]:
        """批量查询 DeepSearch 知识库文档状态（用于同步后的知识库文档状态展示）"""
        resp = await self._http.request(
            "POST",
            "/api/kb/documents/status",
            jsons={
                "space_id": space_id,
                "kb_id": kb_id,
                "doc_id_list": doc_id_list,
            },
        )
        return resp.json()

    async def delete_documents(
        self,
        space_id: str,
        kb_id: str,
        document_ids: list,
    ) -> Dict[str, Any]:
        """批量删除 DeepSearch 知识库文档（用于更新同步前清空 DS 侧文档以实现覆盖）"""
        resp = await self._http.request(
            "POST",
            "/api/kb/documents/delete",
            jsons={"space_id": space_id, "kb_id": kb_id, "document_ids": document_ids},
        )
        return resp.json()

    async def task_progress(
        self,
        space_id: str,
        kb_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """查询 DeepSearch 知识库文档处理任务进度"""
        resp = await self._http.request(
            "POST",
            "/api/kb/task/progress",
            jsons={"space_id": space_id, "kb_id": kb_id, "task_id": task_id},
        )
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
            raise RuntimeClientError(
                code=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.code,
                message=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.errmsg
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


    async def runtime_health_check(self) -> Dict[str, Any]:
        """检查 runtime 服务健康状态"""
        try:
            resp = await self._http.request("GET", "/health")
            data = resp.json()
            if data.get("status") != "healthy":
                logger.error(f"[RUNTIME_HEALTH_CHECK] Runtime health status is not healthy: {data}")
                raise RuntimeClientError(
                    code=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.code,
                    message=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.errmsg
                )
            return data
        except Exception as e:
            logger.error(f"[RUNTIME_HEALTH_CHECK] Unexpected error: {e}")

            raise RuntimeClientError(
                code=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.code,
                message=StatusCode.AGENT_RUNTIME_CLIENT_ERROR.errmsg
            ) from e


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

        if payload.get("userdata") is not None:
            params["userdata"] = json.dumps(payload.get("userdata"))
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

        except DeepSearchClientError as e:
            if e.error_code == 205002:
                return Response(
                    status_code=400,
                    text=f"Runtime service unreachable: All connection attempts failed",
                )
        except Exception as e:
            logger.error(f"[GET_DEPLOY_DETAIL] HTTP error: {e.response.status_code}, body={e.response.text}")
            raise RuntimeError(f"Failed to get deploy detail: {e}") from e
