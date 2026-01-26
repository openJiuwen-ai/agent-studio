from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import status
from openjiuwen.core.tracer.span import TraceWorkflowSpan
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    get_db_jw, get_val_from_dict)
from openjiuwen_studio.models.workflow import WorkflowBaseDB, WorkflowPublishDB
from openjiuwen_studio.models.workflow_execution import (WorkflowExecutionDB,
                                           WorkflowExecutionDetailsDB)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.execution_log import (ComponentExecuteStatus,
                                       ExecutionCallType,
                                       ExecutionLogCreateInfo,
                                       ExecutionLogDebug,
                                       ExecutionLogsCreateList,
                                       ExecutionLogSummary, InvokeExecuteInfo,
                                       WfExecutionLogIndex,
                                       WfExecutionLogsFilter)
from openjiuwen_studio.schemas.workflow import WorkflowId


def calc_duration_ms(start: datetime | None, end: datetime | None) -> int | None:
    return int((end - start).total_seconds() * 1000) if start and end else None


class WorkflowExecutionRepository():
    def __init__(self) -> None:
        # log中抽取至summary的共同字段, 这些字段只存于summary数据表，不会存于details数据表中
        self.common_fields_extract_from_log_to_summary = ["execution_id", "trace_id"]
        self.call_type_field = "call_type"          # 执行的发起者类型的属性名
        self.creat_time_field = 'create_time'       # 创建时间的属性名
        pass
    # def __init__(self, db: Session) -> None:
    #     self._workflow_execution_db: JiuwenBaseRepository[WorkflowExecutionDB] = JiuwenBaseRepository(db, WorkflowExecutionDB)
    #     self._workflow_execution_details_db: JiuwenBaseRepository[WorkflowExecutionDetailsDB] = JiuwenBaseRepository(db, WorkflowExecutionDetailsDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                error_log = f"Error: workflow execution db data preprocessing error, {type(e).__name__}"
                logger.error(error_log)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message=error_log)
        return wrapper
    
    @staticmethod
    def _extract_summary_execution_info_from_log(
        log_data: list[TraceWorkflowSpan],
        execute_start_time: datetime | None = None
    ) -> list[InvokeExecuteInfo] | None:
        """
        description: 从workflow的某次执行log_data中，提取总的执行信息, WfComponentsExecuteInfo类型
        """
        if not log_data:
            return None
        components_execute_info: list[InvokeExecuteInfo] = []       # 已处理好的组件执行信息
        running_component_execute_info: dict[str, InvokeExecuteInfo] = {}     # 当前还在处理中的组件
        if not execute_start_time:
            execute_start_time = log_data[0].start_time

        def _get_parent_component_info(invoke_id: str) -> tuple[InvokeExecuteInfo | None, str | None]:
            """
            description: 根据invoke_id获取父组件信息
            invoke_id规则：
            - workflow_cLjMT: 子工作流
            - workflow_cLjMT.start_0: 该工作流的start子组件
            - workflow_cLjMT.workflow_fV0Wb: workflow_cLjMT执行了其子工作流workflow_fV0Wb
            - loop_U2lTa: 循环节点
            - loop_U2lTa.workflow_hjFr6: 循环节点下的子工作流
            - loop_U2lTa.workflow_hjFr6.end_0: 子工作流的end节点
            """
            if not invoke_id:
                return None, None
            
            # 检查是否为工作流、循环节点或其子组件
            if invoke_id.startswith(('workflow_', 'loop_')):
                # 分割invoke_id获取父级关系
                parts = invoke_id.split('.')
                
                # 对于workflow_cLjMT.start_0，父级是workflow_cLjMT
                # 对于loop_U2lTa.workflow_hjFr6，父级是loop_U2lTa
                # 对于loop_U2lTa.workflow_hjFr6.end_0，父级是loop_U2lTa.workflow_hjFr6
                if len(parts) > 1:
                    parent_type = '.'.join(parts[:-1])
                    if parent_type in running_component_execute_info:
                        return running_component_execute_info[parent_type], parent_type
            
            return None, None

        def _component_process_over(log: TraceWorkflowSpan | None, component_execute_info: InvokeExecuteInfo):
            """
            description: 结束running组件的处理过程
            """
            if log:
                component_execute_info.status = log.status
                component_execute_info.duration = calc_duration_ms(log.start_time, log.end_time)
                component_execute_info.outputs = log.outputs
            else:   # 没有对应的log，说明此component没有正常结束, 可能是被终止了
                component_execute_info.status = ComponentExecuteStatus.error
            
            # 1. 优先处理循环组件关系
            if component_execute_info.loop_node_id: 
                # 处理循环组件中的子组件
                if component_execute_info.loop_node_id in running_component_execute_info:
                    # 将子组件的执行信息添加到父组件中
                    parent_component_execute_info = running_component_execute_info[component_execute_info.loop_node_id]
                    if parent_component_execute_info.child_invokes_execute_info is None:
                        parent_component_execute_info.child_invokes_execute_info = []
                    parent_component_execute_info.child_invokes_execute_info.append(component_execute_info)
                    return
                else:
                    # 还处理中的组件中无法找到父节点，说明存在错误
                    error_msg = "Can't find the parent loop_component of this component"
                    logger.debug(error_msg)
                    # 不抛出异常，继续尝试其他父级关系
            
            # 2. 处理子工作流/子组件的层级关系
            parent_info, parent_type = _get_parent_component_info(component_execute_info.invoke_id)
            if parent_info:
                # 将当前组件作为父组件的子组件
                if parent_info.child_invokes_execute_info is None:
                    parent_info.child_invokes_execute_info = []
                parent_info.child_invokes_execute_info.append(component_execute_info)
                return
            

            
            # 4. 一般组件，直接添加到结果列表
            components_execute_info.append(component_execute_info)

        for log in log_data:
            # 统计单个组件的执行信息
            # 获取组件名称
            component_name = log.component_name
            
            # 组件开始
            if log.status == ComponentExecuteStatus.start:
                component_execute_info = InvokeExecuteInfo(
                    invoke_id=log.invoke_id, 
                    invoke_name=component_name,
                    invoke_type=log.component_type,
                    status=log.status,
                    start_timestamp=calc_duration_ms(execute_start_time, log.start_time),
                    loop_node_id=log.loop_node_id,
                    loop_index=log.loop_index,
                    inputs=log.inputs,
                )
                # 保存到running字典，key使用invoke_id
                # 对于工作流和循环节点，使用完整的invoke_id以便后续根据层级关系查找
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
                        invoke_name=component_name,
                        invoke_type=log.component_type,
                        status=ComponentExecuteStatus.start,
                        start_timestamp=calc_duration_ms(execute_start_time, log.start_time),
                        loop_node_id=log.loop_node_id,
                        loop_index=log.loop_index,
                        inputs=log.inputs,
                    )
                    _component_process_over(log, component_execute_info)
        # 处理剩余的正处理中的组件，说明这些组件没有正常结束
        while running_component_execute_info:
            invoke_id, component_execute_info = running_component_execute_info.popitem()
            _component_process_over(None, component_execute_info)
        return components_execute_info
    
    def _summary_log_data(self, workflow: WorkflowBaseDB | WorkflowPublishDB, log_data: list[TraceWorkflowSpan], 
                          execute_start_time: datetime | None = None) -> WorkflowExecutionDB:
        """
        description: 创建 WorkflowExecutionDB 数据
        """
        # 本次workflow执行的所有component执行数据
        components_execute_info = WorkflowExecutionRepository._extract_summary_execution_info_from_log(log_data=log_data,
                                                                                execute_start_time=execute_start_time)
        # 将workflow的本次执行的总信息构造成最外层的InvokeExecuteInfo
        execute_info = InvokeExecuteInfo(
            invoke_id=workflow.workflow_id,
            invoke_version=workflow.workflow_version,
            invoke_type=ExecutionCallType.workflow,
            invoke_name=workflow.name,
            start_timestamp=0 if not execute_start_time else calc_duration_ms(
                execute_start_time, log_data[0].start_time),
            duration=calc_duration_ms(log_data[0].start_time, log_data[-1].end_time),
            inputs=log_data[0].inputs,
        )
        if components_execute_info:
            execute_info.status = components_execute_info[-1].status
            execute_info.outputs = components_execute_info[-1].outputs
            execute_info.child_invokes_execute_info = components_execute_info
        else:
            execute_info.status = ComponentExecuteStatus.error
        # 构造保存到db的数据
        summary_db = WorkflowExecutionDB(
            space_id=workflow.space_id,
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.workflow_version,
            trace_id=log_data[0].trace_id,
            status=execute_info.status,
            execution_id=log_data[0].execution_id,
            duration=execute_info.duration,
            inputs=execute_info.inputs,
            outputs=execute_info.outputs,
            create_time=log_data[0].start_time,
            update_time=log_data[-1].end_time if log_data[-1].end_time else log_data[-1].start_time,
        )
        summary_db.execute_info_list = [execute_info.model_dump(exclude_none=True)]
        if summary_db.status == ComponentExecuteStatus.error:
            if isinstance(log_data[-1].error, dict):
                _code = log_data[-1].error.get("code", None)
                try:
                    summary_db.error_code = int(_code) if _code is not None else None
                except (TypeError, ValueError):
                    summary_db.error_code = None
                summary_db.fail_reason = str(log_data[-1].error.get("message", "unknown"))
            else:
                summary_db.error_code = None
                summary_db.fail_reason = str(log_data[-1].error)
        return summary_db
    
    def _log_data_2_details_db(self, log_data: list[TraceWorkflowSpan]) -> list[WorkflowExecutionDetailsDB]:
        """
        description: 创建 WorkflowExecutionDetailsDB 数据
        """
        detail_dbs = []
        for log in log_data:
            log_dict = log.model_dump(exclude=self.common_fields_extract_from_log_to_summary)
            # 确保 error 字段是字典类型或 None
            if 'error' in log_dict and log_dict['error'] is not None and not isinstance(log_dict['error'], dict):
                # 将非字典类型的错误转换为字典格式
                log_dict['error'] = {'message': str(log_dict['error'])}
            detail_dbs.append(WorkflowExecutionDetailsDB.from_dict(log_dict))
        return detail_dbs
    
    '''
    description: 创建WorkflowExecutionDB模型的数据
    param {*} self
    param {WorkflowId} workflow_index   本次执行的workflow信息
    param {list} log_data       本次执行的日志信息列表， list[TraceWorkflowSpan]
    param {ExecutionCallType} call_type 本次执行的调用类型，默认为workflow
    param {int} agent_execution_detail_id   本次workflow由agent发起调用时，agent的agent_execution_details.id; 
                                            如果是通过sqlalchemy的级联创建，不需要赋值agent_execution_detail_id
    param {int} agent_execution_detail_id   本次执行的真正开始时间, 如果workflow是某执行的子项, 需要输入此值作为执行的开始时间, 而不是从wf中提取; 
    return {*}      WorkflowExecutionDB模型的数据放在ResponseModel.data中
    '''

    def generate_workflow_execution_dbmodel(
        self, dbsession: Session, workflow_index: WorkflowId,
        log_data: list[TraceWorkflowSpan],
        call_type: ExecutionCallType = ExecutionCallType.workflow,
        agent_execution_detail_id: int | None = None,
        execute_start_time: datetime | None = None
    ) -> ResponseModel[WorkflowExecutionDB | None]:
        # 数据校验
        if not log_data:
            logger.debug("No log_data to register")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST, 
                message="No log_data to register"
            )
        
        # 对于log_data, 可能最后一个数据非TraceWorkflowSpan类型而是outputstream类型，所以需要先剔除
        if not isinstance(log_data[-1], TraceWorkflowSpan):
            log_data = log_data[:-1]

        # trace_id唯一性及有效性校验
        trace_id_set = list(set([log.trace_id for log in log_data]))
        trace_id = trace_id_set[0]
        if len(trace_id_set) != 1 or not trace_id:
            logger.debug(f"Trace_id in log_data is not unique or empty, trace_id_set: {trace_id_set}")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Trace_id in log_data is not unique or empty."
            )
        # execution_id唯一性校验
        execution_id_set = list(set([log.execution_id for log in log_data]))
        if len(execution_id_set) != 1:
            logger.debug(f"Execution_id in log_data is not unique, execution_id_set: {execution_id_set}.")
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Execution_id in log_data is not unique."
            )
        
        # 数据库查询workflow是否存在
        if not workflow_index.workflow_version or workflow_index.workflow_version == WorkflowBaseDB.__version_none__:
            # 非发布版本的workflow
            workflow_db = JiuwenBaseRepository(dbsession, WorkflowBaseDB)
            workflow_index.workflow_version = WorkflowBaseDB.__version_none__
        else:
            workflow_db = JiuwenBaseRepository(dbsession, WorkflowPublishDB)
        # 先查找workflow是否存在
        workflow_db_res = workflow_db.get_dl_in_sql(find_id=workflow_index.model_dump(), 
                                                     return_first_item=True, return_declarativebase=True)
        if workflow_db_res.code != status.HTTP_200_OK:
            return workflow_db_res
        
        # 构造summary信息
        execution_summary_create: WorkflowExecutionDB = self._summary_log_data(workflow_db_res.data, log_data, 
                                                                              execute_start_time)
        execution_summary_create.call_type = call_type
        if call_type == ExecutionCallType.agent and agent_execution_detail_id:
            # 如果本次workflow是由agent发起调用; 如果是通过sqlalchemy的级联创建，可以不用赋值agent_execution_detail_id
            execution_summary_create.agent_execution_detail_id = agent_execution_detail_id
        
        # 再构造详细信息
        execution_summary_create.workflow_execution_details_list += self._log_data_2_details_db(log_data)

        # 返回数据
        return ResponseModel(code=status.HTTP_200_OK, message="Generate workflow execution dbmodel ok.", data=execution_summary_create)
        
    @with_exception_handling
    def create_workflow_execution_log(self, workflow_index: WorkflowId, log_data: list[TraceWorkflowSpan],
                                       call_type: ExecutionCallType = ExecutionCallType.workflow, 
                                       agent_execution_detail_id: int | None = None, 
                                       db_session: Session | None = None, 
                                       execute_start_time: datetime | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            wf_exe_dbmodel_res = self.generate_workflow_execution_dbmodel(
                db, workflow_index, log_data, call_type,
                agent_execution_detail_id, execute_start_time
            )
            if isinstance(wf_exe_dbmodel_res.data, WorkflowExecutionDB):
                workflow_execution_db = JiuwenBaseRepository(db, WorkflowExecutionDB)
                return workflow_execution_db.register_dl_in_sql(find_id=None, dl=wf_exe_dbmodel_res.data)
            return wf_exe_dbmodel_res
        
    '''
    description: 删除workflow的所有执行日志
    param {*} self
    param {WorkflowId} workflow_index
    return {*}
    '''
    @with_exception_handling
    def delete_all_execution_logs_of_workflow(self, workflow_index: WorkflowId,
                                       call_type: ExecutionCallType | None = ExecutionCallType.workflow, 
                                       db_session: Session | None = None) -> ResponseModel[None]:
        # 数据校验
        if not workflow_index.workflow_version:
            workflow_index.workflow_version = WorkflowExecutionDB.__version_none__
        find_id = workflow_index.model_dump()
        if call_type:
            find_id[self.call_type_field] = call_type.value
        with get_db_jw(db_session) as db:
            workflow_execution_db = JiuwenBaseRepository(db, WorkflowExecutionDB)
            return workflow_execution_db.unregister_dl_in_sql(find_id=find_id)
    
    '''
    description: 删除workflow的某次执行日志
    param {*} self
    param {WorkflowId} workflow_index
    return {*}
    '''
    @with_exception_handling
    def delete_workflow_execution_log(self, wf_execution_log_index: WfExecutionLogIndex, 
                                      db_session: Session | None = None) -> ResponseModel[None]:
        # 数据校验
        if not wf_execution_log_index.workflow_version:
            wf_execution_log_index.workflow_version = WorkflowExecutionDB.__version_none__
        with get_db_jw(db_session) as db:
            workflow_execution_db = JiuwenBaseRepository(db, WorkflowExecutionDB)
            return workflow_execution_db.unregister_dl_in_sql(find_id=wf_execution_log_index.model_dump())

    '''
    description: 获取一定范围内所有执行日志的创建list
    param {*} self
    param {WfExecutionLogsFilter} wf_execution_logs_filter
    param {*} dbsession     传入的db session
    return {*}
    '''

    def _get_execution_logs_create_list_with_dbsession(
        self, dbsession: Session, wf_execution_logs_filter: WfExecutionLogsFilter,
        call_type: ExecutionCallType | None = ExecutionCallType.workflow
    ) -> ResponseModel[ExecutionLogDebug]:
        if not wf_execution_logs_filter.workflow_version:
            wf_execution_logs_filter.workflow_version = WorkflowExecutionDB.__version_none__
        wf_execution_logs_filter = WfExecutionLogsFilter(**wf_execution_logs_filter.model_dump())
        find_id = wf_execution_logs_filter.model_dump(exclude_none=True)
        if call_type:
            find_id[self.call_type_field] = call_type.value
        # 需要从数据库中获取的字段
        cols_find = list(ExecutionLogCreateInfo.model_fields.keys())
        find_min_max = {self.creat_time_field: [wf_execution_logs_filter.start_time, wf_execution_logs_filter.end_time]}
        order_cols_desc = [self.creat_time_field]   # 降序排列
        workflow_execution_db = JiuwenBaseRepository(dbsession, WorkflowExecutionDB)
        db_res = workflow_execution_db.get_dl_in_sql_with_cols(find_id=find_id, cols_find=cols_find,
                                                            find_min_max=find_min_max, order_cols_desc=order_cols_desc)
        if db_res.code == status.HTTP_200_OK and db_res.data:
            logs_create_list = [ExecutionLogCreateInfo(**record) for record in db_res.data]
            db_res.data = ExecutionLogDebug(logs_create_list=logs_create_list)
        return db_res

    @with_exception_handling
    def get_execution_logs_create_list(self, wf_execution_logs_filter: WfExecutionLogsFilter,
                                       call_type: ExecutionCallType | None = ExecutionCallType.workflow, 
                                       db_session: Session | None = None) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            return self._get_execution_logs_create_list_with_dbsession(db, wf_execution_logs_filter, call_type=call_type)

    '''
    description: 获取workflow的某次执行日志详情
    param {*} self
    param {WfExecutionLogIndex} wf_execution_log_index
    param {*} dbsession     传入的db session
    return {*}
    '''

    def get_execution_log_with_dbsession(
        self, dbsession: Session, wf_execution_log_index: WfExecutionLogIndex
    ) -> ResponseModel[ExecutionLogDebug]:
        if not wf_execution_log_index.workflow_version:
            wf_execution_log_index.workflow_version = WorkflowExecutionDB.__version_none__
        workflow_execution_db = JiuwenBaseRepository(dbsession, WorkflowExecutionDB)
        db_res = workflow_execution_db.get_dl_in_sql(find_id=wf_execution_log_index.model_dump(), return_first_item=True,
                                                        return_declarativebase=True)
        if db_res.code != status.HTTP_200_OK:
            return db_res
        log_summary = ExecutionLogSummary.model_validate(db_res.data.to_dict())
        # 获取workflow执行信息中的共同字段
        details_common_fields_dict = {field: getattr(db_res.data, field)
                                                     for field in self.common_fields_extract_from_log_to_summary}
        workflow_execution_details_list = db_res.data.workflow_execution_details_list
        log_details = [TraceWorkflowSpan.model_validate(detail.to_dict() | details_common_fields_dict) 
                                                for detail in workflow_execution_details_list]
        db_res.data = ExecutionLogDebug(log_summary=log_summary, log_details=log_details)
        return db_res
    
    @with_exception_handling
    def get_execution_log(self, wf_execution_log_index: WfExecutionLogIndex, db_session: Session | None = None) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            return self.get_execution_log_with_dbsession(db, wf_execution_log_index)

    '''
    description: 进行调试日志界面时，返回所有日志create list和最新日志详情
    param {*} self
    param {WorkflowId} workflow_id
    return {*}
    '''
    @with_exception_handling
    def enter_execution_logs_debug(self, workflow_id: WorkflowId, call_type: ExecutionCallType | None = ExecutionCallType.workflow, 
                                   db_session: Session | None = None) -> ResponseModel[ExecutionLogDebug]:
        with get_db_jw(db_session) as db:
            # 获取workflow的运行create list
            logs_create_list_db_res = self._get_execution_logs_create_list_with_dbsession(db, workflow_id,  
                                                                                          call_type=call_type)
            if logs_create_list_db_res.code != status.HTTP_200_OK or not logs_create_list_db_res.data \
                        or not logs_create_list_db_res.data.logs_create_list:
                return logs_create_list_db_res
            # 获取最新运行日志的数据
            logs_create_list: list[ExecutionLogCreateInfo] = logs_create_list_db_res.data.logs_create_list
            lastest_trace_id = logs_create_list[0].trace_id
            wf_execution_log_index = WfExecutionLogIndex.model_validate(
                workflow_id.model_dump() | {"trace_id": lastest_trace_id})
            laster_execution_log_db_res = self.get_execution_log_with_dbsession(db, wf_execution_log_index)
            if laster_execution_log_db_res.code != status.HTTP_200_OK:
                return laster_execution_log_db_res
            laster_execution_log_db_res.data.logs_create_list = logs_create_list
            return laster_execution_log_db_res


workflow_execution_repository = WorkflowExecutionRepository()