"""Lazy credential resolver for external memory service instances.

Mirrors the ``model_service.resolver`` pattern: the IR carries a non-sensitive
``instance_id`` reference (no api_key); at runtime, this resolver lazily
reads the api_key from the OBS auth file ``memory-auth/{instance_id}.json``
written by the Java manager.  Results are cached per-process (per-run) to
avoid repeated OBS reads.

Decryption: api_key values may be SCC-encrypted; ``common_utils.crypto_tool.decrypt``
is plaintext-tolerant (returns the original string on failure), so it works
for both encrypted and plaintext keys.

For single-instance degraded deployments, the env variable ``MEMORY_API_KEY``
can be used as a fallback (LLM global pattern), also passed through ``_decrypt``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# OBS auth file path template — must match the Java side (MemoryServiceInstanceService)
_MEMORY_AUTH_PATH = "memory-auth/%s.json"


class InstanceCredentialResolver:
    """Resolves api_key for an external memory instance from OBS auth files.

    Thread-safe enough for asyncio usage (no mutation after warm cache).
    """

    _instance: Optional["InstanceCredentialResolver"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._cache: dict[str, str] = {}
            self._storage_provider = None
            self._initialized = True
            logger.info("InstanceCredentialResolver initialized")

    def set_storage_provider(self, provider):
        """Inject the S3/OBS storage provider (called from server.py lifespan)."""
        self._storage_provider = provider

    async def resolve_api_key(self, instance_id: str) -> Optional[str]:
        """Lazily resolve the api_key for an external memory instance.

        Lookup order:
        1. Process cache (per-run)
        2. OBS auth file ``memory-auth/{instance_id}.json``
        3. Env fallback ``MEMORY_API_KEY`` (single-instance degraded mode)

        Returns the decrypted api_key, or ``None`` if not found.
        """
        if not instance_id:
            return self._resolve_from_env()

        # 1. Cache hit
        if instance_id in self._cache:
            return self._cache[instance_id]

        # 2. OBS auth file
        api_key = await self._resolve_from_obs(instance_id)
        if api_key:
            self._cache[instance_id] = api_key
            return api_key

        # 3. Env fallback
        api_key = self._resolve_from_env()
        if api_key:
            self._cache[instance_id] = api_key
            return api_key

        logger.warning(
            "No api_key found for memory instance %s "
            "(OBS auth file missing and MEMORY_API_KEY not set)",
            instance_id,
        )
        return None

    async def _resolve_from_obs(self, instance_id: str) -> Optional[str]:
        """Read api_key from OBS auth file ``memory-auth/{instance_id}.json``."""
        if self._storage_provider is None:
            logger.debug("Storage provider not set, cannot read OBS auth for instance %s", instance_id)
            return None

        object_key = _MEMORY_AUTH_PATH % instance_id
        try:
            content = await self._storage_provider.get_content(object_key)
            auth_data = json.loads(content)
            api_key = auth_data.get("api_key", "")
            if api_key:
                return self._decrypt(api_key)
            logger.warning("OBS auth file for instance %s has empty api_key", instance_id)
            return None
        except Exception as e:
            logger.debug(
                "Failed to read OBS auth for instance %s (key=%s): %s",
                instance_id, object_key, e,
            )
            return None

    @staticmethod
    def _resolve_from_env() -> Optional[str]:
        """Fallback: env ``MEMORY_API_KEY`` (single-instance degraded mode)."""
        raw = os.getenv("MEMORY_API_KEY", "")
        if not raw:
            return None
        return InstanceCredentialResolver._decrypt(raw)

    @staticmethod
    def _decrypt(value: str) -> str:
        """Decrypt using common_utils.crypto_tool (plaintext-tolerant)."""
        try:
            from common_utils.crypto_tool import decrypt
            return decrypt(value)
        except Exception:
            return value


def get_resolver() -> InstanceCredentialResolver:
    """Get the singleton credential resolver."""
    return InstanceCredentialResolver()
