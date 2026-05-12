import asyncio
from typing import Any, Awaitable, Callable, Set


def apply_interaction_defaults(
    payload: dict[str, Any],
    *,
    fields_set: Set[str],
    interrupt_feedback: str,
) -> None:
    """Use non-interactive defaults for initial runs when client omits HITL flags."""
    if interrupt_feedback:
        return

    if "workflow_human_in_the_loop" not in fields_set:
        payload["workflow_human_in_the_loop"] = False
    if "outline_interaction_enabled" not in fields_set:
        payload["outline_interaction_enabled"] = False


def get_local_search_kb_ids(payload: dict[str, Any]) -> list[str]:
    """Extract and normalize local knowledge base IDs from payload."""
    local_cfg = payload.get("local_search_config")
    if not isinstance(local_cfg, dict):
        return []

    raw_ids = local_cfg.get("local_search_config_ids")
    if not isinstance(raw_ids, list):
        return []

    kb_ids: list[str] = []
    seen: set[str] = set()
    for kb_id in raw_ids:
        if not isinstance(kb_id, str):
            continue
        normalized_id = kb_id.strip()
        if not normalized_id or normalized_id in seen:
            continue
        seen.add(normalized_id)
        kb_ids.append(normalized_id)
    return kb_ids


async def classify_local_search_kbs(
    *,
    space_id: str,
    kb_ids: list[str],
    list_documents: Callable[..., Awaitable[dict[str, Any]]],
) -> tuple[list[str], list[str], list[str]]:
    """
    Classify local KB IDs by DeepSearch document availability.

    Returns:
        with_docs, empty, unavailable
    """

    async def _inspect(kb_id: str) -> tuple[str, str]:
        page = 1
        size = 100
        scanned = 0
        total = 0
        max_pages = 50

        while page <= max_pages:
            try:
                ds_resp = await list_documents(
                    space_id=space_id,
                    kb_id=kb_id,
                    page=page,
                    size=size,
                )
            except Exception:
                return kb_id, "unavailable"

            if not isinstance(ds_resp, dict):
                return kb_id, "unavailable"

            code = ds_resp.get("code")
            if code not in (None, 200):
                return kb_id, "unavailable"

            data = ds_resp.get("data")
            if not isinstance(data, dict):
                return kb_id, "unavailable"

            raw_total = data.get("total")
            if isinstance(raw_total, str):
                total = int(raw_total) if raw_total.isdigit() else 0
            elif isinstance(raw_total, int):
                total = raw_total
            elif page == 1:
                items = data.get("items")
                total = len(items) if isinstance(items, list) else 0

            items = data.get("items")
            items = items if isinstance(items, list) else []
            scanned += len(items)

            for item in items:
                if isinstance(item, dict) and str(item.get("status", "")).lower() == "indexed":
                    return kb_id, "with_docs"

            if not items or scanned >= total:
                break
            page += 1

        if total > 0:
            return kb_id, "empty"
        return kb_id, "empty"

    results = await asyncio.gather(*(_inspect(kb_id) for kb_id in kb_ids))

    with_docs: list[str] = []
    empty: list[str] = []
    unavailable: list[str] = []

    for kb_id, kb_status in results:
        if kb_status == "with_docs":
            with_docs.append(kb_id)
        elif kb_status == "empty":
            empty.append(kb_id)
        else:
            unavailable.append(kb_id)

    return with_docs, empty, unavailable
