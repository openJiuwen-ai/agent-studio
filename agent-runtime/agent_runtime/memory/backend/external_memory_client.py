"""External memory client — httpx async client for agent-memory 2.0 HTTP API.

This is the EXTERNAL branch of the runtime data-plane. It directly calls
the agent-memory 2.0 HTTP server (native http.server, no FastAPI).

2.0 API contract:
  - Unified entry: POST /v1/{verb} where verb = MemoryAPI method name
  - Scope is a nested object: {"org", "space", "user", "agent", "session"}
  - Responses are raw return values (no envelope wrapping)
  - Auth: Authorization: Bearer <api_key>

Scope mapping from Studio:
  - org = "studio" (fixed)
  - space = memory_repo_id (per-repo isolation)
  - user = user_id (per-user isolation)
  - agent = "" / session = "" (unused)

Key methods:
  - add(content, scope, system_metadata={infer:"true"}) → auto-triggers LLM extraction
  - search(query, context={scope}, top_k, disclosure="l2") → {items:[{unit_id, content, score}]}
  - list(scope, offset, limit) → {items:[{id, segments:[{content}]}], count}
  - delete(selector={scope, mode:"purge"}) → ["id1", ...]
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

from agent_runtime.memory.backend.instance_credential_resolver import get_resolver

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 120.0

# Default to skip TLS verification, aligning with IR_LLM_SSL_VERIFY /
# OPENSEARCH_SSL_VERIFY / KB_SSL_VERIFY conventions in this codebase (all
# default false). Set MEMORY_VERIFY_SSL=true to enforce cert validation
# when the agent-memory instance uses a trusted CA certificate.
_VERIFY_SSL = os.getenv("MEMORY_VERIFY_SSL", "false").strip().lower() in ("1", "true", "yes", "on")


class ExternalMemoryClient:
    """Async HTTP client for the agent-memory 2.0 service.

    Constructed from IR metadata: ``instance_base_url`` + resolved ``api_key``.
    The api_key is resolved lazily from OBS auth files by ``instance_id``.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(_DEFAULT_TIMEOUT),
                verify=_VERIFY_SSL,
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _build_scope(repo_id: str, user: str) -> dict[str, str]:
        """Build the 2.0 Scope object from Studio's memory_repo_id + user_id.

        In the offline/dev profile (InMemoryEngine), space must be empty.
        We use the ``user`` field for isolation: ``user = "{repo_id}:{user_id}"``
        to keep per-repo + per-user isolation without requiring space support.
        In production (CloudEngine), this can be changed to use ``space = repo_id``.
        """
        combined_user = f"{repo_id}:{user}" if repo_id else user
        return {"org": "studio", "space": "", "user": combined_user, "agent": "", "session": ""}

    # ==================== Data-plane methods ====================

    async def add(
        self,
        content: str,
        space: str,
        user: str,
        infer: bool = True,
        tags: list[str] | None = None,
    ) -> bool:
        """Write a memory unit to agent-memory 2.0.

        When ``infer=True`` (default), the server automatically triggers LLM
        extraction to derive structured memories from the content.

        Maps to ``POST /v1/add``.
        Returns True on success, False on failure (graceful degradation).
        """
        body: dict[str, Any] = {
            "content": content,
            "scope": self._build_scope(space, user),
            "source": "text",
            "system_metadata": {"infer": "true"} if infer else {},
        }
        if tags:
            body["tags"] = tags

        return await self._post("/v1/add", body)

    async def add_messages(
        self,
        messages: list[dict[str, Any]],
        user_id: str,
        scope_id: str,
        **kwargs,
    ) -> bool:
        """Write conversation messages to agent-memory 2.0.

        Iterates over messages and calls add() for each with infer=true.
        This replaces the 1.0 add_messages endpoint.
        """
        uid = user_id.lower()
        all_ok = True
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            if not content:
                continue
            ok = await self.add(content=content, space=scope_id, user=uid, infer=True)
            if not ok:
                all_ok = False
        return all_ok

    async def search(
        self,
        query: str,
        top_k: int,
        user_id: str,
        scope_id: str,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Semantic search for memories.

        Maps to ``POST /v1/search``.
        Returns a list of memory dicts: [{unit_id, content, score, ...}].
        """
        body = {
            "query": query,
            "context": {
                "scope": self._build_scope(scope_id, user_id.lower()),
            },
            "top_k": top_k,
            "disclosure": "l2",
            "with_trajectory": False,
        }
        result = await self._post_json("/v1/search", body)
        if result is None:
            return []
        if isinstance(result, dict):
            items = result.get("items", [])
            return items if isinstance(items, list) else []
        if isinstance(result, list):
            return result
        return []

    async def search_memory(
        self,
        query: str,
        num: int,
        user_id: str,
        scope_id: str,
        threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Backward-compatible alias for search()."""
        return await self.search(query, num, user_id, scope_id, threshold)

    async def search_user_history_summary(
        self,
        query: str,
        num: int,
        user_id: str,
        scope_id: str,
    ) -> list[dict[str, Any]]:
        """Search user history summaries.

        Uses the 2.0 search endpoint. In 2.0, memory type filtering is done
        via the ``filters`` parameter. We pass a filter for summary-type memories.
        """
        body = {
            "query": query,
            "context": {
                "scope": self._build_scope(scope_id, user_id.lower()),
            },
            "top_k": num,
            "disclosure": "l2",
            "with_trajectory": False,
        }
        result = await self._post_json("/v1/search", body)
        if result is None:
            return []
        if isinstance(result, dict):
            items = result.get("items", [])
            return items if isinstance(items, list) else []
        return []

    async def list_memories(
        self,
        user_id: str,
        scope_id: str,
        offset: int = 0,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Paginated list of user memories.

        Maps to ``POST /v1/list``.
        Returns ``{"items": [...], "count": N}`` or empty structure on failure.
        """
        body = {
            "scope": self._build_scope(scope_id, user_id.lower()),
            "offset": offset,
            "limit": limit,
        }
        result = await self._post_json("/v1/list", body)
        if result is None:
            return {"items": [], "count": 0}
        if isinstance(result, dict):
            return {
                "items": result.get("items", []),
                "count": result.get("count", 0),
            }
        return {"items": [], "count": 0}

    async def get_user_mem_by_page(
        self,
        user_id: str,
        scope_id: str,
        page_num: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """Backward-compatible alias for list_memories()."""
        return await self.list_memories(user_id, scope_id, (page_num - 1) * page_size, page_size)

    async def delete_by_scope(self, scope_id: str, user_id: str = "") -> bool:
        """Delete all memories for a scope.

        Maps to ``POST /v1/delete`` with selector containing scope + mode=purge.
        """
        body = {
            "selector": {
                "scope": self._build_scope(scope_id, user_id.lower()),
                "mode": "purge",
            }
        }
        return await self._post("/v1/delete", body)

    async def delete_mem_by_scope(self, scope_id: str) -> bool:
        """Backward-compatible alias for delete_by_scope()."""
        return await self.delete_by_scope(scope_id)

    async def delete_mem_by_id(self, scope_id: str, mem_id: str, user_id: str = "") -> bool:
        """Delete a specific memory by ID.

        Maps to ``POST /v1/delete`` with selector containing unit_ids.
        """
        body = {
            "selector": {
                "unit_ids": [mem_id],
                "scope": self._build_scope(scope_id, user_id.lower()),
                "mode": "purge",
            }
        }
        return await self._post("/v1/delete", body)

    async def batch_delete_mem(self, scope_id: str, mem_ids: list[str], user_id: str = "") -> bool:
        """Batch delete memories by ID list."""
        body = {
            "selector": {
                "unit_ids": mem_ids,
                "scope": self._build_scope(scope_id, user_id.lower()),
                "mode": "purge",
            }
        }
        return await self._post("/v1/delete", body)

    async def health_check(self) -> bool:
        """Check if the agent-memory instance is healthy.

        Maps to ``GET /healthz``.
        """
        try:
            client = await self._ensure_client()
            resp = await client.get("/healthz", headers=self._headers())
            if resp.status_code != 200:
                logger.warning(
                    "agent-memory %s/healthz returned %d",
                    self._base_url, resp.status_code,
                )
                return False
            return True
        except Exception as e:
            logger.warning(
                "agent-memory %s/healthz request failed: %s",
                self._base_url, e,
            )
            return False

    # ==================== Internal HTTP helpers ====================

    async def _post(self, path: str, body: dict) -> bool:
        """POST and return True/False (graceful degradation, no exception)."""
        try:
            client = await self._ensure_client()
            resp = await client.post(path, json=body, headers=self._headers())
            if resp.status_code != 200:
                logger.warning(
                    "agent-memory %s%s returned %d: %s",
                    self._base_url, path, resp.status_code,
                    resp.text[:200] if resp.text else "",
                )
                return False
            return True
        except Exception as e:
            logger.warning(
                "agent-memory %s%s request failed (degraded): %s",
                self._base_url, path, e,
            )
            return False

    async def _post_json(self, path: str, body: dict) -> Any:
        """POST and return parsed JSON, or None on failure."""
        try:
            client = await self._ensure_client()
            resp = await client.post(path, json=body, headers=self._headers())
            if resp.status_code != 200:
                logger.warning(
                    "agent-memory %s%s returned %d: %s",
                    self._base_url, path, resp.status_code,
                    resp.text[:200] if resp.text else "",
                )
                return None
            return resp.json()
        except Exception as e:
            logger.warning(
                "agent-memory %s%s request failed (degraded): %s",
                self._base_url, path, e,
            )
            return None


# ==================== Factory ====================

# Per-run cache of ExternalMemoryClient instances (by instance_id)
_client_cache: dict[str, ExternalMemoryClient] = {}


async def get_external_client(
    instance_id: str,
    base_url: str,
) -> Optional[ExternalMemoryClient]:
    """Get or create an ExternalMemoryClient for the given instance.

    The api_key is lazily resolved from OBS auth (via InstanceCredentialResolver).
    Clients are cached per-run by instance_id to avoid re-resolving keys.
    """
    if not instance_id or not base_url:
        logger.warning("Cannot create external client: missing instance_id or base_url")
        return None

    if instance_id in _client_cache:
        return _client_cache[instance_id]

    resolver = get_resolver()
    api_key = await resolver.resolve_api_key(instance_id)
    client = ExternalMemoryClient(base_url=base_url, api_key=api_key)
    _client_cache[instance_id] = client
    logger.info(
        "Created ExternalMemoryClient for instance %s at %s (api_key: %s)",
        instance_id, base_url, "set" if api_key else "missing",
    )
    return client


async def close_all_clients():
    """Close all cached clients (called on shutdown)."""
    for client in _client_cache.values():
        await client.close()
    _client_cache.clear()
