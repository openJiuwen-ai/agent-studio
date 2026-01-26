#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import json
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import status
from openjiuwen.core.stream.base import OutputSchema
from openjiuwen.core.tracer.span import TraceAgentSpan, TraceWorkflowSpan
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    get_db_jw, get_val_from_dict)
from openjiuwen_studio.core.manager.repositories.workflow_execution_repository import \
    workflow_execution_repository
from openjiuwen_studio.core.manager.repositories.workflow_repository import \
    workflow_repository
from openjiuwen_studio.models.agent import AgentBaseDB, AgentPublishDB
from openjiuwen_studio.models.agent_execution import (AgentExecutionDB,
                                        AgentExecutionDetailsDB)
from openjiuwen_studio.models.workflow_execution import WorkflowExecutionDB
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.execution_log import (AgExecutionLogIndex,
                                       AgExecutionLogsFilter,
                                       ComponentExecuteStatus,
                                       ExecutionCallType,
                                       ExecutionLogCreateInfo,
                                       ExecutionLogDebug, ExecutionLogSummary,
                                       InvokeExecuteInfo,
                                       TraceInvokeExecutionLogIndex,
                                       WfExecutionLogIndex)
from openjiuwen_studio.schemas.workflow import WorkflowId


def calc_duration_ms(start: datetime | None, end: datetime | None) -> int | None:
    return abs(int((end - start).total_seconds() * 1000)) if start and end else None


class AgentExecutionRepository():
    def __init__(self) -> None:
        # log中抽取至summary的共同字段, 这些字段只存于summary数据表，不会存于details数据表中
        self.common_fields_extract_from_log_to_summary = ["trace_id"]
        self.call_type_field = "call_type"          # 执行的发起者类型的属性名
        self.creat_time_field = 'create_time'       # 创建时间的属性名
        pass
    # def __init__(self, db: Session) -> None:
        # self._agent_execution_db: JiuwenBaseRepository[AgentExecutionDB] = JiuwenBaseRepository(db, AgentExecutionDB)
        # self._agent_execution_details_db: JiuwenBaseRepository[AgentExecutionDetailsDB] = JiuwenBaseRepository(db, AgentExecutionDetailsDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_log = f"Error: agent execution db data preprocessing error, {str(e)}"
                logger.error(error_log)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message=error_log)
        return wrapper
    
    def _trans_json_enum_2_string(self, data: dict | list) -> dict | list:
        """
        description: json中存在枚举类型数据，将其转换为string|int|...等常见类型存储
        """
        # 用于对json数据中的enum类型数据进行编码
        class EnumEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Enum):
                    return obj.value  # enum类型的编码取值
                return super().default(obj)
        return json.loads(json.dumps(data, cls=EnumEncoder))

    '''
    description: 将log_data中的workflow进行归拢, 放至相应TraceAgentSpan节点的metaData中
    param {list} log_data
    return {*}
    '''

    def _log_data_gather_workflow(self, log_list: list[TraceAgentSpan | TraceWorkflowSpan]) -> list[TraceAgentSpan]:
        log_data_new: list[TraceAgentSpan] = []
        workflow_data_list: list[TraceWorkflowSpan] = []

        def add_workflow_data_2_metadata():
            nonlocal log_data_new, workflow_data_list
            # 需要将workflow数据放至上一个agent节点的metaData中
            if not log_data_new or log_data_new[-1].invoke_type != "workflow" \
                or log_data_new[-1].end_time:
                # 上一个tracer_agent节点必须是workflow类型且是开始的节点
                raise ValueError(
                    f"log_data error: the error of the layout of workflow, last log should be workflow but got {log.invoke_type}")
            log_data_new[-1].meta_data["workflows"] = workflow_data_list
            workflow_data_list = []

        for log in log_list:
            if isinstance(log, TraceWorkflowSpan):
                # workflow数据
                workflow_data_list.append(log)
            else:
                # agent数据
                # 如果是agent中的workflow的结束节点
                if log.invoke_type == "workflow" and log.end_time:
                    add_workflow_data_2_metadata()
                # 将当前tracer_agent节点加入list
                log_data_new.append(log)
        # 如果是中途错误退出，可能导致没有执行完成
        if workflow_data_list:
            add_workflow_data_2_metadata()
        return log_data_new

    def _log_data_2_details_db(
        self, dbsession: Session, agent_index: AgentId, log_data: list[TraceAgentSpan | TraceWorkflowSpan],
        call_type: ExecutionCallType = ExecutionCallType.agent
    ) -> list[AgentExecutionDetailsDB]:
        """
        description: 
        遍历log_data中各node的执行数据生成list[AgentExecutionDetailsDB]: 
            1.1) 对于所有数据，先直接构造AgentExecutionDetailsDB模型数据; 
            1.2) 对于workflow数据, 调用_generate_workflow_execution_dbmodel方法生成WorkflowExecutionDB模型数据，再将其添加到成员workflow_execution中;
        """
        detail_dbs = []
        log_data_new: list[TraceAgentSpan] = self._log_data_gather_workflow(log_data)
        for log in log_data_new:
            # 获取workflow数据
            workflow_data_list = log.meta_data.pop("workflows", [])
            detail_db = AgentExecutionDetailsDB.from_dict(log.model_dump())
            # detail_db.inputs = self._trans_json_enum_2_string(detail_db.inputs)     # 将inputs中的枚举类型数据转换为字符串存储
            detail_db.outputs = self._trans_json_enum_2_string(detail_db.outputs)   # 将outputs中的枚举类型数据转换为字符串存储
            # agent节点包含workflow数据
            if workflow_data_list:
                workflow_index = WorkflowId(
                    space_id=agent_index.space_id,
                    workflow_id=log.meta_data["metadata"]["id"],
                    workflow_version=log.meta_data["metadata"].get("version", None)
                )
                workflow_exe_gen_res = workflow_execution_repository.generate_workflow_execution_dbmodel(
                                                                        dbsession, workflow_index, workflow_data_list, 
                                                                        call_type=call_type, execute_start_time=log_data_new[0].start_time)
                if workflow_exe_gen_res.code != status.HTTP_200_OK:
                    raise ValueError(f"workflow execution data generate error: {workflow_exe_gen_res.message}")
                detail_db.workflow_execution = workflow_exe_gen_res.data
            detail_dbs.append(detail_db)
        return detail_dbs
    
    def _extract_summary_execution_info_from_log(
        self, log_details: list[AgentExecutionDetailsDB]
    ) -> list[InvokeExecuteInfo] | None:
        """
        description: 从agent的某次执行log_details中，提取总的树状执行信息, list[InvokeExecuteInfo]树状结构类型
        """
        if not log_details:
            return None
        components_execute_info: list[InvokeExecuteInfo] = []       # 已处理好的组件执行信息
        running_component_execute_info: dict[str, InvokeExecuteInfo] = {}     # 当前还在处理中的组件
        execute_start_time = log_details[0].start_time

        def _component_process_over(log: AgentExecutionDetailsDB | None, component_execute_info: InvokeExecuteInfo):
            """
            description: 结束running组件的处理过程
            """
            if log:
                component_execute_info.status = ComponentExecuteStatus.error if log.error else ComponentExecuteStatus.finish
                component_execute_info.duration = calc_duration_ms(log.start_time, log.end_time)
                component_execute_info.outputs = log.outputs
            else:   # 没有对应的log，说明此component没有正常结束, 可能是被终止了
                component_execute_info.status = ComponentExecuteStatus.error
            if component_execute_info.loop_node_id: 
                # 处理循环组件中的子组件
                if component_execute_info.loop_node_id in running_component_execute_info:
                    # 将子组件的执行信息添加到父组件中
                    parent_component_execute_info = running_component_execute_info[component_execute_info.loop_node_id]
                    if parent_component_execute_info.child_invokes_execute_info is None:
                        parent_component_execute_info.child_invokes_execute_info = []
                    parent_component_execute_info.child_invokes_execute_info.append(component_execute_info)
                else:
                    # 还处理中的组件中无法找到父节点，说明存在错误
                    error_msg = "Can't find the parent loop_component of this component"
                    logger.debug(error_msg)
                    raise ValueError(error_msg)
            else:
                # 一般组件
                components_execute_info.append(component_execute_info)

        for log in log_details:
            # 统计单个组件的执行信息
            # 组件开始
            if not log.end_time:
                component_execute_info = InvokeExecuteInfo(
                    invoke_id=log.invoke_id, 
                    invoke_name=log.name,
                    invoke_type=log.invoke_type,
                    status=ComponentExecuteStatus.start,
                    start_timestamp=calc_duration_ms(execute_start_time, log.start_time),
                    inputs=log.inputs,
                )
                if log.workflow_execution:
                    # 如果本组件是workflow类型, 获取workflow的执行树状信息
                    workflow_execution: WorkflowExecutionDB = log.workflow_execution
                    # workflow中的组件执行树状信息
                    if len(workflow_execution.execute_info_list) == 1:
                        # 即使根节点只1个节点，也会多套一层外部结构，所以只取[0]的child_invokes_execute_info
                        wf_invoke_exe_info = InvokeExecuteInfo.model_validate(workflow_execution.execute_info_list[0])
                        component_execute_info.child_invokes_execute_info = wf_invoke_exe_info.child_invokes_execute_info
                    else:
                        # 根节点有多个数据
                        component_execute_info.child_invokes_execute_info = [InvokeExecuteInfo.model_validate(wf_exe_info) 
                                                                                for wf_exe_info in workflow_execution.execute_info_list]
                running_component_execute_info[log.invoke_id] = component_execute_info
            # 组件结束 或 报错
            else:
                # 从正处理的组件中取出该组件信息
                component_execute_info = running_component_execute_info.pop(log.invoke_id, None)
                if component_execute_info:
                    _component_process_over(log, component_execute_info)
                else:
                    warn_msg = f"Can't find this component from running components, invoke_id: {log.invoke_id}"
                    logger.warning(warn_msg)
                    component_execute_info = InvokeExecuteInfo(
                        invoke_id=log.invoke_id,
                        invoke_name=log.name,
                        invoke_type=log.invoke_type,
                        status=ComponentExecuteStatus.start,
                        start_timestamp=calc_duration_ms(execute_start_time, log.start_time),
                        inputs=log.inputs,
                    )
                    _component_process_over(log, component_execute_info)

        # 处理剩余的正处理中的组件，说明这些组件没有正常结束
        while running_component_execute_info:
            _, component_execute_info = running_component_execute_info.popitem()
            _component_process_over(None, component_execute_info)

        return components_execute_info
    
    def _summary_log_data(
        self, agent: AgentBaseDB | AgentPublishDB, log_details: list[AgentExecutionDetailsDB]
    ) -> AgentExecutionDB:
        '''
        description: 
        1. 使用list[AgentExecutionDetailsDB]生成summary数据(AgentExecutionDB类型), 
        2. 将此list添加至summary的成员agent_execution_details_list中, 最后返回此数据
        '''
        # 本次agent执行的所有component执行数据
        components_execute_info = self._extract_summary_execution_info_from_log(log_details)
        execute_info = InvokeExecuteInfo(
            invoke_id=agent.agent_id,
            invoke_version=agent.agent_version,
            invokeType=ExecutionCallType.agent,
            invoke_name=agent.agent_name,
            start_timestamp=0,
            duration=calc_duration_ms(log_details[-1].end_time, log_details[0].start_time),
            inputs=log_details[0].inputs,
        )
        if components_execute_info:
            execute_info.status = components_execute_info[-1].status
            execute_info.outputs = components_execute_info[-1].outputs
            execute_info.child_invokes_execute_info = components_execute_info
        else:
            execute_info.status = ComponentExecuteStatus.error

        # 构造保存到db的数据
        summary_db = AgentExecutionDB(
            space_id=agent.space_id,
            agent_id=agent.agent_id,
            agent_version=agent.agent_version,
            trace_id=log_details[0].trace_id,
            status=execute_info.status,
            # execution_id = log_details[0].execution_id,
            duration=execute_info.duration,
            inputs=execute_info.inputs,
            outputs=execute_info.outputs,
            create_time=log_details[0].start_time,
            update_time=log_details[-1].end_time if log_details[-1].end_time else log_details[-1].start_time,
        )
        summary_db.execute_info_list = [execute_info.model_dump(exclude_none=True)]
        if summary_db.status == ComponentExecuteStatus.error:
            if isinstance(log_details[-1].error, dict):
                _code = log_details[-1].error.get("code", None)
                try:
                    summary_db.error_code = int(_code) if _code is not None else None
                except (TypeError, ValueError):
                    summary_db.error_code = None
                summary_db.fail_reason = str(log_details[-1].error.get("message", "unknown"))
            else:
                summary_db.error_code = None
                summary_db.fail_reason = str(log_details[-1].error)
        summary_db.agent_execution_details_list = log_details
        return summary_db

    '''
    description: 创建AgentExecutionDB模型的数据
    param {*} self
    param {AgentId} agent_index   本次执行的agent信息
    param {list} log_data       本次执行的日志信息列表， list[TraceAgentSpan]
    param {ExecutionCallType} call_type 本次执行的调用类型，默认为agent
    return {*}      AgentExecutionDB模型的数据放在ResponseModel.data中
    '''

    def _generate_agent_execution_dbmodel(
        self, dbsession: Session, agent_index: AgentId, log_data: list[TraceAgentSpan | TraceWorkflowSpan],
        call_type: ExecutionCallType = ExecutionCallType.agent
    ) -> ResponseModel[AgentExecutionDB | None]:
        # 数据校验
        if not log_data:
            logger.debug("No log_data to register")
            return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No log_data to register")
        
        # 数据库查询agent是否存在
        if not agent_index.agent_version or agent_index.agent_version == AgentBaseDB.__version_none__:
            # 非发布版本的agent
            agent_db = JiuwenBaseRepository(dbsession, AgentBaseDB)
            agent_index.agent_version = AgentBaseDB.__version_none__
        else:
            agent_db = JiuwenBaseRepository(dbsession, AgentPublishDB)
        # 先查找agent是否存在
        agent_db_res = agent_db.get_dl_in_sql(find_id=agent_index.model_dump(), 
                                            return_first_item=True, return_declarativebase=True)
        if agent_db_res.code != status.HTTP_200_OK:
            return agent_db_res
        
        # 对于log_data, 可能最后一个数据非TraceAgentSpan类型而是outputstream类型，所以需要先剔除或者只处理该数据
        if isinstance(log_data[-1], OutputSchema):
            # 如果只有OutputSchema的时候，则只处理output
            if len(log_data) == 1:
                agent_db: AgentBaseDB | AgentPublishDB = agent_db_res.data
                output_schema: OutputSchema = log_data[-1]
                execution_summary_create = AgentExecutionDB(space_id=agent_index.space_id,
                                                            agent_id=agent_index.agent_id,
                                                            agent_version=agent_index.agent_version,
                                                            trace_id=str(output_schema.index),
                                                            status=ComponentExecuteStatus.finish,
                                                            call_type=ExecutionCallType.agent, 
                                                            outputs=output_schema.payload,
                                                            create_time=datetime.now(timezone.utc).replace(tzinfo=None)
                                                            )
                return ResponseModel(code=status.HTTP_200_OK, message="Generate agent execution dbmodel only \
                                      from output_schema ok.", data=execution_summary_create)
            # 如果不只有OutputSchema，还有其他trace，剔除该outputschema
            log_data = log_data[:-1]
        
        # trace_id唯一性及有效性校验
        trace_id_set = list(set([log.trace_id for log in log_data]))
        trace_id = trace_id_set[0]
        if len(trace_id_set) != 1 or not trace_id:
            logger.debug(f"Trace_id in log_data is not unique or empty, trace_id_set: {trace_id_set}")
            return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="Trace_id in log_data is not unique or empty.")
        
        # 构造AgentExecutionDB模型数据信息
        '''
        1. 先使用_log_data_2_details_db函数，遍历log_data中各node的执行数据生成list[AgentExecutionDetailsDB]: 
            1.1) 对于所有数据，先直接构造AgentExecutionDetailsDB模型数据; 
            1.2) 对于workflow数据, 调用_generate_workflow_execution_dbmodel方法生成WorkflowExecutionDB模型数据，再将其添加到成员workflow_execution中;
        2. 使用list[AgentExecutionDetailsDB]生成summary数据，AgentExecutionDB类型，并将list添加至成员agent_execution_details_list中，最后返回此数据
        '''
        agent_execution_details_list = self._log_data_2_details_db(
            dbsession=dbsession, agent_index=agent_index, log_data=log_data, call_type=call_type)
        execution_summary_create: AgentExecutionDB = self._summary_log_data(
            agent_db_res.data, agent_execution_details_list)
        execution_summary_create.call_type = call_type
        # 返回数据
        return ResponseModel(code=status.HTTP_200_OK, message="Generate agent execution dbmodel ok.", data=execution_summary_create)
        
    @with_exception_handling
    def create_agent_execution_log(
        self, agent_index: AgentId, log_data: list[TraceAgentSpan | TraceWorkflowSpan],
        call_type: ExecutionCallType = ExecutionCallType.agent, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as dbsession:
            ag_exe_dbmodel_res = self._generate_agent_execution_dbmodel(dbsession, agent_index, log_data, call_type)
            if isinstance(ag_exe_dbmodel_res.data, AgentExecutionDB):
                agent_execution_db = JiuwenBaseRepository(dbsession, AgentExecutionDB)
                return agent_execution_db.register_dl_in_sql(find_id=None, dl=ag_exe_dbmodel_res.data)
            return ag_exe_dbmodel_res
        
    '''
    description: 删除agent的所有执行日志
    param {*} self
    param {AgentId} agent_index
    return {*}
    '''
    @with_exception_handling
    def delete_all_execution_logs_of_agent(self, agent_index: AgentId, call_type: ExecutionCallType | None = ExecutionCallType.agent, 
                                           db_session: Session | None = None) -> ResponseModel[None]:
        # 数据校验
        if not agent_index.agent_version:
            agent_index.agent_version = AgentExecutionDB.__version_none__
        find_id = agent_index.model_dump()
        if call_type:
            find_id[self.call_type_field] = call_type.value
        with get_db_jw(db_session) as db:
            agent_execution_db = JiuwenBaseRepository(db, AgentExecutionDB)
            return agent_execution_db.unregister_dl_in_sql(find_id=find_id)
    
    '''
    description: 删除agent的某次执行日志
    param {*} self
    param {AgentId} agent_index
    return {*}
    '''
    @with_exception_handling
    def delete_agent_execution_log(self, ag_execution_log_index: AgExecutionLogIndex, 
                                   db_session: Session | None = None) -> ResponseModel[None]:
        # 数据校验
        if not ag_execution_log_index.agent_version:
            ag_execution_log_index.agent_version = AgentExecutionDB.__version_none__
        with get_db_jw(db_session) as db:
            agent_execution_db = JiuwenBaseRepository(db, AgentExecutionDB)
            return agent_execution_db.unregister_dl_in_sql(find_id=ag_execution_log_index.model_dump())

    '''
    description: 获取一定范围内所有执行日志的创建list
    param {*} self
    param {WfExecutionLogsFilter} wf_execution_logs_filter
    param {*} dbsession     传入的db session
    return {*}
    '''

    def _get_execution_logs_create_list_with_dbsession(
        self, dbsession: Session, ag_execution_logs_filter: AgExecutionLogsFilter,
        call_type: ExecutionCallType | None = ExecutionCallType.agent
    ) -> ResponseModel[ExecutionLogDebug]:
        if not ag_execution_logs_filter.agent_version:
            ag_execution_logs_filter.agent_version = AgentExecutionDB.__version_none__
        ag_execution_logs_filter = AgExecutionLogsFilter(**ag_execution_logs_filter.model_dump())
        find_id = ag_execution_logs_filter.model_dump(exclude_none=True)
        if call_type:
            find_id[self.call_type_field] = call_type.value
        # 需要从数据库中获取的字段
        cols_find = list(ExecutionLogCreateInfo.model_fields.keys())
        find_min_max = {self.creat_time_field: [ag_execution_logs_filter.start_time, ag_execution_logs_filter.end_time]}
        order_cols_desc = [self.creat_time_field]   # 降序排列
        agent_execution_db = JiuwenBaseRepository(dbsession, AgentExecutionDB)
        db_res = agent_execution_db.get_dl_in_sql_with_cols(find_id=find_id, cols_find=cols_find,
                                                            find_min_max=find_min_max, order_cols_desc=order_cols_desc)
        if db_res.code == status.HTTP_200_OK and db_res.data:
            logs_create_list = [ExecutionLogCreateInfo(**record) for record in db_res.data]
            db_res.data = ExecutionLogDebug(logs_create_list=logs_create_list)
        return db_res

    @with_exception_handling
    def get_execution_logs_create_list(self, ag_execution_logs_filter: AgExecutionLogsFilter, 
                                       call_type: ExecutionCallType | None = ExecutionCallType.agent, 
                                       db_session: Session | None = None) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            return self._get_execution_logs_create_list_with_dbsession(db, ag_execution_logs_filter, call_type=call_type)

    '''
    description: 获取workflow的某次执行日志详情
    param {*} self
    param {WfExecutionLogIndex} wf_execution_log_index
    param {*} dbsession     传入的db session
    return {*}
    '''

    def get_execution_log_with_dbsession(
        self, dbsession: Session, ag_execution_log_index: AgExecutionLogIndex
    ) -> ResponseModel[ExecutionLogDebug]:
        if not ag_execution_log_index.agent_version:
            ag_execution_log_index.agent_version = AgentExecutionDB.__version_none__
        agent_execution_db = JiuwenBaseRepository(dbsession, AgentExecutionDB)
        db_res = agent_execution_db.get_dl_in_sql(find_id=ag_execution_log_index.model_dump(), return_first_item=True,
                                                        return_declarativebase=True)
        if db_res.code != status.HTTP_200_OK:
            return db_res
        # 对于agent，只获取总结信息
        log_summary = ExecutionLogSummary.model_validate(db_res.data.to_dict())
        db_res.data = ExecutionLogDebug(log_summary=log_summary)
        return db_res
    
    @with_exception_handling
    def get_execution_log(self, ag_execution_log_index: AgExecutionLogIndex, 
                          db_session: Session | None = None) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            return self.get_execution_log_with_dbsession(db, ag_execution_log_index)

    '''
    description: 进行调试日志界面时，返回所有日志create list和最新日志详情
    param {*} self
    param {WorkflowId} workflow_id
    return {*}
    '''
    @with_exception_handling
    def enter_execution_logs_debug(
        self, agent_id: AgentId, db_session: Session | None = None
    ) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            # 获取workflow的运行create list
            logs_create_list_db_res = self._get_execution_logs_create_list_with_dbsession(db, agent_id,  
                                                                                          call_type=ExecutionCallType.agent)
            if logs_create_list_db_res.code != status.HTTP_200_OK or not logs_create_list_db_res.data \
                        or not logs_create_list_db_res.data.logs_create_list:
                return logs_create_list_db_res
            # 获取最新运行日志的数据
            logs_create_list: list[ExecutionLogCreateInfo] = logs_create_list_db_res.data.logs_create_list
            lastest_trace_id = logs_create_list[0].trace_id
            ag_execution_log_index = AgExecutionLogIndex.model_validate(
                agent_id.model_dump() | {"trace_id": lastest_trace_id})
            laster_execution_log_db_res = self.get_execution_log_with_dbsession(db, ag_execution_log_index)
            if laster_execution_log_db_res.code != status.HTTP_200_OK:
                return laster_execution_log_db_res
            laster_execution_log_db_res.data.logs_create_list = logs_create_list
            return laster_execution_log_db_res

    '''
    description: 点击调试界面运行树中的workflow叶子时, 可以进入到workflow的执行日志界面
    param {*} self
    param {TraceInvokeExecutionLogIndex} ag_invoke_id
    return {*}
    '''
    @with_exception_handling
    def enter_sub_workflow_execution_logs_debug(
        self, ag_invoke_id: TraceInvokeExecutionLogIndex, 
        db_session: Session | None = None
    ) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            ag_invoke_details_db = JiuwenBaseRepository(db, AgentExecutionDetailsDB)
            cols_find = ["meta_data"]
            db_res = ag_invoke_details_db.get_dl_in_sql_with_cols(find_id=ag_invoke_id.model_dump(
                exclude=["space_id"]), cols_find=cols_find, return_first_item=True)
            if db_res.code != status.HTTP_200_OK:
                return db_res
            meta_data = db_res.data["meta_data"]
            if meta_data.get("type", "") != "workflow":
                raise ValueError(f"invoke type is not workflow, but {meta_data.get('type', '')}")
            if 'metadata' not in meta_data:
                raise ValueError(f"metadata not found in this invoke's meta_data: {meta_data}")
            if 'id' not in meta_data['metadata']:
                raise ValueError(f"workflow id not found in this invoke's meta_data: {meta_data}")
            
            workflow_id = WorkflowId(
                space_id=ag_invoke_id.space_id,
                workflow_id=meta_data['metadata']['id'],
                workflow_version=meta_data['metadata'].get('version', None)
            )
            
            wf_execution_log_index = WfExecutionLogIndex(**workflow_id.model_dump(), trace_id=ag_invoke_id.trace_id)
            wf_execution_log_db_res = workflow_execution_repository.get_execution_log_with_dbsession(
                db, wf_execution_log_index)
            if wf_execution_log_db_res.code != status.HTTP_200_OK:
                return wf_execution_log_db_res
            
            wf_data_db_res: ResponseModel = workflow_repository.workflow_get(workflow_id)
            if wf_data_db_res.data:
                wf_execution_log_db_res.data.workflow_metadata = wf_data_db_res.data
            return wf_execution_log_db_res
            

agent_execution_repository = AgentExecutionRepository()