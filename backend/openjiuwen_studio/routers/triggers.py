#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

import openjiuwen_studio.core.manager.trigger as mgr
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.core.scheduler.webhook_utils import verify_webhook_signature
from openjiuwen_studio.core.database import SessionLocal
from openjiuwen_studio.models.trigger import TriggerDB
from openjiuwen_studio.schemas.trigger import (
    TriggerCreate, TriggerGet, TriggerUpdate, TriggerActivate,
    TriggerList, TriggerLogsFilter, TriggerLogDetail,
)

# JWT-protected router — mounted at /api/v1/triggers
triggers_router = APIRouter()

# Public router (no JWT) — also mounted at /api/v1/triggers
# Only the /inbound/{webhook_token} path is here
triggers_inbound_router = APIRouter()


@triggers_router.post("/create")
async def trigger_create_api(request: TriggerCreate, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_create(request, current_user)


@triggers_router.post("/list")
async def trigger_list_api(request: TriggerList, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_list(request, current_user)


@triggers_router.post("/get")
async def trigger_get_api(request: TriggerGet, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_get(request, current_user)


@triggers_router.post("/update")
async def trigger_update_api(request: TriggerUpdate, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_update(request, current_user)


@triggers_router.post("/delete")
async def trigger_delete_api(request: TriggerGet, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_delete(request, current_user)


@triggers_router.post("/activate")
async def trigger_activate_api(request: TriggerActivate, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_activate(request, current_user)


@triggers_router.post("/deactivate")
async def trigger_deactivate_api(request: TriggerActivate, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_deactivate(request, current_user)


@triggers_router.post("/run")
async def trigger_run_api(request: TriggerGet, background_tasks: BackgroundTasks,
                          current_user: dict = Depends(get_current_user)):
    return mgr.trigger_run_manual(request, current_user, background_tasks)


@triggers_router.post("/execution_logs")
async def trigger_execution_logs_api(request: TriggerLogsFilter, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_get_execution_logs(request, current_user)


@triggers_router.post("/execution_log_detail")
async def trigger_execution_log_detail_api(request: TriggerLogDetail, current_user: dict = Depends(get_current_user)):
    return mgr.trigger_get_execution_log_detail(request, current_user)


# ── Public webhook inbound receiver ──────────────────────────────────────────

@triggers_inbound_router.get("/inbound/{webhook_token}")
async def webhook_inbound(
    webhook_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Public endpoint — no JWT. Accepts inbound webhooks.
    Always returns 200 (even for unknown tokens) to prevent token enumeration.
    """
    db = SessionLocal()
    try:
        trigger: TriggerDB = (
            db.query(TriggerDB)
            .filter(
                TriggerDB.webhook_token == webhook_token,
                TriggerDB.is_active.is_(True),
            )
            .first()
        )
        if not trigger:
            # Return 200 — do not leak whether this token exists
            return {"status": "accepted"}

        # Optional HMAC validation
        secret = (trigger.config or {}).get("webhook_secret")
        if secret:
            body = await request.body()
            sig_header = request.headers.get("X-Hub-Signature-256", "")
            if not verify_webhook_signature(body, sig_header, secret):
                raise HTTPException(status_code=403, detail="Invalid signature")

        trigger_id = trigger.trigger_id
    finally:
        db.close()

    from openjiuwen_studio.core.scheduler.runner import execute_trigger_job
    background_tasks.add_task(execute_trigger_job, trigger_id, "webhook")
    return {"status": "accepted"}
