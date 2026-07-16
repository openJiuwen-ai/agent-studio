# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""
prompt service
"""

import ast
import concurrent
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional, Tuple, Literal

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.security.auth import Auth
from agent_builder.common.status import TaskStatus
from agent_builder.common.utils.utils import convert_string, CODE_FIELD
from agent_builder.prompt.common.config import LLMModelInfo
from agent_builder.prompt.core.optimizer.dataset import BaseCaseData
from agent_builder.prompt.core.optimizer.opt_with_badcase.optimize_with_badcase import (
    OptimizeWithBadcase,
)
from agent_builder.prompt.core.optimizer.opt_with_feedback.optimize_with_feedback import (
    OptimizeWithFeedBack,
)
from agent_builder.prompt.template.prompt_builder import PromptBuilder
from agent_builder.prompt.tune.base.case import CaseManager, CaseValidationException
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.context import JobInfo
from agent_builder.prompt.tune.base.context_manager import ContextManager, StatusChecker
from agent_builder.prompt.tune.base.utils import (
    check_not_none_with_alias,
    calc_run_time,
)
from agent_builder.prompt.tune.joint_optimizer import JointOptimizer
from agent_builder.prompt.tune.service.interface import (
    OptimizeTaskCreationRequest,
    OptimizeTaskGetInfoRequest,
)
from agent_builder.prompt.tune.service.validator import TaskParamsValidator
from agent_builder.serve.common.exception.exception_handler import ExceptionHandler
from agent_builder.serve.common.exception.exceptions import ParamCheckFailedException
from agent_builder.serve.common.exception.exceptions import ResourceNotFoundException
from agent_builder.serve.common.logger.request_logger import (
    log_request_prompt_builder_stats,
)
from flask import (
    request,
    Blueprint,
    Response,
    stream_with_context,
    jsonify,
    copy_current_request_context,
    g,
)
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.check_info import CheckInfo
from agent_builder.adapter.placeholder_editor import PlaceholderEditor
from agent_builder.adapter.task_info import TaskInfo
from pydantic import BaseModel, Field, field_validator, FieldValidationInfo, StrictStr

MIN_CONVERSATION_ID_LENGTH = 1
USER_INSTRUCTION_LENGTH_LIMIT = min(
    int(os.environ.get("PROMPT_INSTRUCTION_LENGTH_LIMIT", 16000)),
    128 * 1000,  # 提示词指令长度
)

# tools limit: maximum of 20, total string length 16K
TOOLS_LENGTH_LIMIT = min(int(os.environ.get("TOOLS_LENGTH_LIMIT", 20)), 40)  # 工具个数
TOOL_STR_LENGTH_LIMIT = min(
    int(os.environ.get("TOOL_STR_LENGTH_LIMIT", 16000)),
    64 * 1000,  # 工具字符串长度
)

DEFAULT_MODEL_LENGTH = min(
    int(os.environ.get("DEFAULT_MODEL_LENGTH", 1024)),
    2048,  # 模型字符串长度
)
DEEP_SEEK_META_LIST = (
    ast.literal_eval(os.environ.get("DEEPSEEK_R1_MODEL_MARK"))
    if os.environ.get("DEEPSEEK_R1_MODEL_MARK")
    else ["deepseek_r1", "deepseek-r1"]
)


class XiaoYiNl2AgentInfo(BaseModel):
    """GenerateInfo"""

    query: str = Field(min_length=1, max_length=USER_INSTRUCTION_LENGTH_LIMIT)
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url=""))
    agentType: Literal["llm_agent", "workflow"] = Field(...)
    agentId: Optional[str] = None
    icon: Optional[str] = None
    iconObsKey: Optional[str] = None
    context: Optional[list] = None
    env: Optional[str] = None


class EiCloudNl2AgentInfo(BaseModel):
    """GenerateInfo"""

    conversationId: StrictStr = Field(min_length=MIN_CONVERSATION_ID_LENGTH)
    query: StrictStr = Field(
        min_length=MIN_CONVERSATION_ID_LENGTH, max_length=USER_INSTRUCTION_LENGTH_LIMIT
    )
    agentType: Literal["llm_agent", "workflow"] = Field(...)
    modelInfo: LLMModelInfo = Field(...)


class MetaTemplateTypeEnum(str, Enum):
    GENERAL_TEMPLATE_XIAOYI = "GeneralTemplate-Xiaoyi"
    PLAN_TEMPLATE_XIAOYI = "PlanTemplate-Xiaoyi"
    DEEPSEEKR1_PLANTEMPLATE_XIAOYI = "DeepSeekR1-PlanTemplate-XiaoYi"


class TemplateInfo(BaseModel):
    """TemplateInfo"""

    metaTemplateType: MetaTemplateTypeEnum = Field(
        default=MetaTemplateTypeEnum.GENERAL_TEMPLATE_XIAOYI
    )


class GenerateInfo(BaseModel):
    """GenerateInfo"""

    instruct: str = Field(min_length=1, max_length=USER_INSTRUCTION_LENGTH_LIMIT)
    tools: Optional[List[dict]] = None
    templateInfo: TemplateInfo = Field(default=TemplateInfo())
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url=""))
    stream: bool = Field(default=True)

    @field_validator("instruct")
    @classmethod
    def check_str_content(cls, value, info: FieldValidationInfo):
        """check str content"""
        return CheckInfo.check_str_content(value, info.field_name)

    @field_validator("tools")
    @classmethod
    def validate_tools_item_length(cls, value):
        """验证 tools 列表整体长度"""
        if not value:
            return value
        if not isinstance(value, list):
            raise ValueError("tools must be list")
        if len(value) > TOOLS_LENGTH_LIMIT:
            raise ValueError(f"tools length exceed limit: {TOOLS_LENGTH_LIMIT}")
        json_str = json.dumps(value, separators=(",", ":"))
        if len(json_str) > TOOL_STR_LENGTH_LIMIT:
            raise ValueError(f"tool info length exceed limit {TOOL_STR_LENGTH_LIMIT}")
        return value

    @field_validator("modelInfo")
    @classmethod
    def validate_model_info_length(cls, value):
        """check modelInfo length"""
        if not value:
            return value
        json_str = json.dumps(value.dict(), separators=(",", ":"))
        item_length = len(json_str)
        if item_length > DEFAULT_MODEL_LENGTH:
            raise ValueError(f"modelInfo length exceed limit {DEFAULT_MODEL_LENGTH}")
        return value


class OptBadCaseInfo(BaseModel):
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url="", token=""))
    prompt: str = Field(min_length=1)
    badcases: Optional[List[dict]] = None
    stream: bool = Field(default=True)
    templateInfo: TemplateInfo = Field(default=TemplateInfo())

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value):
        """validate select content index"""
        if not value.strip():
            raise ValueError("prompt is empty string")
        return value

    @field_validator("badcases")
    @classmethod
    def validate_badcases(cls, value):
        """Validate badcases"""
        if value is not None:
            for badcase in value:
                if not isinstance(badcase, dict):
                    raise ValueError("Each badcase must be a dictionary")
                query = badcase.get("query", "")
                label = badcase.get("label", "")
                if not isinstance(query, str) or not isinstance(label, str):
                    raise ValueError("'query' and 'label' fields should be str")
                if not query.strip() or not label.strip():
                    raise ValueError(
                        "'query' and 'label' fields in badcase cannot be empty"
                    )
        return value


class OptFeedBackInfo(BaseModel):
    modelInfo: LLMModelInfo = Field(default=LLMModelInfo(url="", token=""))
    prompt: str = Field(min_length=1)
    feedback: str = Field(min_length=1, max_length=65535)
    select_content_index: Optional[Tuple[int, int]] = Field(default=None)
    insert_pos_index: Optional[int] = Field(default=None)
    stream: bool = Field(default=True)
    templateInfo: TemplateInfo = Field(default=TemplateInfo())

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, value):
        """validate select content index"""
        if not value.strip():
            raise ValueError("feedback is empty string")
        return value

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value):
        """validate select content index"""
        if not value.strip():
            raise ValueError("prompt is empty string")
        return value

    # 验证 select_content_index 字段
    @field_validator("select_content_index")
    @classmethod
    def validate_select_content_index(cls, value):
        """validate select content index"""
        if value is not None:
            if len(value) != 2:
                raise ValueError("select_content_index should contain two elements")
            start, end = value
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError("select_content_index must be int")
            if start > end:
                raise ValueError("start index is bigger than end index")
        return value

    # 验证 insert_pos_index 字段
    @field_validator("insert_pos_index")
    @classmethod
    def validate_insert_pos_index(cls, value):
        """validate insert pos index"""
        if value is not None and not isinstance(value, int):
            raise ValueError("insert_pos_index should be int")
        return value


prompt_manage_app = Blueprint("prompt_manage_api", __name__)


def get_prompt_builder(meta_template_name, input_info):
    """get_prompt_builder"""
    if "xiaoyi" in meta_template_name:
        editor = PlaceholderEditor()
        return PromptBuilder().initialize(
            model_info=input_info.modelInfo, editor=editor
        )
    return PromptBuilder().initialize(model_info=input_info.modelInfo)


def get_meta_template_name(
    meta_template_type: str, input_info: GenerateInfo, template_mapping: dict
):
    """从用户的元模板类型映射到程序识别的类型"""
    meta_template_name = template_mapping.get(meta_template_type)
    if "Xiaoyi" in meta_template_type and input_info.tools:
        meta_template_name = "xiaoyi_plan_meta_epo"
    supported_tool = ["PlanTemplate-Xiaoyi"]
    if meta_template_type in supported_tool and not input_info.tools:
        raise ParamCheckFailedException(
            f"input value field name: tools check failed! tools is required in "
            f"{meta_template_type}"
        )
    return meta_template_name


def streaming_result_transfer(streaming_result):
    """streaming_result_transfer"""
    try:
        for data in streaming_result:
            if data.get(CODE_FIELD) != 0:
                raise JiuWenBaseException(
                    StatusCode.LLM_CONNECTION_ERROR.code, data.get("message")
                )
            yield json.dumps(data, ensure_ascii=False) + "\n"
    except JiuWenBaseException as e:
        raise e
    except Exception as e:
        raise e


@prompt_manage_app.route("/v1/prompt/build", methods=["POST"])
@ExceptionHandler.catch_exception
@Auth.authenticate
@log_request_prompt_builder_stats(request)
def prompt_generate():
    """prompt_generate"""
    input_info = GenerateInfo(**request.json)

    if not input_info.modelInfo.headers:
        input_info.modelInfo.headers = {}
    request_headers = dict(request.headers)
    input_info.modelInfo.headers = request_headers | input_info.modelInfo.headers

    template_mapping = {
        "GeneralTemplate-Xiaoyi": "xiaoyi_general_meta_epo",
        "PlanTemplate-Xiaoyi": "xiaoyi_plan_meta_epo",
        "DeepSeekR1-PlanTemplate-XiaoYi": "deepseek_r1_xiaoyi_plan_meta_epo",
    }
    for model_mark in DEEP_SEEK_META_LIST:
        if model_mark in input_info.modelInfo.model.lower() and input_info.tools:
            input_info.templateInfo.metaTemplateType = (
                MetaTemplateTypeEnum.DEEPSEEKR1_PLANTEMPLATE_XIAOYI
            )

    if input_info.templateInfo.metaTemplateType not in template_mapping:
        raise ResourceNotFoundException(
            f"Meta template type: {input_info.templateInfo.metaTemplateType} not found"
        )
    meta_template_name = get_meta_template_name(
        input_info.templateInfo.metaTemplateType, input_info, template_mapping
    )
    prompt_builder = get_prompt_builder(meta_template_name, input_info)
    if not input_info.stream:
        raise ParamCheckFailedException("stream params only support true")
    streaming_result = prompt_builder.hmi_streaming_build(
        instruction=input_info.instruct,
        meta_template=meta_template_name,
        tools=input_info.tools,
    )
    return Response(
        stream_with_context(
            streaming_result_transfer(streaming_result=streaming_result)
        ),
        mimetype="text/event-stream",
    )


@prompt_manage_app.route("/v1/prompt/optimize_feedback", methods=["POST"])
@ExceptionHandler.catch_exception
@Auth.authenticate
@log_request_prompt_builder_stats(request)
def optimize_feedback():
    """基于反馈优化"""
    input_info = OptFeedBackInfo(**request.json)
    process_prompt = convert_string(input_info.prompt)
    meta_prompt_name = "opt_feedback_intent_meta"
    meta_optimize_prompts = [
        "opt_feedback_part_modify_meta",
        "opt_feedback_insert_modify_meta",
        "opt_feedback_global_modify_meta",
    ]

    if not input_info.modelInfo.headers:
        input_info.modelInfo.headers = {}
    request_headers = dict(request.headers)
    input_info.modelInfo.headers = request_headers | input_info.modelInfo.headers

    optimizer = OptimizeWithFeedBack(
        input_prompt_list=process_prompt,
        model_info=input_info.modelInfo,
        feedback=input_info.feedback,
        selected_content_index=input_info.select_content_index,
        insert_pos_index=input_info.insert_pos_index,
        meta_prompt_name=meta_prompt_name,
    )
    if input_info.select_content_index is not None:
        output_prompt = optimizer.optimize_with_part(meta_optimize_prompts[0])
    elif input_info.insert_pos_index is not None:
        output_prompt = optimizer.optimize_with_insert(meta_optimize_prompts[1])
    else:
        output_prompt = optimizer.optimize_with_dialog(meta_optimize_prompts[2])
    if not output_prompt:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_FEEDBACK_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_FEEDBACK_ERROR.errmsg.format(
                error_msg="Optimize feedback is unuseful"
            ),
        )
    return Response(
        stream_with_context(streaming_result_transfer(streaming_result=output_prompt)),
        mimetype="text/event-stream",
    )


@prompt_manage_app.route("/v1/prompt/optimize_badcase", methods=["POST"])
@ExceptionHandler.catch_exception
@Auth.authenticate
@log_request_prompt_builder_stats(request)
def optimize_bad_cases():
    """optimize_case"""
    input_info = OptBadCaseInfo(**request.json)
    bad_case_list = []
    for case in input_info.badcases:
        bad_case_list.append(
            BaseCaseData(input=case.get("query"), label=case.get("label"))
        )
    meta_prompt_name = ["opt_generator_badcase_zh_meta", "opt_analyze_badcase_zh_meta"]

    request_headers = dict(request.headers)
    input_info.modelInfo.headers = request_headers | input_info.modelInfo.headers

    process_prompt = convert_string(input_info.prompt)
    opt_bad_case_optimizer = OptimizeWithBadcase(
        input_prompt_list=process_prompt,
        bad_case_list=bad_case_list,
        model_info=input_info.modelInfo,
        meta_prompt_name=meta_prompt_name,
    )
    output_prompt = opt_bad_case_optimizer.run()
    if not output_prompt:
        raise JiuWenBaseException(
            error_code=StatusCode.PROMPT_OPTIMIZE_BAD_CASE_ERROR.code,
            message=StatusCode.PROMPT_OPTIMIZE_BAD_CASE_ERROR.errmsg.format(
                error_msg="Optimize bad case output prompt is empty"
            ),
        )
    return Response(
        stream_with_context(streaming_result_transfer(streaming_result=output_prompt)),
        mimetype="text/event-stream",
    )


def generate_optimize_task_job_id(mode: str = "JNT"):
    """
    Generates a job ID based on the request data and timestamp, with a prefix based on 'is_joint' parameter
    """
    json_data = json.dumps(request.json, sort_keys=True)
    timestamp = int(time.time() * 1000)
    sign_str = f"{json_data}|{timestamp}"
    return f"{mode}_{hashlib.sha256(sign_str.encode()).hexdigest()}"


def prompt_optimize_success(
    template_optimize_info: OptimizeTaskCreationRequest, task_info: TaskInfo
) -> Response:
    """prompt_optimize_success"""
    check_not_none_with_alias(template_optimize_info, "template_optimize_info")
    check_not_none_with_alias(task_info, "task_info")
    assistant_model = (
        template_optimize_info.assistant_info.model
        if template_optimize_info.assistant_info is not None
        else template_optimize_info.model_info.model
    )
    job_info_data = JobInfo(
        id=task_info.task_id,
        name=task_info.name,
        desc=task_info.desc,
        num_iter=template_optimize_info.optimize_info.num_iter,
        created_at=task_info.create_time,
        optimized_model=template_optimize_info.model_info.model,
        assistant_model=assistant_model,
    )
    return jsonify(
        code=200,
        jobInfo=job_info_data.model_dump(),
        message="Template optimize start success.",
    )


@prompt_manage_app.route("/v1/prompt/templates_optimization/jobs", methods=["POST"])
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize():
    """prompt_optimize"""
    if not ContextManager().is_executable():
        return jsonify(
            code=500,
            message="Running optimization task exceeds threshold, please try again later.",
        )
    TaskParamsValidator.validate_task_parameters(request.json)
    OptimizeTaskCreationRequest.strong_field_verification(request.json)
    creation_info = OptimizeTaskCreationRequest(**request.json)
    creation_info.optimize_info.tools = creation_info.agent_tools

    optimizer = JointOptimizer()
    job_id = generate_optimize_task_job_id()

    request_headers = dict(request.headers)
    creation_info.model_info.headers = (
        request_headers | creation_info.model_info.headers
    )
    creation_info.assistant_info.headers = (
        request_headers | creation_info.assistant_info.headers
    )

    progress_info = ContextManager().get(job_id)
    if progress_info is not None:
        return jsonify(code=200, message=f"Optimization task {job_id} already exists.")

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
        run_in_thread, task_info, creation_info, g.__dict__, optimizer
    )
    StatusChecker().add_task(job_id)

    try:
        future.result(timeout=3)
        return prompt_optimize_success(creation_info, task_info)
    except concurrent.futures.TimeoutError:
        # After 3s, exception information could be recorded in error_msg of progress_info.
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


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/jobs/<job_id>", methods=["GET"]
)
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


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/data_check", methods=["POST"]
)
@ExceptionHandler.catch_exception
@Auth.authenticate
def prompt_optimize_cases_validation():
    """prompt_optimize_cases_validation"""
    cases = request.json.get("cases", None)
    try:
        if cases is None:
            raise CaseValidationException("Empty cases")
        CaseManager.validate_with_convert(cases)
    except CaseValidationException as e:
        return jsonify(code=500, message=e.message, error_index=e.error_index)

    return jsonify(
        code=200,
        message="Cases validation success.",
        error_index=TuneConstant.ROOT_CASE_INDEX,
    )


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/jobs/<job_id>", methods=["DELETE"]
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


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/jobs/<job_id>/stop", methods=["POST"]
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


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/jobs/<job_id>/restart", methods=["POST"]
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
        progress_info = ContextManager().load_context(job_id)

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
    optimizer = JointOptimizer()
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


@prompt_manage_app.route(
    "/v1/prompt/templates_optimization/jobs/get_infos", methods=["POST"]
)
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
