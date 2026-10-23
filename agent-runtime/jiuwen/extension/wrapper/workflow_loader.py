#!/usr/bin/env python
# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""Register and cache openjiuwen workflows — conversion delegated to IRConverter."""

from __future__ import annotations

from typing import Any

from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner import Runner

_JIUWEN_IR_PATH_ATTR = "_jiuwen_ir_path"


async def ensure_openjiuwen_workflow_registered(
    workflow_ir: dict,
    *,
    workflow_id: str,
    workflow_name: str = "",
    description: str = "",
    agent_id: str = "",
):
    """Ensure an openjiuwen workflow resource exists for the current workflow/tag.

    Returns a ``LazyWorkflow`` shell — the actual IR -> Workflow graph build is
    deferred to the first ``stream``/``invoke`` call (see ``LazyWorkflow``).

    The shell is resolved through ``aget_or_create_workflow_instance``: for
    published IR the *same* shell is handed out across requests, so the
    expensive ``build_openjiuwen_workflow_from_ir`` runs once per
    (ir_path, IR content) instead of once per request. Cross-request reuse of
    the built graph is safe because execution-time state is sessionized by the
    static_graph_patch set; unpublished IR and the downgraded path still build
    a fresh shell every call.

    The registry entry is still removed-and-reregistered per request so a
    stale entry never outlives the IR it was built from.
    """
    workflow_id = workflow_id or workflow_ir.get("workflowId")
    tag = agent_id or None
    if not workflow_id:
        raise ValueError("workflow_id is required to register openjiuwen workflow")

    _remove_workflow_if_exists(workflow_id, tag)

    from jiuwen.serve.controllers.execution.ir_converter import IRConverter
    from jiuwen.serve.controllers.execution.workflow_instance_cache import (
        aget_or_create_workflow_instance,
    )

    ir_path = _resolve_workflow_ir_path(workflow_ir)
    workflow = await aget_or_create_workflow_instance(
        ir_path,
        workflow_ir,
        build=IRConverter.async_ir_to_workflow,
    )
    _attach_workflow_ir_path(workflow, ir_path)

    result = Runner.resource_mgr.add_workflow(
        card=workflow.card,
        workflow=lambda *args, workflow=workflow, **kwargs: workflow,
        tag=tag,
    )
    if hasattr(result, "is_ok") and not result.is_ok():
        err = result.err() if hasattr(result, "err") else result
        if "resource already exist" not in str(err):
            raise RuntimeError(f"failed to register openjiuwen workflow: {err}")
    return workflow


def _resolve_workflow_ir_path(workflow_ir: dict) -> str:
    if not isinstance(workflow_ir, dict):
        return ""
    return str(workflow_ir.get("ir_path") or workflow_ir.get("irPath") or "")


def _attach_workflow_ir_path(workflow: Any, ir_path: str) -> None:
    if ir_path:
        setattr(workflow, _JIUWEN_IR_PATH_ATTR, ir_path)


def _workflow_matches_ir_path(workflow: Any, ir_path: str) -> bool:
    if not ir_path:
        return True
    return getattr(workflow, _JIUWEN_IR_PATH_ATTR, None) == ir_path


def _remove_workflow_if_exists(workflow_id: str, tag: str | None) -> None:
    try:
        result = Runner.resource_mgr.remove_workflow(workflow_id=workflow_id, tag=tag)
    except TypeError:
        result = Runner.resource_mgr.remove_workflow(workflow_id)
    except Exception as exc:
        if _is_not_found_error(exc):
            return
        raise

    if hasattr(result, "is_ok") and not result.is_ok():
        err = result.err() if hasattr(result, "err") else result
        if not _is_not_found_error(err):
            raise RuntimeError(f"failed to remove stale openjiuwen workflow: {err}")


async def _get_workflow_if_exists(workflow_id: str, tag: str | None):
    try:
        return await Runner.resource_mgr.get_workflow(workflow_id=workflow_id, tag=tag)
    except Exception as exc:
        if "not found" in str(exc).lower() or "not exist" in str(exc).lower():
            return None
        return None


def _is_not_found_error(error: Any) -> bool:
    error_text = str(error).lower()
    return "not found" in error_text or "not exist" in error_text
