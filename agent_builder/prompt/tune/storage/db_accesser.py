# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agent builder chain Template optimizer
"""

import json
from typing import List, Dict, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.common.store.db import DBUtil, DBTable
from agent_builder.prompt.mmapo.utils import ApoParams, JNT_MODE
from agent_builder.prompt.tune.base.case import Case
from agent_builder.prompt.tune.base.context import History
from agent_builder.prompt.tune.base.utils import (
    OptimizeInfo,
    LLMModelInfo,
    JointParams,
    placeholder_to_dict,
)
from agent_builder.common.status import TaskStatus
from agent_builder.common.store.dialect import GaussDBDialect
from agent_builder.prompt.tune.storage.base import BaseContextStoreAccesser
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.json_utils import safe_json_loads_raise_exception


class DBConstant:
    """database constants"""

    """ table name"""
    JOB_INFO_TABLE = "job_info"
    OPTIMIZE_INFO_TABLE = "optimize_info"
    PROGRESS_TABLE = "progress"
    HISTORY_TABLE = "history"
    CASES_TABLE = "cases"

    """ table column fields """
    JOB_INFO_COLUMNS: List[DBTable.Field] = [
        DBTable.Field(name="id", type="VARCHAR(256)"),
        DBTable.Field(name="name", type="VARCHAR(256)"),
        DBTable.Field(name="desc", type="VARCHAR(256)"),
        DBTable.Field(name="num_iter", type="INT"),
        DBTable.Field(name="created_at", type="TEXT"),
        DBTable.Field(name="optimized_model_name", type="VARCHAR(128)"),
        DBTable.Field(name="optimized_model_source", type="VARCHAR(128)"),
        DBTable.Field(name="optimized_model_url", type="VARCHAR(128)"),
        DBTable.Field(name="optimized_model_token", type="VARCHAR(128)"),
        DBTable.Field(name="assistant_model_name", type="VARCHAR(128)"),
        DBTable.Field(name="assistant_model_source", type="VARCHAR(128)"),
        DBTable.Field(name="assistant_model_url", type="VARCHAR(128)"),
        DBTable.Field(name="assistant_model_token", type="VARCHAR(128)"),
    ]

    OPTIMIZE_INFO_COLUMNS: List[DBTable.Field] = [
        DBTable.Field(name="id", type="VARCHAR(256)"),
        DBTable.Field(name="num_iter", type="INT"),
        DBTable.Field(name="llm_parallel", type="INT"),
        DBTable.Field(name="example_num", type="INT"),
        DBTable.Field(name="cot_example_num", type="INT"),
        DBTable.Field(name="optimize_method", type="VARCHAR(128)"),
        DBTable.Field(name="base_prompt", type="TEXT"),
        DBTable.Field(name="placeholders", type="TEXT"),
        DBTable.Field(name="evaluation_method", type="VARCHAR(128)"),
        DBTable.Field(name="tools", type="TEXT"),
        DBTable.Field(name="extra_data", type="TEXT"),
    ]

    CASES_COLUMNS: List[DBTable.Field] = [
        DBTable.Field(name="id", type="VARCHAR(256)"),
        DBTable.Field(name="cases", type="TEXT"),
    ]

    PROGRESS_COLUMNS: List[DBTable.Field] = [
        DBTable.Field(name="id", type="VARCHAR(256)"),
        DBTable.Field(name="base_instruction", type="TEXT"),
        DBTable.Field(name="best_prompt", type="TEXT"),
        DBTable.Field(name="best_placeholder", type="TEXT"),
        DBTable.Field(name="examples", type="TEXT"),
        DBTable.Field(name="cot_examples", type="TEXT"),
        DBTable.Field(name="filled_prompt", type="TEXT"),
        DBTable.Field(name="success_rate", type="FLOAT"),
        DBTable.Field(name="error_msg", type="TEXT"),
        DBTable.Field(name="progress_rate", type="FLOAT"),
        DBTable.Field(name="time_cost", type="INT"),
        DBTable.Field(name="status", type="VARCHAR(64)"),
        DBTable.Field(name="iteration_round", type="INT"),
        DBTable.Field(name="answer_format", type="TEXT"),
        DBTable.Field(name="task_description", type="TEXT"),
        DBTable.Field(name="opt_placeholder", type="TEXT"),
        DBTable.Field(name="sampled_error_case", type="TEXT"),
    ]

    HISTORY_COLUMNS: List[DBTable.Field] = [
        DBTable.Field(name="id", type="VARCHAR(256)"),
        DBTable.Field(name="optimized_prompt", type="TEXT"),
        DBTable.Field(name="optimized_placeholder", type="TEXT"),
        DBTable.Field(name="examples", type="TEXT"),
        DBTable.Field(name="cot_examples", type="TEXT"),
        DBTable.Field(name="filled_prompt", type="TEXT"),
        DBTable.Field(name="success_rate", type="FLOAT"),
        DBTable.Field(name="iteration_round", type="INT"),
        DBTable.Field(name="evaluations", type="TEXT"),
    ]


class DbContextAccesser(BaseContextStoreAccesser):
    """DbContextAccesser"""

    def __init__(self):
        super().__init__()
        self._job_info_table = DBTable(
            table_name=DBConstant.JOB_INFO_TABLE,
            fields=DBConstant.JOB_INFO_COLUMNS,
            primary_keys=["id"],
        )
        self._optimize_info_table = DBTable(
            table_name=DBConstant.OPTIMIZE_INFO_TABLE,
            fields=DBConstant.OPTIMIZE_INFO_COLUMNS,
            primary_keys=["id"],
        )
        self._cases_table = DBTable(
            table_name=DBConstant.CASES_TABLE,
            fields=DBConstant.CASES_COLUMNS,
            primary_keys=["id"],
        )
        self._progress_table = DBTable(
            table_name=DBConstant.PROGRESS_TABLE,
            fields=DBConstant.PROGRESS_COLUMNS,
            primary_keys=["id"],
        )
        self._history_table = DBTable(
            table_name=DBConstant.HISTORY_TABLE,
            fields=DBConstant.HISTORY_COLUMNS,
            primary_keys=["id", "iteration_round"],
        )
        self._available_table_fields = set()
        self._available_table_fields.update(
            {field.name for field in self._job_info_table.fields}
        )
        self._available_table_fields.update(
            {field.name for field in self._optimize_info_table.fields}
        )
        self._available_table_fields.update(
            {field.name for field in self._cases_table.fields}
        )
        self._available_table_fields.update(
            {field.name for field in self._progress_table.fields}
        )
        self._available_table_fields.update(
            {field.name for field in self._history_table.fields}
        )
        DBUtil.instance()

    def store_context_ids(self, ctx_ids: List[str]):
        """save context ids to store
        Args:
            ctx_ids: context uid
        """
        pass

    def store_context(self, ctx_id: str, context: Dict[str, Any]):
        """store context to database"""

        job_info = dict(
            id=ctx_id,
            name=context["name"],
            desc=context["desc"],
            num_iter=context["optimize_info"].num_iter,
            created_at=context["create_time"],
            optimized_model_name=context["model_info"].model,
            optimized_model_source=context["model_info"].model_source,
            optimized_model_url=context["model_info"].url,
            optimized_model_token="",
            assistant_model_name=context["assistant_info"].model,
            assistant_model_source=context["assistant_info"].model_source,
            assistant_model_url=context["assistant_info"].url,
            assistant_model_token="",
        )
        self._job_info_table.insert(job_info)

        tools = (
            json.dumps(context["optimize_info"].tools, ensure_ascii=False)
            if isinstance(context["optimize_info"].tools, list)
            else context["optimize_info"].tools
        )

        extra_data: dict[str, Any] = dict(
            user_compare_options=context["optimize_info"].user_compare_options,
            early_stop_score=context["optimize_info"].early_stop_score,
            optimize_algo=context["optimize_info"].optimize_algo,
            external_knowledge=context["optimize_info"].external_knowledge,
            user_compare_rules=context["optimize_info"].user_compare_rules,
        )

        optimize_info = dict(
            id=ctx_id,
            num_iter=context["optimize_info"].num_iter,
            llm_parallel=context["optimize_info"].llm_parallel,
            example_num=context["optimize_info"].example_num,
            cot_example_num=context["optimize_info"].cot_example_num,
            optimize_method=context["optimize_info"].optimize_method,
            base_prompt=context["raw_templates"][0],
            placeholders=json.dumps(
                context["optimize_info"].placeholder, ensure_ascii=False
            ),
            evaluation_method=context["optimize_info"].eval_mode,
            tools=tools,
            extra_data=json.dumps(extra_data, ensure_ascii=False),
        )
        self._optimize_info_table.insert(optimize_info)

        cases_data = [case.model_dump() for case in context["optimize_info"].cases]
        cases = dict(id=ctx_id, cases=json.dumps(cases_data, ensure_ascii=False))
        self._cases_table.insert(cases)

        if "params" in context:
            progress = dict(
                id=ctx_id,
                base_instruction=context["params"].base_instruction,
                best_prompt=context["params"].full_prompt,
                best_placeholder=json.dumps(
                    context["params"].placeholder, ensure_ascii=False
                ),
                examples=json.dumps(context["params"].examples, ensure_ascii=False),
                cot_examples=json.dumps(
                    context["params"].cot_examples, ensure_ascii=False
                ),
                filled_prompt=context["params"].filled_instruction,
                success_rate=context["scores"][0],
                error_msg=context["error_msg"],
                progress_rate=context["progress_rate"],
                time_cost=context["run_time"],
                status=context["status"],
                iteration_round=context["iter_num"],
                answer_format=context["params"].answer_format,
                task_description=context["params"].task_description,
                opt_placeholder=self._serialize_list_to_string(
                    context["params"].opt_schema
                ),
                sampled_error_case=json.dumps(
                    context["sampled_incorrect_data"], ensure_ascii=False
                ),
            )
            iteration_round = context.get("iter_num")
            history = context.get("history")
            if (
                not self._history_table.exists(
                    id=ctx_id, iteration_round=iteration_round
                )
                and history
            ):
                history_tmp: History = context["history"][-1]
                history = dict(
                    id=ctx_id,
                    optimized_prompt=history_tmp.optimized_prompt,
                    optimized_placeholder=json.dumps(
                        history_tmp.optimized_placeholder, ensure_ascii=False
                    ),
                    examples=self._serialize_list_to_string(history_tmp.examples),
                    cot_examples="",
                    filled_prompt=history_tmp.filled_prompt,
                    success_rate=history_tmp.success_rate,
                    iteration_round=history_tmp.iteration_round,
                    evaluations=json.dumps(history_tmp.evaluations, ensure_ascii=False),
                )
                self._history_table.insert(history)
        else:
            progress = dict(
                id=ctx_id,
                base_instruction="",
                best_prompt="",
                best_placeholder=json.dumps([], ensure_ascii=False),
                examples="",
                cot_examples="",
                filled_prompt="",
                success_rate=context["scores"][0],
                error_msg=context["error_msg"],
                progress_rate=context["progress_rate"],
                time_cost=context["run_time"],
                status=context["status"],
                iteration_round=0,
                answer_format="",
                task_description="",
                opt_placeholder="",
                sampled_error_case=json.dumps([], ensure_ascii=False),
            )
        self._progress_table.insert(progress)

    def load_context(
        self, ctx_id: str, load_all: bool = False, mode: str = JNT_MODE
    ) -> Dict[str, Any]:
        """load context from database"""
        context = dict()
        try:
            result = self._job_info_table.query(id=ctx_id)
            self._load_job_info(context, result)

            result = self._optimize_info_table.query(id=ctx_id)
            self._load_optimize_info(context, result)

            if load_all:
                result = self._cases_table.query(id=ctx_id)
                self._load_cases(context, result)

            result = self._progress_table.query(id=ctx_id)
            self._load_progress(context, result, mode)

            results = self._history_table.batch_query(id=ctx_id)
            self._load_history_table(context, results)
            return context
        except Exception as e:
            raise e

    def get_context_attr(self, ctx_id: str, attr_name: str, **kwargs) -> Any:
        if attr_name not in self._available_table_fields:
            raise AttributeError(f"{attr_name} is not available")
        """query context attribute from store"""
        table_name = kwargs.get("table_name", "progress")
        if table_name == "progress":
            result = self._progress_table.query(target=attr_name, id=ctx_id)
        elif table_name == "job_info":
            result = self._job_info_table.query(target=attr_name, id=ctx_id)
        else:
            result = {}
        return result.get(attr_name, None)

    def set_context_attr(self, ctx_id: str, attr_name: str, attr_value: Any, **kwargs):
        """update context attribute from store"""
        self._progress_table.update(attr_name, attr_value, id=ctx_id)

    def delete_context(self, ctx_id: str):
        """delete context from database"""
        self._job_info_table.delete(id=ctx_id)
        self._optimize_info_table.delete(id=ctx_id)
        self._cases_table.delete(id=ctx_id)
        self._progress_table.delete(id=ctx_id)
        self._history_table.delete(id=ctx_id)

    def init_db(self):
        """initialize database"""
        self._job_info_table.create()
        self._optimize_info_table.create()
        self._cases_table.create()
        self._progress_table.create()
        self._history_table.create()
        logger.info("init db success")

    def fix_stale_tasks(self):
        """Fix stale running/stopping tasks left from previous process crash/restart"""
        d = self._job_info_table.dialect
        q = d.quote
        stale_statuses = (TaskStatus.TASK_RUNNING, TaskStatus.TASK_STOPPING)
        for status in stale_statuses:
            sql = (
                f"UPDATE {q(DBConstant.PROGRESS_TABLE)} "
                f"SET {q('status')} = '{TaskStatus.TASK_FAILED}' "
                f"WHERE {q('status')} = '{status}'"
            )
            try:
                DBUtil.execute(sql, fetch_all=False)
            except Exception as e:
                logger.warning(f"Failed to fix stale tasks with status={status}: {e}")

    def update_column_type(self, table_name: str, column_name: str, new_type: str):
        """update column type"""
        if not table_name or not column_name or not new_type:
            logger.warning("The table_name, column_name, and new_type cannot be empty.")
            return

        d = self._job_info_table.dialect
        describe_sql = d.describe_column_type_sql(table_name, column_name)

        if isinstance(d, GaussDBDialect):
            check_sql = (
                "SELECT COUNT(*) FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' AND column_name = '{column_name}'"
            )
            result = DBUtil.execute(check_sql)
            if not result or result[0][0] == 0:
                logger.warning("The column name does not exist in the table.")
                return

        try:
            type_result = DBUtil.execute(describe_sql, fetch_all=False)
            if not type_result:
                logger.warning(
                    f"Unable to retrieve the current type of the column {column_name}."
                )
                return
            if isinstance(d, GaussDBDialect):
                current_type = str(type_result[0])
            else:
                current_type = None
                for row in (type_result if isinstance(type_result, list) else [type_result]):
                    if isinstance(row, (tuple, list)) and row[0] == column_name:
                        current_type = row[1]
                        break
                if current_type is None:
                    logger.warning(
                        f"Unable to retrieve the current type of the column {column_name}."
                    )
                    return
        except Exception:
            logger.warning(
                f"Failed to retrieve the type of column {column_name}. Skipping."
            )
            return

        if current_type.strip().upper() == new_type.strip().upper():
            logger.info(
                f"Column {table_name}.{column_name} already has been type '{new_type}'. Skipping update."
            )
            return

        try:
            alter_sql = d.alter_column_type_sql(table_name, column_name, new_type)
            DBUtil.execute(alter_sql)
            logger.info(
                f"Successfully updated the column '{column_name}' in table '{table_name}'"
            )
        except Exception as e:
            logger.warning(f"Update failed: {e}")

    def _load_history_table(
        self, context: Dict[str, Any], results: List[Dict[str, Any]]
    ) -> History:
        """load history table"""
        history_list = []
        for hist_result in results:
            history: History = History()
            history.optimized_prompt = hist_result["optimized_prompt"]
            history.optimized_placeholder = safe_json_loads_raise_exception(
                hist_result["optimized_placeholder"]
            )
            history.original_placeholder = placeholder_to_dict(
                context.get("optimize_info").placeholder, True
            )
            history.examples = self._deserialize_string_to_list(hist_result["examples"])
            history.filled_prompt = hist_result["filled_prompt"]
            history.success_rate = hist_result["success_rate"]
            history.iteration_round = hist_result["iteration_round"]
            history.evaluations = json.loads(hist_result["evaluations"])
            history_list.append(history)

        context["history"] = history_list

    def _load_progress(
        self, context: Dict[str, Any], result: Dict[str, Any], mode: str = JNT_MODE
    ) -> None:
        """load progress from store"""
        if not result:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="load empty progress"
                ),
            )
        if result.get("iteration_round") != 0 or result.get("base_instruction"):
            if mode == JNT_MODE:
                params = JointParams()
                context["params"] = params
                params.example_num = context.get("optimize_info").example_num
                params.cot_example_num = context.get("optimize_info").cot_example_num
                params.placeholder = json.loads(result.get("best_placeholder"))
                params.opt_schema = self._deserialize_string_to_list(
                    result.get("opt_placeholder")
                )
                params.examples = json.loads(result.get("examples")) or []
                params.cot_examples = json.loads(result.get("cot_examples")) or []
                params.task_description = result.get("task_description")
                params.original_placeholder = context.get("optimize_info").placeholder
                params.answer_format = result.get("answer_format")
                params.external_knowledge = result.get("external_knowledge")
            else:
                params = ApoParams()
                context["params"] = params
            params.base_instruction = result.get("base_instruction")
            params.full_prompt = result.get("best_prompt")
            params.filled_instruction = result.get("filled_prompt")
            params.num_iter = context.get("optimize_info").num_iter
            params.early_stop_score = context.get("optimize_info").early_stop_score
        context["error_msg"] = result.get("error_msg")
        context["scores"] = [result.get("success_rate")]
        context["run_time"] = result.get("time_cost")
        context["progress_rate"] = result.get("progress_rate")
        context["status"] = result.get("status")
        context["iter_num"] = result.get("iteration_round")
        context["sampled_incorrect_data"] = json.loads(result.get("sampled_error_case"))

    def _load_cases(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """load cases from store"""
        if not result:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="load empty cases"
                ),
            )
        opt_info: OptimizeInfo = context.get("optimize_info")
        cases = [
            Case(messages=case.get("messages"), tools=case.get("tools"))
            for case in json.loads(result.get("cases"))
        ]
        opt_info.cases = cases

    def _load_optimize_info(
        self, context: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """load optimize info from store"""
        if not result:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="load empty optimize info"
                ),
            )
        """load optimize_info from store"""
        opt_info = OptimizeInfo()
        context["optimize_info"] = opt_info
        opt_info.num_iter = result.get("num_iter")
        opt_info.llm_parallel = result.get("llm_parallel")
        opt_info.example_num = result.get("example_num")
        opt_info.cot_example_num = result.get("cot_example_num")
        opt_info.optimize_method = result.get("optimize_method")
        opt_info.placeholder = json.loads(result.get("placeholders"))
        opt_info.eval_mode = result.get("evaluation_method")
        opt_info.tools = result.get("tools")
        # 扩展信息
        extra_data = json.loads(result.get("extra_data"))
        opt_info.user_compare_rules = extra_data.get("user_compare_rules")
        opt_info.user_compare_options = extra_data.get("user_compare_options")
        opt_info.early_stop_score = extra_data.get("early_stop_score")
        opt_info.optimize_algo = extra_data.get("optimize_algo")
        opt_info.external_knowledge = extra_data.get("external_knowledge")
        context["raw_templates"] = [result.get("base_prompt")]

    def _load_job_info(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        if not result:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="load empty job info"
                ),
            )
        """load job info from store"""
        model_info = LLMModelInfo(headers={})
        context["model_info"] = model_info
        model_info.model = result.get("optimized_model_name")
        model_info.model_source = result.get("optimized_model_source")

        assistant_info = LLMModelInfo(headers={})
        context["assistant_info"] = assistant_info
        assistant_info.model = result.get("assistant_model_name")
        assistant_info.model_source = result.get("assistant_model_source")

        context["name"] = result.get("name")
        context["desc"] = result.get("desc")
        context["create_time"] = result.get("created_at")
        context["optimized_model_name"] = result.get("optimized_model_name")

    def _serialize_list_to_string(self, target_list: List[str]) -> str:
        """serialize list"""
        if not target_list:
            return ""
        return ",".join(target_list)

    def _deserialize_string_to_list(self, target_string: str) -> List[str]:
        """deserialize string"""
        if not target_string.strip():
            return []
        return target_string.strip().split(",")
