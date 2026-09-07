"""Internal endpoints for memory repo and memory item management.

Called by Java studio-runtime-service via JiuWenClient, these endpoints
operate directly on the LTM (LongTermMemory) singleton.
"""

import logging
import re
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from openjiuwen.core.memory.manage.mem_model.memory_unit import MemoryType

from agent_runtime.memory.adapter.ltm_manager import get_ltm

logger = logging.getLogger(__name__)


def _validate_uuid(value: str, field_name: str = "id") -> str | None:
    """Validate UUID format. Returns error message if invalid, None if valid."""
    try:
        uuid.UUID(value)
        return None
    except (ValueError, AttributeError):
        return f"Invalid {field_name} format: {value!r} is not a valid UUID"


# memory_id 由 agent-core 抽取器生成，为 24 位十六进制 ObjectId（非 UUID）。
# 兼容两种格式：24-hex ObjectId 与标准 UUID。
_MEMORY_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{24}$"
    r"|^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _validate_memory_id(value: str) -> str | None:
    """Validate memory ID format (24-hex ObjectId or UUID). Returns error message if invalid."""
    if value and _MEMORY_ID_PATTERN.match(value):
        return None
    return f"Invalid memory_id format: {value!r}"

memory_internal_router = APIRouter(prefix="/internal/v1/memory-repos", tags=["memory-internal"])


# ── Memory repo lifecycle ──


@memory_internal_router.delete("/{memory_repo_id}")
async def delete_memory_repo(memory_repo_id: str):
    """Delete all memory data for a memory repo.

    Called by Java Manager via Runtime RCE when a memory repo is deleted.
    """
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})

    ltm = get_ltm()
    if ltm is None:
        return {"status": "skipped", "reason": "memory library not initialized"}

    try:
        await ltm.delete_mem_by_scope(memory_repo_id)
    except Exception as e:
        logger.error("Failed to delete memory data for repo %s: %s", memory_repo_id, e)
        return {"status": "error", "reason": str(e)}

    try:
        await ltm.delete_scope_config(memory_repo_id)
    except Exception as e:
        logger.warning(
            "Failed to delete scope config for repo %s (non-critical): %s",
            memory_repo_id,
            e,
        )

    return {"status": "ok"}


# ── Memory item CRUD ──


@memory_internal_router.delete("/{memory_repo_id}/users/{user_id}/memories")
async def clear_user_memories(memory_repo_id: str, user_id: str):
    """Clear all memories for a user within a memory repo scope."""
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})

    ltm = get_ltm()
    if ltm is None:
        return {"status": "skipped", "reason": "memory library not initialized"}

    # LTM stores user_id in lowercase (OpenSearch index names must be lowercase)
    user_id = user_id.lower()

    try:
        await ltm.delete_mem_by_user_id(user_id, memory_repo_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(
            "Failed to clear memories for user %s in repo %s: %s",
            user_id,
            memory_repo_id,
            e,
        )
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})


@memory_internal_router.post("/{memory_repo_id}/users/{user_id}/memories/batch-delete")
async def batch_delete_memories(memory_repo_id: str, user_id: str, body: dict):
    """Batch-delete memories by ID list.

    Body: {"memory_ids": ["id1", "id2", ...]}
    """
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})

    ltm = get_ltm()
    if ltm is None:
        return {"status": "skipped", "reason": "memory library not initialized"}

    # LTM stores user_id in lowercase (OpenSearch index names must be lowercase)
    user_id = user_id.lower()

    memory_ids = body.get("memory_ids", [])
    if not memory_ids:
        return JSONResponse(status_code=400, content={"status": "error", "reason": "memory_ids is required"})

    errors = []
    for mem_id in memory_ids:
        try:
            await ltm.delete_mem_by_id(mem_id, user_id, memory_repo_id)
        except Exception as e:
            errors.append({"mem_id": mem_id, "error": str(e)})

    if errors:
        return {"status": "partial", "errors": errors}
    return {"status": "ok"}


@memory_internal_router.get("/{memory_repo_id}/users/{user_id}/memories")
async def list_user_memories(
    memory_repo_id: str,
    user_id: str,
    page_size: int = Query(10, ge=1, le=1000),
    page_num: int = Query(1, ge=1),
    memory_type: str = Query(None),
):
    """Paginated list of memories for a user within a memory repo scope."""
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})

    ltm = get_ltm()
    if ltm is None:
        return {"total": 0, "memories": []}

    # LTM stores user_id in lowercase (OpenSearch index names must be lowercase)
    user_id = user_id.lower()

    # 类型过滤：字符串 → MemoryType 枚举，直传 LTM（服务端过滤 + 过滤后分页）。
    # LTM 只认枚举（UNKNOWN 表示不过滤），透传字符串会被当成无效类型。
    mem_type_enum = MemoryType.UNKNOWN
    if memory_type:
        try:
            mem_type_enum = MemoryType(memory_type)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "reason": f"invalid memory_type: {memory_type}"},
            )

    try:
        results = await ltm.get_user_mem_by_page(
            user_id=user_id,
            scope_id=memory_repo_id,
            page_size=page_size,
            page_idx=page_num,
            memory_type=mem_type_enum,
        )

        memories = []
        for r in (results or []):
            info = r.mem_info if hasattr(r, "mem_info") else r
            mem_type = getattr(info, "type", None)
            if mem_type is not None and hasattr(mem_type, "value"):
                mem_type_str = mem_type.value
            elif mem_type is not None:
                mem_type_str = str(mem_type)
            else:
                mem_type_str = ""
            memories.append({
                "memory_id": getattr(info, "mem_id", ""),
                "content": getattr(info, "content", ""),
                "type": mem_type_str,
                "last_update_time": str(getattr(info, "timestamp", "")),
            })

        # 非满页即最后一页，total 可直接算出；满页才需要有界扫描（cap 内精确）
        if len(memories) < page_size:
            total = (page_num - 1) * page_size + len(memories)
        else:
            total = await _count_user_memories(ltm, user_id, memory_repo_id, mem_type_enum)

        return {"total": total, "memories": memories}
    except Exception as e:
        logger.error(
            "Failed to list memories for user %s in repo %s: %s",
            user_id,
            memory_repo_id,
            e,
            exc_info=True,
        )
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})


# total 统计的扫描参数：每批行数与安全上限（超出上限后 total 按封顶值近似）
_TOTAL_SCAN_PAGE_SIZE = 1000
_TOTAL_SCAN_MAX_ROWS = 2000


async def _count_user_memories(
    ltm, user_id: str, scope_id: str, mem_type_enum: MemoryType
) -> int:
    """有界扫描统计 total。

    LTM 的 get_user_mem_by_page 不返回总数（openjiuwen SDK 约束不可改），
    按 _TOTAL_SCAN_PAGE_SIZE 分批扫描直到出现非满批（精确）或到达
    _TOTAL_SCAN_MAX_ROWS 上限（封顶近似）。
    """
    total = 0
    page_idx = 1
    while total < _TOTAL_SCAN_MAX_ROWS:
        batch = await ltm.get_user_mem_by_page(
            user_id=user_id,
            scope_id=scope_id,
            page_size=_TOTAL_SCAN_PAGE_SIZE,
            page_idx=page_idx,
            memory_type=mem_type_enum,
        )
        batch_len = len(batch or [])
        total += batch_len
        if batch_len < _TOTAL_SCAN_PAGE_SIZE:
            break
        page_idx += 1
    return total


@memory_internal_router.post("/{memory_repo_id}/users/{user_id}/memories/search")
async def search_memories(
    memory_repo_id: str,
    user_id: str,
    body: dict,
):
    """Semantic search for memories within a memory repo scope.

    Body: {"query": "...", "top_k": 10, "threshold": 0.3}
    """
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})

    ltm = get_ltm()
    if ltm is None:
        return {"total": 0, "memories": []}

    # LTM stores user_id in lowercase (OpenSearch index names must be lowercase)
    user_id = user_id.lower()

    query = body.get("query", "")
    if not query:
        return JSONResponse(status_code=400, content={"status": "error", "reason": "query is required"})

    top_k = body.get("top_k", 10)
    threshold = body.get("threshold", 0.3)

    try:
        results = await ltm.search_user_mem(
            query=query,
            num=top_k,
            user_id=user_id,
            scope_id=memory_repo_id,
            threshold=threshold,
        )

        memories = []
        for r in (results or []):
            info = r.mem_info if hasattr(r, "mem_info") else r
            mem_type = getattr(info, "type", None)
            if mem_type is not None and hasattr(mem_type, "value"):
                mem_type_str = mem_type.value
            elif mem_type is not None:
                mem_type_str = str(mem_type)
            else:
                mem_type_str = ""

            memories.append({
                "memory_id": getattr(info, "mem_id", ""),
                "content": getattr(info, "content", ""),
                "type": mem_type_str,
                "score": getattr(r, "score", None),
                "last_update_time": str(getattr(info, "timestamp", "")),
            })

        return {"total": len(memories), "memories": memories}
    except Exception as e:
        logger.error(
            "Failed to search memories for user %s in repo %s: %s",
            user_id,
            memory_repo_id,
            e,
            exc_info=True,
        )
        return {"total": 0, "memories": [], "error": str(e)}


@memory_internal_router.put("/{memory_repo_id}/memories/{memory_id}")
async def update_memory(memory_repo_id: str, memory_id: str, body: dict):
    """Update a single memory's content.

    Body: {"user_id": "...", "content": "new content"}
    """
    err = _validate_uuid(memory_repo_id, "memory_repo_id")
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})
    err = _validate_memory_id(memory_id)
    if err:
        return JSONResponse(status_code=400, content={"status": "error", "reason": err})
    if not memory_id or not memory_id.strip():
        return JSONResponse(status_code=400, content={"status": "error", "reason": "memory_id is required"})

    ltm = get_ltm()
    if ltm is None:
        return {"status": "skipped", "reason": "memory library not initialized"}

    user_id = body.get("user_id", "")
    content = body.get("content", "")

    # LTM stores user_id in lowercase (OpenSearch index names must be lowercase)
    user_id = user_id.lower()

    try:
        # agent-core 的 update_mem_by_id 在 id 不存在时只打 warning 静默返回（不抛错），
        # 若不预检会向 manager 返回 ok，用户的编辑被静默丢弃却提示成功。
        # write_manager 内部正是用 memory_index.get_by_id 判定存在性，此处预检与其等价；
        # 非 default 索引实现没有 get_by_id 时跳过预检，保持原行为。
        memory_index = getattr(ltm, "memory_index", None)
        if memory_index is not None and hasattr(memory_index, "get_by_id"):
            existing = await memory_index.get_by_id(user_id, memory_repo_id, memory_id)
            if existing is None:
                return {
                    "status": "skipped",
                    "reason": f"memory {memory_id} not found for user in repo {memory_repo_id}",
                }
        await ltm.update_mem_by_id(memory_id, content, user_id, memory_repo_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(
            "Failed to update memory %s in repo %s: %s",
            memory_id,
            memory_repo_id,
            e,
        )
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})
