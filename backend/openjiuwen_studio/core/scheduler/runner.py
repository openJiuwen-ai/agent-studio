"""
execute_trigger_job() is the single entry point for all trigger types.
Called by:
  - APScheduler (cron and polling)
  - Webhook inbound receiver (via FastAPI BackgroundTasks)
  - Manual test-run endpoint (via asyncio.create_task)
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import SessionLocal, milliseconds
from openjiuwen_studio.core.scheduler.system_user import make_system_user
from openjiuwen_studio.models.trigger import TriggerDB, TriggerExecutionLogDB


@dataclass
class LogParams:
    """Parameters for writing trigger execution log."""
    status: str
    fired_by: str
    conversation_id: Optional[str] = None
    inputs_snapshot: Optional[Dict[str, Any]] = None
    poll_hash_seen: Optional[str] = None
    error_message: Optional[str] = None


async def execute_trigger_job(trigger_id: str, fired_by: str = "scheduler") -> None:
    """
    Main entry point. Looks up the trigger, routes to type-specific handler.
    All errors are caught here so the scheduler never sees an unhandled exception.
    """
    logger.info(f"[Trigger] Job invoked: trigger_id={trigger_id} fired_by={fired_by}")
    db = SessionLocal()
    try:
        trigger: Optional[TriggerDB] = (
            db.query(TriggerDB)
            .filter(TriggerDB.trigger_id == trigger_id)
            .first()
        )
        if not trigger:
            logger.error(f"[Trigger] Not found: trigger_id={trigger_id}")
            return
        if not trigger.is_active and fired_by != "manual":
            logger.info(f"[Trigger] Inactive, skipping: trigger_id={trigger_id}")
            return

        logger.info(
            f"[Trigger] Firing: trigger_id={trigger_id} name={trigger.name!r} "
            f"type={trigger.trigger_type} target={trigger.target_type}:{trigger.target_id}"
        )

        if trigger.trigger_type == "polling":
            await _handle_polling(db, trigger, fired_by)
        else:
            # cron or webhook — fire immediately
            await _fire_execution(db, trigger, fired_by=fired_by)

    except Exception as e:
        logger.exception(
            f"[Trigger] Unhandled error for trigger_id={trigger_id}: {e}"
        )
    finally:
        db.close()


# ── Polling ──────────────────────────────────────────────────────────────────

async def _handle_polling(db, trigger: TriggerDB, fired_by: str) -> None:
    config = trigger.config or {}
    poll_url = config.get("poll_url", "")
    if not poll_url:
        logger.warning(f"[Trigger/Poll] No poll_url for trigger_id={trigger.trigger_id}")
        return

    current_hash: Optional[str] = None
    error_msg: Optional[str] = None

    try:
        # Run sync requests in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(
            requests.get,
            poll_url,
            timeout=15,
            headers={"User-Agent": "JiuwenTriggerPoller/1.0"},
        )
        content = response.content
        # Cap at 10 MB before hashing to handle arbitrarily large responses
        if len(content) > 10 * 1024 * 1024:
            content = content[: 10 * 1024 * 1024]
        current_hash = hashlib.sha256(content).hexdigest()
    except Exception as e:
        error_msg = f"Poll fetch failed: {e}"
        logger.warning(f"[Trigger/Poll] {error_msg} trigger_id={trigger.trigger_id}")

    now = milliseconds()
    last_seen_hash = config.get("last_seen_hash")

    # Always update last_checked_at
    new_config = dict(config)
    new_config["last_checked_at"] = now
    if current_hash:
        new_config["last_seen_hash"] = current_hash
    trigger.config = new_config
    trigger.update_time = now
    db.add(trigger)
    db.commit()

    if error_msg:
        _write_log(
            db, trigger,
            LogParams(status="error", fired_by=fired_by, error_message=error_msg)
        )
        return

    if current_hash == last_seen_hash and last_seen_hash is not None:
        # Content unchanged — record a skipped check, do not fire
        _write_log(
            db, trigger,
            LogParams(status="skipped", fired_by="poll", poll_hash_seen=current_hash)
        )
        return

    # Content changed (or first ever check where last_seen_hash is None)
    await _fire_execution(
        db, trigger,
        fired_by="poll",
        poll_hash_seen=current_hash,
    )


# ── Execution ─────────────────────────────────────────────────────────────────

async def _fire_execution(
    db,
    trigger: TriggerDB,
    fired_by: str,
    extra_inputs: Optional[Dict[str, Any]] = None,
    poll_hash_seen: Optional[str] = None,
) -> None:
    conversation_id = str(uuid.uuid4())

    inputs: Dict[str, Any] = dict(trigger.input_payload or {})
    if extra_inputs:
        inputs.update(extra_inputs)

    current_user = make_system_user(trigger.space_id)

    # Write "running" log immediately so the UI can show in-progress state
    log = _write_log(
        db, trigger,
        LogParams(
            status="running",
            fired_by=fired_by,
            conversation_id=conversation_id,
            inputs_snapshot=inputs,
            poll_hash_seen=poll_hash_seen,
        )
    )

    started_at = milliseconds()
    outputs: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    status = "success"

    try:
        gen = _get_runner(trigger, inputs, conversation_id, current_user)

        # Fully consume the async generator — partial consumption leaks resources
        last_chunk = None
        async for chunk in gen:
            last_chunk = chunk

        if last_chunk is not None:
            outputs = _extract_outputs(last_chunk)

    except Exception as e:
        status = "error"
        error_message = str(e)
        logger.exception(
            f"[Trigger] Execution error trigger_id={trigger.trigger_id}: {e}"
        )

    finished_at = milliseconds()

    log.status = status
    log.outputs = outputs
    log.error_message = error_message
    log.finished_at = finished_at
    log.duration_ms = finished_at - started_at
    log.update_time = finished_at
    db.add(log)
    db.commit()


def _get_runner(
    trigger: TriggerDB,
    inputs: Dict[str, Any],
    conversation_id: str,
    current_user: Dict[str, Any],
):
    """Return the async generator for the target agent or workflow."""
    if trigger.target_type == "agent":
        from openjiuwen_studio.core.executor.agent.agent_runner import agent_mgr
        # Agent runner requires conversation_id in inputs dict
        agent_inputs = dict(inputs)
        agent_inputs["conversation_id"] = conversation_id
        return agent_mgr.run(
            id=trigger.target_id,
            version=trigger.target_version,
            inputs=agent_inputs,
            conversation_id=conversation_id,
            space_id=trigger.space_id,
            current_user=current_user,
        )
    elif trigger.target_type == "workflow":
        from openjiuwen_studio.core.executor.workflow.workflow_runner import flow_mgr
        return flow_mgr.run(
            id=trigger.target_id,
            version=trigger.target_version,
            inputs=inputs,
            conversation_id=conversation_id,
            space_id=trigger.space_id,
            current_user=current_user,
        )
    else:
        raise ValueError(f"Unknown target_type: {trigger.target_type!r}")


def _write_log(
    db,
    trigger: TriggerDB,
    params: LogParams,
) -> TriggerExecutionLogDB:
    now = milliseconds()
    log = TriggerExecutionLogDB(
        space_id=trigger.space_id,
        trigger_id=trigger.trigger_id,
        trigger_type=trigger.trigger_type,
        status=params.status,
        fired_by=params.fired_by,
        conversation_id=params.conversation_id,
        inputs_snapshot=params.inputs_snapshot,
        poll_hash_seen=params.poll_hash_seen,
        error_message=params.error_message,
        started_at=now,
        create_time=now,
        update_time=now,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _json_default(obj: Any) -> Any:
    """Fallback serializer for types not handled by the standard encoder."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)


def _extract_outputs(chunk: Any) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of a JSON-serializable dict from a stream chunk."""
    try:
        if hasattr(chunk, "model_dump"):
            raw = chunk.model_dump()
        elif isinstance(chunk, dict):
            raw = chunk
        else:
            return {"raw": str(chunk)}
        # Round-trip through JSON to ensure every value is serializable.
        # This converts datetime objects, custom classes, etc. to plain strings.
        return json.loads(json.dumps(raw, default=_json_default))
    except Exception:
        return None
