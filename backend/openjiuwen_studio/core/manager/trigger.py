from __future__ import annotations

import secrets
import uuid
from typing import Optional

from fastapi import BackgroundTasks, status
from sqlalchemy import func

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import SessionLocal, milliseconds
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.scheduler.jobs import register_trigger_job, remove_trigger_job
from openjiuwen_studio.core.scheduler.scheduler import get_scheduler
from openjiuwen_studio.models.trigger import TriggerDB, TriggerExecutionLogDB
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.trigger import (
    TriggerCreate, TriggerGet, TriggerUpdate, TriggerActivate,
    TriggerList, TriggerLogsFilter, TriggerLogDetail,
    TriggerDetail, TriggerListResponse,
    TriggerExecutionLogRecord, TriggerExecutionLogSummary, TriggerLogsResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_detail(t: TriggerDB) -> TriggerDetail:
    return TriggerDetail(
        trigger_id=t.trigger_id,
        space_id=t.space_id,
        name=t.name,
        description=t.description,
        trigger_type=t.trigger_type,
        target_type=t.target_type,
        target_id=t.target_id,
        target_version=t.target_version,
        input_payload=t.input_payload,
        is_active=t.is_active,
        config=t.config,
        webhook_token=t.webhook_token,
        scheduler_job_id=t.scheduler_job_id,
        create_time=t.create_time,
        update_time=t.update_time,
    )


def _build_config(req, existing: Optional[dict] = None) -> dict:
    config = dict(existing or {})
    if req.cron_config:
        config["cron_expr"] = req.cron_config.cron_expr
    if req.webhook_config is not None:
        config["webhook_secret"] = req.webhook_config.webhook_secret
    if req.polling_config:
        config["poll_url"] = req.polling_config.poll_url
        config["poll_interval_seconds"] = req.polling_config.poll_interval_seconds
    return config


def _user_id(current_user: dict) -> str:
    return (current_user.get("data") or {}).get("user_id_str", "unknown")


# ── CRUD ──────────────────────────────────────────────────────────────────────

def trigger_create(req: TriggerCreate, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        now = milliseconds()
        config = _build_config(req)
        webhook_token = secrets.token_hex(32) if req.trigger_type == "webhook" else None

        trigger = TriggerDB(
            space_id=req.space_id,
            trigger_id=str(uuid.uuid4()),
            name=req.name,
            description=req.description,
            trigger_type=req.trigger_type,
            target_type=req.target_type,
            target_id=req.target_id,
            target_version=req.target_version,
            input_payload=req.input_payload,
            is_active=False,  # always starts inactive; user must explicitly activate
            config=config,
            webhook_token=webhook_token,
            create_user=_user_id(current_user),
            update_user=_user_id(current_user),
            create_time=now,
            update_time=now,
        )
        db = SessionLocal()
        try:
            db.add(trigger)
            db.commit()
            db.refresh(trigger)
            return ResponseModel(
                code=status.HTTP_200_OK, message="success", data=_to_detail(trigger)
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[trigger_create] {e}")
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_get(req: TriggerGet, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")
            return ResponseModel(code=status.HTTP_200_OK, message="success", data=_to_detail(trigger))
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_list(req: TriggerList, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            q = db.query(TriggerDB).filter(TriggerDB.space_id == req.space_id)
            if req.trigger_type:
                q = q.filter(TriggerDB.trigger_type == req.trigger_type)
            if req.target_type:
                q = q.filter(TriggerDB.target_type == req.target_type)
            if req.is_active is not None:
                q = q.filter(TriggerDB.is_active == req.is_active)

            total = q.count()
            items = (
                q.order_by(TriggerDB.create_time.desc())
                .offset((req.page - 1) * req.page_size)
                .limit(req.page_size)
                .all()
            )
            return ResponseModel(
                code=status.HTTP_200_OK, message="success",
                data=TriggerListResponse(
                    items=[_to_detail(t) for t in items],
                    total=total,
                    page=req.page,
                    page_size=req.page_size,
                ),
            )
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_update(req: TriggerUpdate, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")

            if req.name is not None:
                trigger.name = req.name
            if req.description is not None:
                trigger.description = req.description
            if req.target_type is not None:
                trigger.target_type = req.target_type
            if req.target_id is not None:
                trigger.target_id = req.target_id
            if req.target_version is not None:
                trigger.target_version = req.target_version
            if req.input_payload is not None:
                trigger.input_payload = req.input_payload

            # Update type-specific config (preserve existing keys not in request)
            trigger.config = _build_config(req, existing=trigger.config)
            trigger.update_user = _user_id(current_user)
            trigger.update_time = milliseconds()

            # If active, re-register the job so the new config takes effect
            if trigger.is_active and trigger.trigger_type in ("cron", "polling"):
                job_id = register_trigger_job(get_scheduler(), trigger)
                trigger.scheduler_job_id = job_id

            db.add(trigger)
            db.commit()
            db.refresh(trigger)
            return ResponseModel(code=status.HTTP_200_OK, message="success", data=_to_detail(trigger))
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_delete(req: TriggerGet, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")
            # Remove from scheduler before DB delete
            remove_trigger_job(get_scheduler(), trigger)
            db.delete(trigger)
            db.commit()
            return ResponseModel(code=status.HTTP_200_OK, message="success", data={})
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_activate(req: TriggerActivate, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")

            trigger.is_active = True
            trigger.update_time = milliseconds()

            if trigger.trigger_type in ("cron", "polling"):
                job_id = register_trigger_job(get_scheduler(), trigger)
                trigger.scheduler_job_id = job_id
            # Webhook triggers have no scheduler job — they are always "listening"
            # as long as is_active=True (the inbound endpoint checks this flag)

            db.add(trigger)
            db.commit()
            db.refresh(trigger)
            return ResponseModel(code=status.HTTP_200_OK, message="success", data=_to_detail(trigger))
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_deactivate(req: TriggerActivate, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")

            trigger.is_active = False
            trigger.update_time = milliseconds()
            remove_trigger_job(get_scheduler(), trigger)
            trigger.scheduler_job_id = None

            db.add(trigger)
            db.commit()
            db.refresh(trigger)
            return ResponseModel(code=status.HTTP_200_OK, message="success", data=_to_detail(trigger))
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_run_manual(req: TriggerGet, current_user: dict, background_tasks: BackgroundTasks) -> ResponseModel:
    """Queue a one-shot manual execution. Returns immediately."""
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            trigger = db.query(TriggerDB).filter(
                TriggerDB.trigger_id == req.trigger_id,
                TriggerDB.space_id == req.space_id,
            ).first()
            if not trigger:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Trigger not found")
            trigger_id = trigger.trigger_id
        finally:
            db.close()

        from openjiuwen_studio.core.scheduler.runner import execute_trigger_job
        background_tasks.add_task(execute_trigger_job, trigger_id, "manual")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Execution queued",
            data=TriggerExecutionLogSummary(
                log_id=0, status="running", trace_id=None, started_at=milliseconds()
            ),
        )
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


# ── Execution Logs ────────────────────────────────────────────────────────────

def _to_log_record(log: TriggerExecutionLogDB) -> TriggerExecutionLogRecord:
    return TriggerExecutionLogRecord(
        id=log.id,
        trigger_id=log.trigger_id,
        trace_id=log.trace_id,
        conversation_id=log.conversation_id,
        status=log.status,
        fired_by=log.fired_by,
        trigger_type=log.trigger_type,
        started_at=log.started_at,
        finished_at=log.finished_at,
        duration_ms=log.duration_ms,
        inputs_snapshot=log.inputs_snapshot,
        outputs=log.outputs,
        error_message=log.error_message,
        poll_hash_seen=log.poll_hash_seen,
        create_time=log.create_time,
    )


def trigger_get_execution_logs(req: TriggerLogsFilter, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            q = db.query(TriggerExecutionLogDB).filter(
                TriggerExecutionLogDB.trigger_id == req.trigger_id,
                TriggerExecutionLogDB.space_id == req.space_id,
            )
            if req.status:
                q = q.filter(TriggerExecutionLogDB.status == req.status)

            total = q.count()
            items = (
                q.order_by(TriggerExecutionLogDB.started_at.desc())
                .offset((req.page - 1) * req.page_size)
                .limit(req.page_size)
                .all()
            )
            return ResponseModel(
                code=status.HTTP_200_OK, message="success",
                data=TriggerLogsResponse(
                    items=[_to_log_record(log_item) for log_item in items],
                    total=total,
                    page=req.page,
                    page_size=req.page_size,
                ),
            )
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


def trigger_get_execution_log_detail(req: TriggerLogDetail, current_user: dict) -> ResponseModel:
    try:
        check_user_space(req.space_id, current_user)
        db = SessionLocal()
        try:
            log = db.query(TriggerExecutionLogDB).filter(
                TriggerExecutionLogDB.id == req.log_id,
                TriggerExecutionLogDB.space_id == req.space_id,
            ).first()
            if not log:
                return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Log not found")
            return ResponseModel(
                code=status.HTTP_200_OK, message="success", data=_to_log_record(log)
            )
        finally:
            db.close()
    except Exception as e:
        return ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))
