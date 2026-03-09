#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
import os
import time
import hashlib
from typing import List, Dict, Any

from concurrent.futures import TimeoutError as FutureTimeoutError
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException, APIRouter, Request
from fastapi.openapi.models import Response
from fastapi.params import Depends, Query
from sqlalchemy.orm import Session
from starlette.concurrency import iterate_in_threadpool
from starlette.responses import StreamingResponse, JSONResponse

from openjiuwen_studio.ops.common.date_time_util import get_china_datetime
from openjiuwen_studio.ops.modules.prompt.application.service import JobService
from openjiuwen_studio.ops.modules.prompt.domain import entities
from openjiuwen_studio.ops.modules.prompt.domain.entities import (
    OptimizeTaskCreationRequest, OptimizeTaskCreationResponse,
    JobInfo, BaseResponse, OptimizeProgressResponse, OptimizeTaskGetInfoResponse,
    JobDraftCreateResponse, OptimizeTaskGetInfoRequest
)

from openjiuwen_studio.ops.modules.prompt.infra.database import get_db_ops
from openjiuwen_studio.ops.modules.prompt.infra.repositories.job_repo import SQLJobRepository
from openjiuwen_studio.ops.modules.llm.llm_config_service import LLMConfigService
from openjiuwen_studio.ops.common.handle_exceptions_util import handle_exceptions
from openjiuwen_studio.routers.prompt_llm_router import get_llm_config_service
from openjiuwen_studio.core.utils.compatible_field import compatible_provider, mask_sensitive_fields
from openjiuwen_studio.core.common.language_thread_context import get_language
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.login_manager.user import get_current_user

from openjiuwen.dev_tools.tune.chat_agent.chat_agent import create_chat_agent_config, create_chat_agent
from openjiuwen.dev_tools.tune.optimizer.joint_optimizer import JointOptimizer
from openjiuwen.dev_tools.tune.evaluator.evaluator import DefaultEvaluator
from openjiuwen.dev_tools.tune.base import Case, EvaluatedCase
from openjiuwen.dev_tools.tune.trainer.base import Progress, Callbacks
from openjiuwen.core.single_agent.legacy import LLMCallConfig
from openjiuwen.core.common.schema import Param
from openjiuwen.core.common.logging import logger
from openjiuwen.core.foundation.llm import ToolCall
from openjiuwen.core.foundation.tool import ToolInfo
from openjiuwen.core.foundation.llm.schema.mode_info import BaseModelInfo
from openjiuwen.core.foundation.tool.function.function import LocalFunction
from openjiuwen.core.foundation.tool import ToolCard
from openjiuwen.core.foundation.llm import Model, ModelRequestConfig, ModelClientConfig  # from ModelConfig
from openjiuwen.dev_tools.tune.trainer.trainer import Trainer
from openjiuwen.dev_tools.tune.dataset.case_loader import CaseLoader
from openjiuwen.dev_tools.prompt_builder.builder.meta_template_builder import MetaTemplateBuilder
from openjiuwen.dev_tools.prompt_builder.builder.feedback_prompt_builder import FeedbackPromptBuilder
from openjiuwen.dev_tools.prompt_builder.builder.badcase_prompt_builder import BadCasePromptBuilder

router = APIRouter(prefix="/api/v1/prompts/tuning", tags=["prompt tuning"])

os.environ.setdefault("LLM_SSL_VERIFY", "false")


def get_job_service(db: Session = Depends(get_db_ops)) -> JobService:
    """ 依赖注入，获取 JobService 实例 """
    job_repo = SQLJobRepository(db)
    return JobService(job_repo)


def process_job_draft_body(body: dict):
    """
    草稿允许body体中desc，optimizeInfo.cases ，rawTemplates字段为空
    """
    if 'optimizeInfo' in body and 'cases' in body['optimizeInfo']:
        for case in body['optimizeInfo']['cases']:
            if 'messages' in case and isinstance(case['messages'], list):
                if not case['messages']:
                    # 如果messages为空，添加空的assistant消息
                    case['messages'] = [{"role": "assistant", "content": ""}]
                else:
                    last_message = case['messages'][-1]
                    if last_message.get('role') != 'assistant':
                        # 最后一条不是assistant，添加空的assistant消息
                        case['messages'].append({"role": "assistant", "content": ""})
    fields_to_check = ['desc', 'rawTemplates']
    for field in fields_to_check:
        if field in body and not body[field]:
            body[field] = " "

    if 'optimizeInfo' in body and isinstance(body['optimizeInfo'], dict):
        if 'cases' in body['optimizeInfo'] and (
                body['optimizeInfo']['cases'] is None or body['optimizeInfo']['cases'] == []):
            del body['optimizeInfo']['cases']


def get_prompt_content(current_prompt):
    """从prompt数据中提取content内容"""
    if isinstance(current_prompt, str):
        return current_prompt
    elif (isinstance(current_prompt, list) and
          current_prompt and
          isinstance(current_prompt[0], dict)):
        return current_prompt[0].get('content', '')
    return str(current_prompt) if current_prompt is not None else ""


class ModelConfigConverter:
    """模型配置转换工具类"""

    @staticmethod
    def convert_to_sdk_format(llm_service: LLMConfigService, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """转换模型配置为SDK所需格式"""
        result = {}
        if not model_info:
            return result

        model_config_info = llm_service.get_llm_model_key_info(
            model_info.get("id", ""), model_info.get("model_from", "")
        )
        model_provider = model_config_info.get("provider", "")

        result["base_url"] = model_config_info.get("base_url", "")
        result["api_key"] = model_config_info.get("api_key", "")
        result["provider"] = model_provider
        result["model_name"] = model_config_info.get("model_name", "")

        # 用户定义参数
        result["params"] = {}
        headers = model_info.get("headers", {})
        result["params"]["temperature"] = headers.get("temperature") if headers.get(
            "temperature", None) is not None else model_config_info["params"]["temperature"]
        result["params"]["top_p"] = headers.get("top_p") if headers.get(
            "top_p", None) is not None else model_config_info["params"]["top_p"]
        result["params"]["timeout"] = headers.get("timeout") if headers.get(
            "timeout", None) is not None else model_config_info["params"]["timeout"]

        logger.info(f"convert_to_sdk_format model config : {mask_sensitive_fields(result)}")
        return result


class OptimizationCallbacks(Callbacks):
    """支持数据库更新的回调类"""

    def __init__(self, job_id: str, job_service: JobService, space_id: str, user_id: str):
        self.history_records = []
        self.job_id = job_id
        self.job_service = job_service
        self.space_id = space_id
        self.user_id = user_id
        self.start_time = time.time()
        super().__init__()

    def on_train_epoch_end(self, agent, progress: Progress, eval_info: List[EvaluatedCase]):
        """每个epoch结束回调"""
        try:
            # 计算耗时
            current_time = time.time()
            time_cost = int(current_time - self.start_time)

            # 获取当前最优提示词
            current_prompt = get_prompt_content(agent.get_llm_calls().get("llm_call").get_system_prompt().content)
            # on_train_end也需要加eval_info
            eval_info_list = []
            for elem in eval_info:
                eval_info_list.append(elem.model_dump())
                logger.info(f"on_train_epoch_end eval_info: {elem.model_dump()}")
            # 构建历史记录
            history_record = {
                "iteration_round": progress.current_epoch,
                "success_rate": float(progress.current_epoch_score),
                "optimized_prompt": current_prompt,
                "evaluate_cases": eval_info_list
            }

            # 计算进度
            progress_rate = min(progress.current_epoch / progress.max_epoch, 0.99)  # 最大99%，留1%给完成状态

            # 准备更新数据
            update_data = {
                "progress_rate": progress_rate,
                "timeCost": time_cost,
                "success_rate": float(progress.best_score),
                "updated_at": get_china_datetime(),
                "status": "running"
            }

            if progress.best_score <= progress.current_epoch_score:
                update_data["bestIteration"] = progress.current_epoch
                update_data["bestTemplates"] = current_prompt

            # 如果有历史记录，更新历史
            if self.history_records:
                self.history_records.append(history_record)
                update_data["history"] = json.dumps(self.history_records)
            else:
                self.history_records = [history_record]
                update_data["history"] = json.dumps(self.history_records)

            logger.info(f"Epoch {progress.current_epoch} 完成 - 最佳分数: {progress.best_score:.4f}, 进度: {progress_rate:.2%}")

            # 更新数据库
            self._update_job_info(update_data)

        except Exception as e:
            logger.warning(f"更新数据库失败: {e}")

    def on_train_end(self, agent, progress: Progress, eval_info: List[EvaluatedCase]):
        """训练结束回调"""
        try:
            total_time = int(time.time() - self.start_time)

            # 最终更新数据
            update_data = {
                "status": "finished",
                "progress_rate": 1.0,
                "timeCost": total_time,
                "updated_at": get_china_datetime(),
                "errorMsg": "job successfully finished",
            }

            eval_info_list = []
            for elem in eval_info:
                eval_info_list.append(elem.model_dump())
                logger.info(f"on_train_end eval_info: {elem.model_dump()}")

            logger.info(f"训练完成! 最终分数: {progress.best_score:.4f}, 总耗时: {total_time}秒")
            self._update_job_info(update_data)

        except Exception as e:
            logger.info(f"训练结束更新数据库失败: {e}")

    def on_train_begin(self, agent, progress: Progress, eval_info: List[EvaluatedCase]):
        """训练结束回调"""
        try:
            total_time = int(time.time() - self.start_time)

            # 最终更新数据
            update_data = {
                "status": "running",
                "progress_rate": 0,
                "timeCost": total_time,
                "updated_at": get_china_datetime(),
                "success_rate": float(progress.current_epoch_score),
            }

            eval_info_list = []
            for elem in eval_info:
                eval_info_list.append(elem.model_dump())
            # 首轮需要填充基线历史
            self.history_records.append({
                "iteration_round": 0,
                "success_rate": float(progress.current_epoch_score),
                "optimized_prompt": "",
                "evaluate_cases": eval_info_list
            })
            update_data["history"] = json.dumps(self.history_records)
            logger.info(f"训练完成! 最终分数: {progress.best_score:.4f}, 总耗时: {total_time}秒")
            self._update_job_info(update_data)

        except Exception as e:
            logger.info(f"训练结束更新数据库失败: {e}")

    def _update_job_info(self, update_data: dict):
        """更新任务信息到数据库"""
        try:
            self.job_service.update_job(
                job_id=self.job_id,
                space_id=self.space_id,
                user_id=self.user_id,
                update_data=update_data
            )
            logger.info(f"数据库更新成功: {list(update_data.keys())}")

        except Exception as e:
            logger.warning(f"数据库更新失败 in _update_job_info: {e}")


class OptimizationTaskExecutor:
    """优化任务执行器"""

    def __init__(self, llm_service: LLMConfigService, app_service: JobService):
        self.llm_service = llm_service
        self.app_service = app_service
        self.config_converter = ModelConfigConverter()  # 添加配置转换器实例
        self.optimization_timeout = 3600 * 12  # 单位秒

    @staticmethod
    def _convert_model_config(llm_service: LLMConfigService, model_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用工具类转换模型配置"""
        return ModelConfigConverter.convert_to_sdk_format(llm_service, model_info)

    @staticmethod
    def _covert_dict_to_sdk_format(original_dict: Dict[str, Any]) -> Dict[str, Any]:
        transformed = {}
        for key, value in original_dict.items():
            if isinstance(value, dict) and "content" in value:
                transformed[key] = value["content"]
            else:
                transformed[key] = value
        return transformed

    @staticmethod
    def _convert_cases_to_sdk_format(cases: List[entities.Case], agent_tools: List[ToolInfo]) -> List[Case]:
        """将前端cases转换为SDK Case格式"""

        sdk_cases = []

        if not cases:
            logger.info("没有需要转换的cases")
            return sdk_cases

        for case in cases:
            try:
                inputs_dict = case.inputs
                label_dict = case.label.copy()  # 创建副本避免修改原数据

                # 检查并转换 tool_calls
                if "tool_calls" in label_dict and "content" in label_dict["tool_calls"]:

                    if isinstance(label_dict["tool_calls"]["content"], str):
                        tool_calls_data = json.loads(label_dict["tool_calls"]["content"])
                    else:
                        tool_calls_data = label_dict["tool_calls"]["content"]

                    if not isinstance(tool_calls_data, list):
                        tool_calls_data = [tool_calls_data]

                    tool_calls_list = []
                    for tool_call_dict in tool_calls_data:
                        tool_call = ToolCall(
                            id="",
                            name=tool_call_dict.get("name", ""),
                            type=tool_call_dict.get("type", "function"),
                            arguments=json.dumps(tool_call_dict.get("arguments", {}))
                        )
                        tool_calls_list.append(tool_call)
                    label_dict["tool_calls"] = tool_calls_list

                # 检查 inputs 和 label 是否为空
                if not inputs_dict or not label_dict:
                    logger.info(f"跳过无效的case: inputs或label为空")
                    continue

                # 构建SDK Case，包含转换后的tools
                sdk_case = Case(
                    inputs=OptimizationTaskExecutor._covert_dict_to_sdk_format(inputs_dict),
                    label=OptimizationTaskExecutor._covert_dict_to_sdk_format(label_dict),
                    tools=agent_tools if agent_tools else None
                )

                sdk_cases.append(sdk_case)

            except Exception as e:
                logger.warning(f"创建SDK Case失败: {e}")
                continue

        logger.info(f"成功转换 {len(sdk_cases)} 个cases")
        return sdk_cases

    @staticmethod
    def _is_nested_type(type):
        return type in ["object", "array"]

    @staticmethod
    def _convert_agent_tools_to_local_function(agent_tools: List[Dict[str, Any]]) -> List[LocalFunction]:
        """将agentTools转换为LocalFunction列表"""

        local_functions = []

        for tool in agent_tools:
            if tool.get("type") != "function":
                continue

            function_data = tool.get("function", {})
            parameters = function_data.get("parameters", {})

            # 解析参数
            properties = parameters.get("properties", {})
            required_list = parameters.get("required", [])

            param_name_list = []
            for field_name, field_schema in properties.items():
                param_name_list.append(field_name)

            tool_card = ToolCard(
                name=function_data.get("name", ""),
                description=function_data.get("description", ""),
                input_params=parameters
            )
            # 验证必选参数都出现在param_name_list中
            missing_required = [req for req in required_list if req not in param_name_list]
            if missing_required:
                logger.warning("缺少必选参数，不转换local funtion")
                continue
            # 创建LocalFunction对象
            local_function = LocalFunction(
                card=tool_card,
                func=lambda a: a
            )

            local_functions.append(local_function)

        logger.info(f"成功转换 {len(local_functions)} 个agent tools")

        return local_functions

    @staticmethod
    def _create_agent(prompt: str, llm_config: Dict[str, Any], tools: List = None):
        """创建聊天Agent"""
        model_client_config = ModelClientConfig(
            client_provider=compatible_provider(llm_config.get("provider")),
            api_base=llm_config.get("base_url"),
            api_key=llm_config.get("api_key"),
            timeout=llm_config.get("params").get("timeout"),
            verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
        )
        model_config = ModelRequestConfig(
            model=llm_config.get("model_name"),
            top_p=llm_config.get("params").get("top_p"),
            temperature=llm_config.get("params").get("temperature"),
            max_tokens=llm_config.get("max_tokens"),
        )

        logger.info(
            f"_create_agent model_config base_url: {model_client_config.api_base} "
            f"model_name: {model_config.model_name}")

        llm_call_config = LLMCallConfig(
            model=model_config,
            model_client=model_client_config,
            system_prompt=[{"role": "system", "content": prompt}],
            user_prompt=[{"role": "user", "content": "{{query}}"}]
        )

        # 创建Agent配置
        config = create_chat_agent_config(
            agent_id='prompt_optimization_agent',
            agent_version='1.0.0',
            description='Prompt Optimization Agent',
            model=llm_call_config
        )

        return create_chat_agent(config, tools)

    @staticmethod
    def _create_trainer(llm_config: Dict[str, Any], optimize_config: Dict[str, Any]):
        """创建训练器"""
        model_client_config = ModelClientConfig(
            client_provider=compatible_provider(llm_config.get("provider")),
            api_base=llm_config.get("base_url"),
            api_key=llm_config.get("api_key"),
            timeout=llm_config.get("params").get("timeout"),
            verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
        )
        model_config = ModelRequestConfig(
            model=llm_config.get("model_name"),
            top_p=llm_config.get("params").get("top_p"),
            temperature=llm_config.get("params").get("temperature"),
            max_tokens=llm_config.get("max_tokens"),
        )

        logger.info(
            f"_create_trainer model_config base_url: {model_client_config.api_base} "
            f"model_name: {model_config.model_name}")

        # 构建评估指标
        metric_parts = []
        if optimize_config.get("user_compare_options"):
            metric_parts.append(optimize_config["user_compare_options"])
        if optimize_config.get("user_compare_rules"):
            metric_parts.append(optimize_config["user_compare_rules"])
        if optimize_config.get("external_knowledge"):
            metric_parts.append(f"背景知识: {optimize_config['external_knowledge']}")

        metric = "\n".join(metric_parts) if metric_parts else "回答需要准确、完整"

        # 创建优化器
        optimizer = JointOptimizer(
            model_config=model_config,
            model_client_config=model_client_config,
            num_examples=optimize_config.get("example_num", 0)
        )

        # 创建评估器
        evaluator = DefaultEvaluator(
            model_config=model_config,
            model_client_config=model_client_config,
            metric=metric
        )
        llm_parallel_num = optimize_config.get("llm_parallel", 1)
        llm_parallel_num = int(llm_parallel_num) \
            if isinstance(llm_parallel_num, (int, float, str)) and llm_parallel_num > 0 else 1
        optimize_config["num_parallel"] = llm_parallel_num
        logger.info(f"_create_trainer optimize_config: {optimize_config}")
        # 创建训练器
        trainer = Trainer(
            evaluator=evaluator,
            optimizer=optimizer,
            **optimize_config
        )

        return trainer

    def _run_optimization_with_timeout(self, task_id: str, creation_info: OptimizeTaskCreationRequest,
                                       space_id: str, user_id: str, model_info: Dict[str, Any],
                                       assistant_info: Dict[str, Any]):
        """带超时的优化任务执行"""
        try:
            # 使用线程池执行优化任务
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._execute_optimization_core,
                    task_id, creation_info, space_id, user_id, model_info, assistant_info
                )

                # 等待任务完成，设置超时时间
                result = future.result(timeout=self.optimization_timeout)
                return result

        except FutureTimeoutError:
            logger.warning(f"优化任务超时: task_id={task_id}, timeout={self.optimization_timeout}s")

            # 更新数据库状态为finished（但标记为超时）
            update_data = {
                "status": "finished",
                "progress_rate": 1.0,
                "updated_at": get_china_datetime(),
                "timeCost": self.optimization_timeout,
                "errorMsg": f"任务执行超时（{self.optimization_timeout}秒）",
            }

            try:
                self.app_service.update_job(
                    job_id=task_id,
                    space_id=space_id,
                    user_id=user_id,
                    update_data=update_data
                )
                logger.info(f"超时任务已更新为finished状态: {task_id}")
            except Exception as db_error:
                logger.warning(f"更新超时任务状态失败: {db_error}")

            return {
                "task_id": task_id,
                "status": "finished",
                "error_message": f"任务执行超时（{self.optimization_timeout}秒）",
                "message": f"优化任务因超时提前结束"
            }
        except Exception as e:
            logger.warning(f"优化任务执行异常: {e}")
            raise

    @staticmethod
    def _build_tool_info(tool):
        return ToolInfo(
            type=tool.card.input_params.get("type", "function"),
            name=tool.card.name,
            description=tool.card.description,
            parameters=tool.card.input_params
        )

    def _execute_optimization_core(self, task_id: str, creation_info: OptimizeTaskCreationRequest,
                                   space_id: str, user_id: str, model_info: Dict[str, Any],
                                   assistant_info: Dict[str, Any]) -> Dict[str, Any]:
        """实际的优化任务执行逻辑（原有的execute_optimization方法内容）"""
        try:

            # 转换agent_tools为ToolInfo列表
            tools = OptimizationTaskExecutor._convert_agent_tools_to_local_function(creation_info.agent_tools)
            tool_info_list = [OptimizationTaskExecutor._build_tool_info(tool) for tool in tools]
            for tool_info in tool_info_list:
                logger.info("tool_info:\n", tool_info.model_dump())

            # 转换cases为SDK格式
            sdk_cases = OptimizationTaskExecutor._convert_cases_to_sdk_format(
                creation_info.optimize_info.cases,
                tool_info_list
            )

            # 创建case loader
            case_loader = CaseLoader(cases=sdk_cases)
            # 创建agent
            agent = OptimizationTaskExecutor._create_agent(
                prompt=creation_info.raw_templates,
                llm_config=assistant_info,
                tools=tools
            )
            # 创建trainer
            trainer = OptimizationTaskExecutor._create_trainer(
                llm_config=model_info,
                optimize_config=creation_info.optimize_info.model_dump()
            )
            # 创建支持数据库更新的回调
            optimization_callbacks = OptimizationCallbacks(
                job_id=task_id,
                job_service=self.app_service,
                space_id=space_id,
                user_id=user_id
            )
            trainer.set_callbacks(optimization_callbacks)

            # 评估原始提示词效果
            initial_score, initial_result = trainer.evaluate(agent, case_loader)

            # 执行优化
            optimized_agent = trainer.train(
                agent,
                case_loader,
                num_iterations=creation_info.optimize_info.num_iter
            )

            # 获取优化后的提示词
            llm_result = optimized_agent.get_llm_calls()
            optimized_prompt = get_prompt_content(llm_result.get("llm_call").get_system_prompt().content)

            # 评估优化后效果
            final_score, final_result = trainer.evaluate(optimized_agent, case_loader)

            return {
                "task_id": task_id,
                "status": "failed",
                "initial_score": initial_score,
                "final_score": final_score,
                "optimized_prompt": optimized_prompt,
                "message": f"优化完成，分数从 {initial_score:.4f} 提升到 {final_score:.4f}"
            }

        except Exception as e:
            logger.error(f"优化任务异常: {e}")
            # 更新任务状态为失败
            try:
                update_data = {
                    "status": "failed",
                    "updated_at": get_china_datetime(),
                    "errorMsg": str(e),
                }
                # 这里调用更新数据库的方法
                self.app_service.update_job(
                    job_id=task_id,
                    space_id=space_id,
                    user_id=user_id,
                    update_data=update_data
                )
            except Exception as db_error:
                logger.error(f"更新失败状态失败: {db_error}")

            return {
                "task_id": task_id,
                "status": "failed",
                "error_message": "execute optimization failed",
                "message": "execute optimization failed"
            }

    def execute_optimization(
            self,
            task_id: str,
            creation_info: OptimizeTaskCreationRequest,
            space_id: str,
            user_id: str,
            model_info: Dict[str, Any],
            assistant_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行优化任务（带超时控制）"""
        return self._run_optimization_with_timeout(
            task_id, creation_info, space_id, user_id, model_info, assistant_info
        )


def generate_optimize_task_job_id(body: dict) -> str:
    """生成基于请求数据和时间戳的任务ID"""
    json_data = json.dumps(body, sort_keys=True)
    timestamp = int(time.time() * 1000)
    sign_str = f"{json_data}|{timestamp}"
    return "JNT_{}".format(hashlib.sha256(sign_str.encode()).hexdigest())


@router.post("/templates_optimization/jobs", response_model=OptimizeTaskCreationResponse)
@handle_exceptions(response_model=OptimizeTaskCreationResponse)
async def prompt_optimize(
        request: Request,
        workspace_id: str = Query(..., title="空间ID"),
        llm_service: LLMConfigService = Depends(get_llm_config_service),
        app_service: JobService = Depends(get_job_service),
        current_user: dict = Depends(get_current_user)
):
    """创建提示词优化任务"""
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]

    # 解析请求体
    body = await request.json()
    creation_info = OptimizeTaskCreationRequest(**body)

    # 生成任务ID
    job_id = generate_optimize_task_job_id(body)

    # 创建任务信息
    create_time = get_china_datetime()

    # 首先在数据库中创建任务记录
    try:
        initial_data = {
            "job_id": job_id,
            "space_id": workspace_id,
            "user_id": user_id,
            "name": creation_info.name,
            "desc": creation_info.desc,
            "rawTemplates": creation_info.raw_templates,
            "optimizeInfo": creation_info.optimize_info.model_dump_json() if creation_info.optimize_info else "{}",
            "modelInfo": creation_info.model_info.model_dump_json() if creation_info.model_info else "{}",
            "assistantInfo": creation_info.assistant_info.model_dump_json() if creation_info.assistant_info else "{}",
            "agentTools": json.dumps(creation_info.agent_tools) if creation_info.agent_tools else "[]",
            "status": "running",
            "progress_rate": 0.0,
            "is_deleted": 0,
            "created_at": create_time,
            "updated_at": create_time
        }

        # 调用服务创建初始记录
        app_service.create_job(initial_data)
        logger.info(f"任务记录创建成功: {job_id}")

    except Exception as e:
        logger.warning(f"创建任务记录失败: {e}")
        return OptimizeTaskCreationResponse(
            code=500,
            msg="Failed to create optimization task due to an internal error.",
            jobInfo=None
        )

    llm_model_info = ModelConfigConverter.convert_to_sdk_format(
        llm_service, creation_info.model_info.model_dump()
    )

    llm_assistant_info = ModelConfigConverter.convert_to_sdk_format(
        llm_service, creation_info.assistant_info.model_dump()
    )

    # 异步执行优化任务
    def run_optimization():
        executor = OptimizationTaskExecutor(llm_service, app_service)
        result = executor.execute_optimization(job_id, creation_info, workspace_id,
                                               user_id, llm_model_info, llm_assistant_info)
        logger.info(f"优化任务执行完成: {job_id}, 结果: {result}")

    # 使用线程池异步执行
    ThreadPoolExecutor().submit(run_optimization)

    # 构建响应
    assistant_model = creation_info.assistant_info.model if creation_info.assistant_info else creation_info.model_info.model

    return OptimizeTaskCreationResponse(
        code=200,
        msg="Template optimize start success.",
        jobInfo=JobInfo(
            id=job_id,
            name=creation_info.name,
            desc=creation_info.desc,
            num_iter=creation_info.optimize_info.num_iter,
            modelInfo=creation_info.model_info,
            assistantInfo=creation_info.assistant_info
        )
    )


@router.get("/templates_optimization/jobs/{job_id}", response_model=OptimizeProgressResponse)
@handle_exceptions(response_model=OptimizeProgressResponse)
def prompt_optimize_progress(
        job_id: str,
        workspace_id: str = Query(..., title="空间ID"),
        service: JobService = Depends(get_job_service),
        current_user: dict = Depends(get_current_user)
):
    """prompt_optimize_progress"""
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    job_info = service.get_job_info(workspace_id, user_id, job_id)

    if job_info is None:
        raise ValueError(f"job_info with user_id {user_id} and space_id: {workspace_id} not found")

    return job_info


@router.post("/templates_optimization/jobs/get_infos", response_model=OptimizeTaskGetInfoResponse)
@handle_exceptions(response_model=OptimizeTaskGetInfoResponse)
def prompt_optimize_progress_list(
        request: OptimizeTaskGetInfoRequest,
        workspace_id: str = Query(..., title="space ID"),
        service: JobService = Depends(get_job_service),
        current_user: dict = Depends(get_current_user)):
    """prompt_optimize_progress_list"""
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    return service.get_jobs(workspace_id, user_id, request.id_list)


@router.delete("/templates_optimization/jobs/{job_id}", response_model=BaseResponse)
@handle_exceptions(response_model=BaseResponse)
def prompt_optimize_delete(job_id: str,
                           workspace_id: str = Query(..., title="space ID"),
                           job_type: str = Query("formal", title="Job typpe"),
                           service: JobService = Depends(get_job_service),
                           current_user: dict = Depends(get_current_user)
                           ):
    """prompt_optimize_delete"""
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    # 删除草稿类型任务
    if job_type == "draft":
        service.del_draft(workspace_id, user_id, job_id)
    else:
        service.del_job(workspace_id, user_id, job_id)

    return BaseResponse(
            code=200,
            msg="Optimization progress delete success."
        )


@router.post("/templates_optimization/job_draft/save", response_model=JobDraftCreateResponse)
@handle_exceptions(response_model=JobDraftCreateResponse)
async def save_draft(request: Request,
               workspace_id: str = Query(..., title="space ID"),
               draft_id: str = Query("", title="Draft ID"),
               service: JobService = Depends(get_job_service),
               current_user: dict = Depends(get_current_user)):
    """用户job任务草稿保存"""
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    body = await request.json()
    process_job_draft_body(body)
    creation_info = OptimizeTaskCreationRequest(**body)
    draft_id = service.save_draft(workspace_id, user_id, draft_id, creation_info)
    return JobDraftCreateResponse(
        code=200,
        msg="job draft save success.",
        draft_id=draft_id
    )


@router.get("/templates_optimization/job_draft/get", response_model=entities.JobDraftResponse)
@handle_exceptions(response_model=entities.JobDraftResponse)
def get_draft(
        workspace_id: str = Query(..., title="space ID"),
        draft_id: str = Query(..., title="Draft ID"),
        service: JobService = Depends(get_job_service),
        current_user: dict = Depends(get_current_user)):
    """
    获取用户job任务草稿
    """
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    draft = service.get_draft(workspace_id, user_id, draft_id)

    if draft is None:
        raise ValueError(f"draft with user_id {user_id} and space_id: {workspace_id} not found")

    return draft


@router.get("/templates_optimization/job_history/{job_id}", response_model=entities.GetOptimizeResponse)
@handle_exceptions(response_model=entities.GetOptimizeResponse)
def get_history(
        job_id: str,
        workspace_id: str = Query(..., title="space ID"),
        page_num: int = Query(default=0, description="页码"),
        page_size: int = Query(default=5, description="每页数量"),
        iteration_round: int = Query(default=None, description="迭代轮次"),
        service: JobService = Depends(get_job_service),
        current_user: dict = Depends(get_current_user)):
    """
    获取用户job任务草稿
    """
    _ = check_user_space(workspace_id, current_user)
    user_id = current_user.get("data")["user_id_str"]
    if iteration_round is None:
        return entities.GetOptimizeResponse(code=404, msg=f"缺少关键参数iteration_round", history=[])
    job_info = service.get_job_info(workspace_id, user_id, job_id)

    if not job_info or not hasattr(job_info, 'history') or not job_info.history:
        return entities.GetOptimizeResponse(history=[])

    history_data = job_info.history

    # 查找指定轮次的数据
    for item in history_data:
        if item.iteration_round == iteration_round:
            # 对找到的item的evaluate_cases进行分页处理
            cases = item.evaluate_cases
            total_cases = len(cases)
            start_idx = (page_num - 1) * page_size
            end_idx = start_idx + page_size

            # 检查分页索引是否超出范围
            if start_idx >= total_cases or start_idx < 0:
                return entities.GetOptimizeResponse(code=400, msg="Page number out of range", history=[])

            paged_cases = cases[start_idx:end_idx]
            item.evaluate_cases = paged_cases
            return entities.GetOptimizeResponse(history=[item])
    if iteration_round <= 1:
        return entities.GetOptimizeResponse(code=200, msg=f"当前提示词已达到目标准确率，未执行优化", history=[])
    return entities.GetOptimizeResponse(code=200, msg=f"未找到iteration_round为{iteration_round}的历史记录", history=[])


async def wrap_sse_generator(original_generator):
    """
    将原始生成器的输出包装成SSE规范格式
    SSE要求每个数据块以"data: "开头，两个换行(\n\n)结尾
    """
    async for content in original_generator:
        if content:
            res = json.dumps({"content": content})
            yield f"data: {res}\n"


@router.post("/build")
@handle_exceptions()
async def prompt_generate(
        request: Request,
        llm_service: LLMConfigService = Depends(get_llm_config_service),
        current_user: dict = Depends(get_current_user)
):
    """prompt一键生成接口"""

    try:
        # 1. 解析请求体
        body = await request.json()

        model_id = body.get("modelInfo", {}).get("id", 1)
        model_from = body.get("modelInfo", {}).get("model_from", "config")
        model_headers = body.get("modelInfo", {}).get("headers", {})

        instruct = body.get("instruct", "")
        stream = body.get("stream", True)
        tools = body.get("tools")
        template_info = body.get("templateInfo", {})
        workspace_id = body.get("workspace_id")
        meta_template_type = template_info.get("metaTemplateType", "general")

        # 2. 参数验证
        _ = check_user_space(workspace_id, current_user)
        if not instruct:
            return JSONResponse(
                content={"error": "instruct parameter is required"},
                status_code=400
            )

        # 3. 根据model_from来源处理模型配置
        if model_from in ["config", "db"]:
            # 使用convert_to_sdk_format获取模型配置
            model_info_dict = {
                "id": model_id,
                "model_from": model_from,
                "headers": model_headers
            }

            llm_config = ModelConfigConverter.convert_to_sdk_format(
                llm_service, model_info_dict
            )

            # 初始化ModelConfig
            model_client_config = ModelClientConfig(
                client_provider=compatible_provider(llm_config.get("provider")),
                api_base=llm_config.get("base_url"),
                api_key=llm_config.get("api_key"),
                timeout=llm_config.get("params").get("timeout"),
                verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
            )
            model_config = ModelRequestConfig(
                model=llm_config.get("model_name"),
                top_p=llm_config.get("params").get("top_p"),
                temperature=llm_config.get("params").get("temperature"),
                max_tokens=llm_config.get("max_tokens"),
            )
            logger.info(f"prompt_generate model_config: {model_config}, model_client_config: {model_client_config}")

        elif model_from == "user":
            # 从用户请求体中提取模型配置
            model_info = body.get("model_info", {})
            model_provider = body.get("model_provider", "")

            if not model_provider:
                return JSONResponse(
                    content={"error": "model_provider is required when model_from is 'user'"},
                    status_code=400
                )

            # 初始化BaseModelInfo
            model_client_config = ModelClientConfig(
                client_provider=compatible_provider(model_info.get("provider", "")),
                api_base=model_info.get("base_url", ""),
                api_key=model_info.get("api_key", ""),
                timeout=model_info.get("params").get("timeout", 60),
                verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
            )
            model_config = ModelRequestConfig(
                model=model_info.get("model_name", ""),
                top_p=model_info.get("params").get("top_p", 0.1),
                temperature=model_info.get("params").get("temperature", 0.95),
                max_tokens=model_info.get("max_tokens", 2000),
            )

        else:
            logger.error(f"Unknown model_from: {model_from}")
            return JSONResponse(
                content={"error": f"Unsupported model_from: {model_from}"},
                status_code=400
            )

        # 4. 初始化MetaTemplateBuilder
        builder = MetaTemplateBuilder(
            model_config=model_config,
            model_client_config=model_client_config,
        )

        # 5. 确定模板类型
        template_type = "general"
        if "plan" in meta_template_type.lower():
            template_type = "plan"
        elif "other" in meta_template_type.lower():
            template_type = "other"

        # 6. 根据stream参数调用不同方法
        if stream:
            # 流式输出
            stream_generator = builder.stream_build(
                prompt=instruct,
                tools=tools,
                template_type=template_type,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
                custom_template_name=meta_template_type if template_type == "other" else None
            )
            sse_stream = wrap_sse_generator(stream_generator)
            return StreamingResponse(
                sse_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式输出
            result = builder.build(
                prompt=instruct,
                tools=tools,
                template_type=template_type,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
                custom_template_name=meta_template_type if template_type == "other" else None
            )
            return JSONResponse(content={
                "content": result,
                "status": "success"
            })

    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": "Invalid JSON format in request body"},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error in prompt_generate: {str(e)}")
        return JSONResponse(
            content={"error": "prompt generate failed"},
            status_code=500
        )


@router.post("/optimize_feedback")
@handle_exceptions()
async def optimize_feedback(
        request: Request,
        llm_service: LLMConfigService = Depends(get_llm_config_service),
        current_user: dict = Depends(get_current_user)
) -> Response:
    """基于反馈优化prompt"""

    try:
        # 1. 解析请求体
        body = await request.json()

        model_id = body.get("modelInfo", {}).get("id", 1)
        model_from = body.get("modelInfo", {}).get("model_from", "config")
        prompt = body.get("prompt", "")
        feedback = body.get("feedback", "")
        mode = body.get("mode", "")  # 可选general，select，insert
        start_pos = body.get("start_pos")
        end_pos = body.get("end_pos")
        stream = body.get("stream", True)
        model_headers = body.get("modelInfo", {}).get("headers", {})
        workspace_id = body.get("workspace_id")

        _ = check_user_space(workspace_id, current_user)

        # 2. 使用convert_to_sdk_format获取模型配置
        model_info_dict = {
            "id": model_id,
            "model_from": model_from,
            "headers": model_headers
        }
        # 3. 获取模型配置
        llm_config = ModelConfigConverter.convert_to_sdk_format(
            llm_service, model_info_dict
        )
        # 4. 初始化FeedbackPromptBuilder
        model_client_config = ModelClientConfig(
            client_provider=compatible_provider(llm_config.get("provider")),
            api_base=llm_config.get("base_url"),
            api_key=llm_config.get("api_key"),
            timeout=llm_config.get("params").get("timeout"),
            verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
        )
        model_config = ModelRequestConfig(
            model=llm_config.get("model_name"),
            top_p=llm_config.get("params").get("top_p"),
            temperature=llm_config.get("params").get("temperature"),
            max_tokens=llm_config.get("max_tokens"),
        )
        logger.info(f"optimize_feedback model_config： {model_config}")
        builder = FeedbackPromptBuilder(
            model_config=model_config,
            model_client_config=model_client_config,
        )

        # 6. 根据stream参数调用不同方法
        if stream:
            # 流式输出
            stream_generator = builder.stream_build(
                prompt=prompt,
                feedback=feedback,
                mode=mode,
                start_pos=start_pos,
                end_pos=end_pos,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
            )
            sse_stream = wrap_sse_generator(stream_generator)
            return StreamingResponse(
                sse_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式输出
            result = builder.build(
                prompt=prompt,
                feedback=feedback,
                mode=mode,
                start_pos=start_pos,
                end_pos=end_pos,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
            )
            return JSONResponse(content={
                "content": result,
                "status": "success"
            })

    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": "Invalid JSON format in request body"},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error in optimize_feedback: {str(e)}")
        return JSONResponse(
            content={"error": "optimize feedback failed"},
            status_code=500
        )


@router.post("/optimize_badcase")
@handle_exceptions()
async def prompt_bad_cases(
        request: Request,
        llm_service: LLMConfigService = Depends(get_llm_config_service),
        current_user: dict = Depends(get_current_user)
) -> Response:
    """基于反馈优化prompt"""
    try:
        # 1. 解析请求体
        body = await request.json()

        model_id = body.get("modelInfo", {}).get("id", 1)
        model_from = body.get("modelInfo", {}).get("model_from", "config")
        prompt = body.get("prompt", "")
        badcases = body.get("badcases", [{}])
        stream = body.get("stream", True)
        model_headers = body.get("modelInfo", {}).get("headers", {})
        workspace_id = body.get("workspace_id")

        _ = check_user_space(workspace_id, current_user)

        cases = []
        for badcase in badcases:
            query, answer = '', ''
            raw_query = badcase.get('query', '')
            if not raw_query or not isinstance(raw_query, str):
                continue
            # 限制输入长度，防止资源耗尽
            if len(raw_query) > 65536:
                raise HTTPException(status_code=400, detail="query field too large")
            try:
                messages = json.loads(raw_query)
            except (json.JSONDecodeError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"query field must be valid JSON: {str(e)}"
                ) from e
            # 结构验证：messages为嵌套列表，内层元素为字典
            if (not isinstance(messages, list) or len(messages) == 0):
                raise HTTPException(status_code=400, detail="query field has invalid message structure")

            last_turn = messages[-1]
            if (not isinstance(last_turn, list) or len(last_turn) == 0):
                raise HTTPException(status_code=400, detail="query field has invalid message structure")
            if not isinstance(last_turn[-1], dict):
                raise HTTPException(status_code=400, detail="query field has invalid message structure")
            if messages[-1][-1].get('role') == 'assistant':
                answer = {'answer': messages[-1][-1].get('content', '')}
            query = str(messages[-1][:-1])
            case = Case(
                inputs={"question": query},  # 用户与agen的多轮问答
                label={"label": ''}          # 用户期望的标准答案
            )
            cases.append(EvaluatedCase(case=case,
                                       reason=badcase.get('label', ''),  # 用户反馈的意见
                                       answer=answer))                  # 优化前大模型生成的结果

        # 2. 使用convert_to_sdk_format获取模型配置
        model_info_dict = {
            "id": model_id,
            "model_from": model_from,
            "headers": model_headers
        }
        # 3. 获取模型配置
        llm_config = ModelConfigConverter.convert_to_sdk_format(
            llm_service, model_info_dict
        )

        # 4. 初始化BadCasePromptBuilder
        model_client_config = ModelClientConfig(
            client_provider=compatible_provider(llm_config.get("provider")),
            api_base=llm_config.get("base_url"),
            api_key=llm_config.get("api_key"),
            timeout=llm_config.get("params").get("timeout"),
            verify_ssl=os.getenv("LLM_SSL_VERIFY", "false").lower() == "true",
        )
        model_config = ModelRequestConfig(
            model=llm_config.get("model_name"),
            top_p=llm_config.get("params").get("top_p"),
            temperature=llm_config.get("params").get("temperature"),
            max_tokens=llm_config.get("max_tokens"),
        )
        logger.info(f"optimize_feedback model_config： {model_config}")
        builder = BadCasePromptBuilder(
            model_config=model_config,
            model_client_config=model_client_config,
        )

        # 6. 根据stream参数调用不同方法
        if stream:
            # 流式输出
            stream_generator = builder.stream_build(
                prompt=prompt,
                cases=cases,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
            )
            sse_stream = wrap_sse_generator(stream_generator)
            return StreamingResponse(
                sse_stream,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式输出
            result = builder.build(
                prompt=prompt,
                cases=cases,
                language="zh-CN" if get_language() in ("zh-cn", "zh") else "en-US",
            )
            return JSONResponse(content={
                "content": result,
                "status": "success"
            })
    except json.JSONDecodeError:
        return JSONResponse(
            content={"error": "Invalid JSON format in request body"},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error in optimize_badcase: {str(e)}")
        return JSONResponse(
            content={"error": "optimize badcase failed"},
            status_code=500
        )

