# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import concurrent
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.security.auth import Auth
from agent_builder.common.status import TaskStatus
from agent_builder.prompt.mmapo.VQA_apo import ApoOptimizer
from agent_builder.prompt.mmapo.validator import ApoTaskParamsValidator
from agent_builder.prompt.tune.base.context_manager import ContextManager
from agent_builder.prompt.tune.base.context_manager import MMAPO_MODE, StatusChecker
from agent_builder.prompt.tune.base.utils import calc_run_time
from agent_builder.prompt.tune.service.interface import (
    OptimizeTaskCreationRequest,
    OptimizeTaskGetInfoRequest,
)
from agent_builder.serve.apis.prompt import (
    generate_optimize_task_job_id,
    prompt_optimize_success,
)
from agent_builder.serve.common.exception.exception_handler import ExceptionHandler
from flask import request, Blueprint, copy_current_request_context, g, jsonify
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.task_info import TaskInfo

mmapo_app = Blueprint("mmapo_api", __name__)


@mmapo_app.route("/v1/MMprompt/templates_optimization/jobs", methods=["POST"])
@ExceptionHandler.catch_exception
def prompt_optimization():
    """prompt_optimization"""
    if not ContextManager().is_executable(mode=MMAPO_MODE):
        return jsonify(
            code=500,
            message="Running mmapo optimization task exceeds threshold, please try again later.",
        )
    ApoTaskParamsValidator.validate_task_parameters(request.json)
    OptimizeTaskCreationRequest.strong_field_verification(request.json)
    creation_info = OptimizeTaskCreationRequest(**request.json)
    creation_info.optimize_info.optimize_method = MMAPO_MODE
    apo_optimizer = ApoOptimizer()
    job_id = generate_optimize_task_job_id(mode=MMAPO_MODE)

    if not creation_info.model_info.headers:
        creation_info.model_info.headers = {}
    if not creation_info.assistant_info.headers:
        creation_info.assistant_info.headers = {}
    request_headers = dict(request.headers)
    creation_info.model_info.headers = (
        request_headers | creation_info.model_info.headers
    )
    creation_info.assistant_info.headers = (
        request_headers | creation_info.assistant_info.headers
    )

    create_time = datetime.now(tz=timezone(timedelta(hours=8))).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    task_info = TaskInfo(job_id, creation_info.name, creation_info.desc, create_time)

    @copy_current_request_context
    def run_in_thread(task_info, creation_info, g_info, optimizer):
        for k, v in g_info.items():
            g.setdefault(k, v)

        return optimizer.do_optimize(
            task_info,
            [creation_info.raw_templates],
            creation_info.optimize_info,
            creation_info.model_info,
            creation_info.assistant_info,
        )

    executor = ThreadPoolExecutor()
    future = executor.submit(
        run_in_thread, task_info, creation_info, g.__dict__, apo_optimizer
    )
    StatusChecker().add_task(job_id)
    try:
        future.result(timeout=3)
        return prompt_optimize_success(creation_info, task_info)
    except concurrent.futures.TimeoutError:
        return prompt_optimize_success(creation_info, task_info)
    except Exception as e:
        error_msg = (
            str(e) if isinstance(e, JiuWenBaseException) else "non-standard exception"
        )
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_START_TASK_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_START_TASK_ERROR.errmsg.format(
                error_msg=f"{error_msg}"
            ),
        ) from e


@mmapo_app.route("/v1/MMprompt/templates_optimization/jobs/get_infos", methods=["POST"])
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_progress_list():
    """prompt_optimize_progress_list"""
    query_info = OptimizeTaskGetInfoRequest(**request.json)
    return jsonify(
        code=200,
        message="Optimization progress list query success.",
        job_details=ContextManager().get_batch_task_info(query_info.id_list),
    )


@mmapo_app.route("/v1/MMprompt/templates_optimization/jobs/<job_id>", methods=["GET"])
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_progress(job_id: str):
    """prompt_optimize_progress"""
    try:
        task_status = TaskStatus.TASK_FAILED
        progress_info = ContextManager().get(job_id)
        if progress_info:
            task_status = ContextManager().get_context_attr(
                job_id, TaskStatus.TASK_STATUS, from_store=True
            )
            if task_status not in (TaskStatus.TASK_FINISHED, TaskStatus.TASK_FAILED):
                progress_info["run_time"] = calc_run_time(progress_info["create_time"])
        info = ContextManager().get_task_info(job_id, task_status)
        return jsonify(
            code=200,
            message="Optimization progress query success.",
            progress=info.get("progress"),
            history=info.get("history"),
        )
    except Exception as e:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.errmsg,
        ) from e


@mmapo_app.route(
    "/v1/MMprompt/templates_optimization/jobs/<job_id>/stop", methods=["POST"]
)
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_stop(job_id: str):
    """prompt_optimize_stop"""
    status = ContextManager().get_context_attr(job_id, TaskStatus.TASK_STATUS)
    if not status:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.errmsg,
        )

    if status != TaskStatus.TASK_RUNNING:
        err_msg = "optimization progress already {}".format(status)
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED_ERROR.errmsg.format(
                error_msg=err_msg
            ),
        )

    ContextManager().set_context_attr(
        job_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_STOPPING
    )
    return jsonify(code=200, message="Optimization progress stop success.")


@mmapo_app.route(
    "/v1/MMprompt/templates_optimization/jobs/<job_id>/restart", methods=["POST"]
)
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_restart(job_id: str):
    """prompt_optimize_restart"""
    if not ContextManager().is_executable():
        return jsonify(
            code=500,
            message="Running optimization task exceeds threshold, please try again later.",
        )
    progress_info = ContextManager().get(job_id)
    if ContextManager().has_store():
        if progress_info:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_RESTART_TASK_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_RESTART_TASK_ERROR.errmsg.format(
                    error_msg=f"Task-{job_id} is still running, please wait."
                ),
            )
        progress_info = ContextManager().load_context(job_id, mode=MMAPO_MODE)

    if progress_info is None:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.errmsg,
        )

    request_headers = dict(request.headers)
    progress_info["model_info"].headers = (
        progress_info["model_info"].headers | request_headers
    )
    progress_info["assistant_info"].headers = (
        progress_info["assistant_info"].headers | request_headers
    )

    task_status = progress_info[TaskStatus.TASK_STATUS]
    if task_status not in (TaskStatus.TASK_STOPPED, TaskStatus.TASK_FAILED):
        err_msg = f"Cannot restart a {task_status} task, task id: {job_id}"
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_STATUS_NOT_EXPECTED_ERROR.errmsg.format(
                error_msg=err_msg
            ),
        )

    if not ContextManager().has_store():
        progress_info = ContextManager().get_checkpoint(job_id)
    progress_info[TaskStatus.TASK_STATUS] = TaskStatus.TASK_RUNNING
    ContextManager().set_checkpoint(job_id, progress_info)

    @copy_current_request_context
    def run_in_thread(job_id, g_info, optimizer):
        for k, v in g_info.items():
            g.setdefault(k, v)
        return optimizer.continue_optimize(job_id)

    executor = ThreadPoolExecutor()
    optimizer = ApoOptimizer()
    future = executor.submit(run_in_thread, job_id, g.__dict__, optimizer)
    StatusChecker().add_task(job_id)

    try:
        future.result(timeout=3)
        return jsonify(code=200, message="Optimization progress restart success.")
    except concurrent.futures.TimeoutError:
        # After 3s, exception information could be recorded in error_msg of progress_info.
        return jsonify(code=200, message="Optimization progress restart success.")
    except Exception as e:
        error_msg = (
            str(e) if isinstance(e, JiuWenBaseException) else "non-standard exception"
        )
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_RESTART_TASK_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_RESTART_TASK_ERROR.errmsg.format(
                error_msg=f"{error_msg}"
            ),
        ) from e


@mmapo_app.route(
    "/v1/MMprompt/templates_optimization/jobs/<job_id>", methods=["DELETE"]
)
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_delete(job_id: str):
    """prompt_optimize_delete"""
    status = ContextManager().get_context_attr(job_id, TaskStatus.TASK_STATUS)
    if not status:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_JOB_NOT_FOUND_ERROR.errmsg,
        )

    # 禁止删除运行中的任务
    if status in (TaskStatus.TASK_RUNNING, TaskStatus.TASK_STOPPING):
        return jsonify(code=500, message="Cannot delete running optimization task.")

    ContextManager().delete(job_id, delete_store=True)
    return jsonify(code=200, message="Optimization progress delete success.")
