"""
Trace Summary Repository Implementation

Based on design document: TRACE_SUMMARY_SCHEMA.md
For workflow and agent execution summary data management
"""

import ast
import json
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from fastapi import status
from pydantic import ValidationError

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.models.trace_detail import TraceDetailDB
from openjiuwen_studio.models.trace_summary import TraceSummaryDB
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.execution_log import ExecutionLogSummary, InvokeExecuteInfo
from openjiuwen_studio.schemas.trace_summary import TraceSummary


def _calc_duration_ms(start_micros, end_micros) -> int | None:
    """
    Convert microseconds duration to milliseconds
    Returns None if calculation is not possible
    """
    if start_micros is None or end_micros is None:
        return None
    try:
        # Convert to integers for calculation
        start = int(start_micros)
        end = int(end_micros)
        duration_us = end - start
        return duration_us // 1000 if duration_us > 0 else None
    except (ValueError, TypeError):
        return None


def _normalize_dict_field(value) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        v = value.strip()
        try:
            return json.loads(v)
        except Exception:
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, str) and parsed:
                    return {"content": parsed}
                return None
            except Exception:
                if v:
                    return {"content": v}
                return None
    return None


def _to_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    try:
        v = int(value)
    except (ValueError, TypeError):
        return None
    if v > 10**14:
        ts = v / 1_000_000
    elif v > 10**11:
        ts = v / 1_000
    else:
        ts = v
    try:
        return datetime.fromtimestamp(ts)
    except Exception:
        return None


def _sort_components_by_start_time(components):
    """
    Recursively sort components and their children by start_timestamp
    
    Args:
        components: List of components to sort
        
    Returns:
        Sorted list of components
    """
    if not components:
        return components
    
    # Sort current level
    sorted_components = sorted(components, key=lambda x: x.start_timestamp or 0)
    
    # Recursively sort children
    for comp in sorted_components:
        if comp.child_invokes_execute_info:
            comp.child_invokes_execute_info = _sort_components_by_start_time(comp.child_invokes_execute_info)
    
    return sorted_components


def with_exception_handling(func):
    """Exception handling decorator"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Trace summary repository error: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Operation failed: {str(e)}",
                data=None,
            )

    return wrapper


def _extract_summary_execution_info_from_trace_detail(
    trace_details: List[Dict[str, Any]],
    base_start_time_micros: Optional[str] = None,
) -> List[InvokeExecuteInfo]:
    """
    Process WORKFLOW TraceDetail data

    Args:
        trace_details: List of TraceDetail data
        base_start_time_micros: Optional base start time in microseconds for calculating relative timestamps

    Returns:
        List[Dict[str, Any]]: Processed execution information list
    """
    execute_info_list: List[InvokeExecuteInfo] = []       # 最终返回的顶层执行信息
    running_component_execute_info: Dict[str, InvokeExecuteInfo] = {}     # 当前还在处理中的组件，key为span_id
    processed_components: Dict[str, InvokeExecuteInfo] = {}     # 已处理完成的组件，key为span_id

    # Use provided base_start_time_micros if available, otherwise get from trace_details
    execute_start_time = base_start_time_micros
    if execute_start_time is None:
        for d0 in trace_details:
            if d0.get("start_time_micros"):
                execute_start_time = d0.get("start_time_micros")
                break

    def _get_parent_component_id(span_id: str) -> str | None:
        """
        从span_id中提取父组件ID
        """
        if "." in span_id:
            # 分割span_id，取除最后一部分外的所有部分作为父组件ID
            parent_id = ".".join(span_id.split(".")[:-1])
            # 检查父组件是否存在
            if parent_id in running_component_execute_info or parent_id in processed_components:
                return parent_id
        return None

    def _component_process_over(detail: Dict[str, Any] | None, component_execute_info: InvokeExecuteInfo):
        """Complete component processing, reference WorkflowExecutionRepository logic"""
        if detail:
            status_code = detail.get("status_code")
            if status_code == "0" or status_code == "finish":
                component_execute_info.status = "finish"
            elif status_code == "interrupted":
                component_execute_info.status = "interrupted"
            elif status_code and status_code != "start":
                component_execute_info.status = "error"
            else:
                component_execute_info.status = status_code or "running"
            
            # Use component_actual_start_times for accurate duration calculation
            actual_start = component_actual_start_times.get(component_execute_info.invoke_id)
            end_time = detail.get("end_time_micros")
            
            if actual_start and end_time:
                duration = _calc_duration_ms(actual_start, end_time)
                if duration:
                    component_execute_info.duration = duration
            elif detail.get("start_time_micros") and detail.get("end_time_micros"):
                # Fallback to using the detail's start and end time if actual_start is not available
                duration = _calc_duration_ms(
                    detail.get("start_time_micros"), detail.get("end_time_micros")
                )
                if duration:
                    component_execute_info.duration = duration
            
            component_execute_info.outputs = _normalize_dict_field(detail.get("output"))
        else:
            component_execute_info.status = "interrupted"

        # 获取父组件ID
        parent_id = _get_parent_component_id(component_execute_info.invoke_id)
        
        # 保存到已处理组件列表
        processed_components[component_execute_info.invoke_id] = component_execute_info
        
        # 查找父组件
        parent_component = None
        if parent_id:
            if parent_id in running_component_execute_info:
                parent_component = running_component_execute_info[parent_id]
            elif parent_id in processed_components:
                parent_component = processed_components[parent_id]
        
        if parent_component:
            # 将当前组件添加到父组件的child_invokes_execute_info中
            if parent_component.child_invokes_execute_info is None:
                parent_component.child_invokes_execute_info = []
            # 检查是否已存在该子组件
            exists = any(child.invoke_id == component_execute_info.invoke_id for child in parent_component.child_invokes_execute_info)
            if not exists:
                parent_component.child_invokes_execute_info.append(component_execute_info)
        else:
            # 检查是否已存在于顶层列表
            exists = any(item.invoke_id == component_execute_info.invoke_id for item in execute_info_list)
            if not exists:
                # 如果没有父组件或父组件不在running中，添加到顶层执行信息列表
                execute_info_list.append(component_execute_info)

    # Track component actual start times for accurate duration calculation
    component_actual_start_times: Dict[str, str] = {}
    
    for detail in trace_details:
        span_id = detail.get("span_id")
        span_type = detail.get("span_type")
        span_name = detail.get("span_name")
        status_code = detail.get("status_code")
        inputs = _normalize_dict_field(detail.get("input"))
        
        # Component start or update
        if span_id in running_component_execute_info:
            # Component is already running, update it
            component_execute_info = running_component_execute_info[span_id]
            # Update status and other fields
            if detail.get("end_time_micros"):
                # Use actual start time for accurate duration calculation
                actual_start = component_actual_start_times.get(span_id)
                if actual_start:
                    duration = _calc_duration_ms(
                        actual_start,
                        detail.get("end_time_micros")
                    )
                    if duration:
                        component_execute_info.duration = duration
            component_execute_info.outputs = _normalize_dict_field(detail.get("output"))
            
            # If component is finished, process it
            if status_code and status_code != "start":
                component_execute_info.status = status_code
                running_component_execute_info.pop(span_id)
                _component_process_over(detail, component_execute_info)
        else:
            # New component
            component_execute_info = InvokeExecuteInfo(
                invoke_id=span_id,
                invoke_name=span_name,
                invoke_type=span_type,
                status=status_code or "start",
                inputs=inputs,
            )
            
            # Store actual start time for accurate duration calculation
            actual_start = detail.get("start_time_micros")
            if actual_start:
                component_actual_start_times[span_id] = actual_start
            
            if actual_start and execute_start_time:
                component_execute_info.start_timestamp = (
                    _calc_duration_ms(
                        execute_start_time, actual_start
                    )
                    or 0
                )

            # Check if this component is already processed
            if span_id not in processed_components:
                # If component is already finished, process it immediately
                if status_code and status_code != "start":
                    _component_process_over(detail, component_execute_info)
                else:
                    # Otherwise, save to running dictionary
                    running_component_execute_info[span_id] = component_execute_info

    # 处理剩余的running组件，这些组件没有结束记录
    while running_component_execute_info:
        span_id, component_execute_info = running_component_execute_info.popitem()
        # 检查是否已处理
        if span_id not in processed_components:
            _component_process_over(None, component_execute_info)

    # Ensure all components have start_timestamp set
    for _info in execute_info_list:
        if _info.start_timestamp is None:
            _info.start_timestamp = 0
        
    # Sort all components recursively using module-level function
    execute_info_list = _sort_components_by_start_time(execute_info_list)
    
    return execute_info_list


def _extract_agent_execution_info_from_trace_detail(
    trace_details: List[Dict[str, Any]],
) -> List[InvokeExecuteInfo]:
    execute_info_list: List[InvokeExecuteInfo] = []
    running_components: Dict[str, InvokeExecuteInfo] = {}
    processed_components: Dict[str, InvokeExecuteInfo] = {}  # Track all processed components to avoid duplicates
    component_time_map: Dict[str, Dict[str, Any]] = {}
    execute_start_time = None
    
    # Collect all studio_agent_workflow entries
    all_workflow_components = []
    for d in trace_details:
        if d.get("platform_type") == "studio_agent_workflow":
            all_workflow_components.append(d)
    
    # Sort all workflow components by start_time_micros for execution order
    all_workflow_components.sort(
        key=lambda x: int(x.get("start_time_micros")) if x.get("start_time_micros") else 0
    )
    
    # Get execute_start_time from the first available entry
    for d0 in trace_details:
        if d0.get("start_time_micros"):
            execute_start_time = d0.get("start_time_micros")
            break

    def _component_process_over(
        detail: Dict[str, Any] | None, component_execute_info: InvokeExecuteInfo
    ):
        if detail:
            sc = detail.get("status_code")
            if sc == "0" or sc == "finish":
                component_execute_info.status = "finish"
            elif sc == "interrupted":
                component_execute_info.status = "interrupted"
            elif sc and sc != "start":
                component_execute_info.status = "error"
            else:
                component_execute_info.status = sc or "running"
            
            # Get component time information from component_time_map for accurate duration calculation
            component_time_info = component_time_map.get(component_execute_info.invoke_id)
            start_time = component_time_info.get("start") if component_time_info else None
            end_time = component_time_info.get("end") if component_time_info else None
            
            # If component_time_map doesn't have complete information, try from detail
            if not start_time:
                start_time = detail.get("start_time_micros")
            if not end_time:
                end_time = detail.get("end_time_micros")
            
            if start_time and end_time:
                duration = _calc_duration_ms(start_time, end_time)
                if duration:
                    component_execute_info.duration = duration
            component_execute_info.outputs = _normalize_dict_field(detail.get("output"))
        else:
            component_execute_info.status = "interrupted"

        # For any workflow component, add its associated studio_agent_workflow components
        if (detail and 
            detail.get("platform_type") == "studio_agent" and 
            detail.get("span_type") == "workflow"):
            # Get workflow's time range
            workflow_start = detail.get("start_time_micros")
            workflow_end = detail.get("end_time_micros")
            
            # Collect studio_agent_workflow entries that fall within this workflow's time range
            # First, collect all start records within the time range
            start_records = []
            for wf_comp in all_workflow_components:
                wf_comp_start = wf_comp.get("start_time_micros")
                if wf_comp_start and workflow_start:
                    try:
                        # Convert time values to integers for comparison
                        wf_comp_start_int = int(wf_comp_start)
                        workflow_start_int = int(workflow_start)
                        workflow_end_int = int(workflow_end) if workflow_end else None
                        
                        # Check if this workflow component's start time is within the parent workflow's time range
                        if wf_comp_start_int >= workflow_start_int:
                            if workflow_end_int:
                                if wf_comp_start_int <= workflow_end_int:
                                    start_records.append(wf_comp)
                            else:
                                start_records.append(wf_comp)
                    except (ValueError, TypeError):
                        # Skip if time values cannot be converted
                        continue
            
            # Now, collect all records (start and finish) for each component
            associated_workflow_components = []
            processed_span_ids = set()
            
            # Create a map of span_id to all records
            span_id_to_records = {}
            for wf_comp in all_workflow_components:
                span_id = wf_comp.get("span_id")
                if span_id:
                    if span_id not in span_id_to_records:
                        span_id_to_records[span_id] = []
                    span_id_to_records[span_id].append(wf_comp)
            
            for start_record in start_records:
                span_id = start_record.get("span_id")
                if span_id and span_id not in processed_span_ids:
                    processed_span_ids.add(span_id)
                    
                    # Get all records for this span_id
                    records = span_id_to_records.get(span_id, [])
                    # Sort records by start_time_micros to ensure correct processing order
                    records.sort(key=lambda x: int(x.get("start_time_micros", 0)))
                    # Add all records to the list
                    associated_workflow_components.extend(records)
            
            if associated_workflow_components:
                # Process all associated workflow components and add as children
                wf_exec_infos = _extract_summary_execution_info_from_trace_detail(
                    associated_workflow_components,
                    base_start_time_micros=workflow_start
                )
                component_execute_info.child_invokes_execute_info = wf_exec_infos
                
                # Update the status of child components based on their finish events
                # Create a mapping of span_id to status from all trace details
                status_map = {}
                for d in trace_details:
                    if d.get("platform_type") == "studio_agent_workflow":
                        span_id = d.get("span_id")
                        status_code = d.get("status_code")
                        if span_id and status_code:
                            status_map[span_id] = status_code
                
                # Update the status of all child components
                def update_child_statuses(components):
                    for comp in components:
                        # Update status from status_map if available
                        if comp.invoke_id in status_map:
                            invoke_status = status_map[comp.invoke_id]
                            if invoke_status == "0" or invoke_status == "finish":
                                comp.status = "finish"
                            elif invoke_status == "interrupted":
                                comp.status = "interrupted"
                            elif invoke_status != "start":
                                comp.status = "error"
                        # Recursively update children
                        if comp.child_invokes_execute_info:
                            update_child_statuses(comp.child_invokes_execute_info)
                
                update_child_statuses(component_execute_info.child_invokes_execute_info)

        # Add to processed components
        processed_components[component_execute_info.invoke_id] = component_execute_info
        
        # Check if component already exists in execute_info_list before adding
        exists = any(item.invoke_id == component_execute_info.invoke_id for item in execute_info_list)
        if not exists:
            execute_info_list.append(component_execute_info)

    for detail in trace_details:
        if detail.get("platform_type") != "studio_agent":
            continue
        
        span_id = detail.get("span_id")
        span_type = detail.get("span_type")
        span_name = detail.get("span_name")
        status_code = detail.get("status_code")
        inputs = _normalize_dict_field(detail.get("input"))
        
        # Check if component has already been processed
        if span_id in processed_components:
            continue
            
        if status_code == "start" or not status_code:
            # Component is starting, check if it's already running
            if span_id not in running_components:
                c = InvokeExecuteInfo(
                    invoke_id=span_id,
                    invoke_name=span_name,
                    invoke_type=span_type,
                    status=status_code,
                    inputs=inputs,
                )
                if detail.get("start_time_micros") and execute_start_time:
                    c.start_timestamp = (
                        _calc_duration_ms(
                            execute_start_time, detail.get("start_time_micros")
                        )
                        or 0
                    )
                if detail.get("start_time_micros"):
                    component_time_map[span_id] = {
                        "start": detail.get("start_time_micros"),
                        "end": None,
                    }
                running_components[span_id] = c
        else:
            # Component is finishing
            c = running_components.pop(span_id, None)
            if c:
                if detail.get("end_time_micros"):
                    tm = component_time_map.get(span_id)
                    if tm is None:
                        tm = {"start": None, "end": None}
                        component_time_map[span_id] = tm
                    tm["end"] = detail.get("end_time_micros")
                _component_process_over(detail, c)
            else:
                # Component not found in running_components, create it
                logger.warning(
                    f"Missing start record for agent component: {span_id}"
                )
                c = InvokeExecuteInfo(
                    invoke_id=span_id,
                    invoke_name=span_name,
                    invoke_type=span_type,
                    status="start",
                    inputs=inputs,
                )
                if detail.get("start_time_micros") and execute_start_time:
                    c.start_timestamp = (
                        _calc_duration_ms(
                            execute_start_time, detail.get("start_time_micros")
                        )
                        or 0
                    )
                _component_process_over(detail, c)

    # Process remaining running components, but only if they haven't been processed
    for sid, c in list(running_components.items()):
        if sid not in processed_components:
            _component_process_over(None, c)
        # Remove from running_components regardless
        running_components.pop(sid)

    for _info in execute_info_list:
        if _info.start_timestamp is None:
            _info.start_timestamp = 0
    
    # Sort all components recursively using module-level function
    execute_info_list = _sort_components_by_start_time(execute_info_list)
    
    return execute_info_list


class TraceSummaryRepository:
    """Trace Summary Repository"""

    def __init__(self):
        pass

    @with_exception_handling
    def create_trace_summary_by_trace_id(
        self, 
        trace_id: str, 
        input: Optional[dict] = None, 
        output: Optional[dict] = None
    ) -> ResponseModel[None]:
        """
        Create TraceSummary record from TraceDetail data

        Args:
            trace_id: Trace ID

        Returns:
            ResponseModel: Creation result
        """
        with get_db_jw() as db:
            # Query all TraceDetail records with same trace_id
            detail_base_repo = JiuwenBaseRepository(db, TraceDetailDB)
            find_id = {"trace_id": trace_id}

            detail_result = detail_base_repo.get_dl_in_sql_with_cols(
                find_id=find_id, order_cols_asc=["start_time_micros"]
            )

            if detail_result.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=detail_result.code,
                    message=f"Failed to query TraceDetail records: {detail_result.message}",
                    data=None,
                )

            if not detail_result.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message=f"No TraceDetail records found for trace_id: {trace_id}",
                    data=None,
                )

            trace_details = detail_result.data

            first_detail = trace_details[0]
            space_id = first_detail.get("space_id")
            business_id = first_detail.get("business_id")
            business_type = first_detail.get("business_type")
            if business_type == "AGENT":
                if not input:
                    inp = None
                    for d in trace_details:
                        if d.get("platform_type") == "studio_agent":
                            inp = _normalize_dict_field(d.get("input"))
                            break
                    inputs = inp
                else:
                    inputs = input
                
                if not output:
                    outp = None
                    for d in reversed(trace_details):
                        if d.get("platform_type") == "studio_agent":
                            outp = _normalize_dict_field(d.get("output"))
                            if outp is not None:
                                break
                    outputs = outp
                else:
                    outputs = output
            else:
                inputs = _normalize_dict_field(first_detail.get("input"))
                outputs = _normalize_dict_field(trace_details[-1].get("output"))

            start_time = None
            end_time = None

            if business_type == "AGENT":
                for d in trace_details:
                    if (
                        start_time is None
                        and d.get("platform_type") == "studio_agent"
                        and d.get("start_time_micros")
                    ):
                        start_time = d.get("start_time_micros")
                    if d.get("platform_type") == "studio_agent" and d.get(
                        "end_time_micros"
                    ):
                        de = d["end_time_micros"]
                        try:
                            de_int = int(de)
                            end_time_int = int(end_time) if end_time else None
                            if end_time_int is None or de_int > end_time_int:
                                end_time = de
                        except (ValueError, TypeError):
                            continue
            else:
                for detail in trace_details:
                    if start_time is None and detail.get("start_time_micros"):
                        start_time = detail.get("start_time_micros")
                    if detail.get("end_time_micros"):
                        detail_end = detail["end_time_micros"]
                        try:
                            detail_end_int = int(detail_end)
                            end_time_int = int(end_time) if end_time else None
                            if end_time_int is None or detail_end_int > end_time_int:
                                end_time = detail_end
                        except (ValueError, TypeError):
                            continue
            # Calculate execution duration (milliseconds)
            duration = _calc_duration_ms(start_time, end_time)

            span_status_map: Dict[str, set] = {}
            for d in trace_details:
                sid = d.get("span_id")
                sc = d.get("status_code")
                if sc is None or sc == "":
                    sc = "start"
                elif sc == "0":
                    sc = "finish"
                s = span_status_map.get(sid)
                if s is None:
                    s = set()
                    span_status_map[sid] = s
                s.add(sc)

            if business_type == "AGENT":
                span_status_map = {
                    k: v
                    for k, v in span_status_map.items()
                    if any(x != "start" for x in v)
                }

            has_error = any(
                any(x not in ("start", "finish", "interrupted") for x in v)
                for v in span_status_map.values()
            )
            has_interrupted = any(
                "interrupted" in v for v in span_status_map.values()
            )
            if has_error:
                overall_status = "error"
            elif has_interrupted:
                overall_status = "interrupted"
            else:
                all_finished = (
                    all("finish" in v for v in span_status_map.values())
                    if span_status_map
                    else False
                )
                if all_finished:
                    overall_status = "finish"
                else:
                    has_any_finish = any(
                        "finish" in v for v in span_status_map.values()
                    )
                    overall_status = "running" if has_any_finish else "start"

            if business_type == "AGENT":
                execute_info_models = _extract_agent_execution_info_from_trace_detail(
                    trace_details
                )
                ag_name = None
                ag_version = None
                for d in trace_details:
                    if d.get("platform_type") == "studio_agent":
                        if ag_name is None:
                            ag_name = d.get("span_name")
                        if ag_version is None:
                            ag_version = d.get("agent_version") or d.get("version")
                        if ag_name or ag_version:
                            break
                ag_wrapper = InvokeExecuteInfo(
                    invoke_id=business_id,
                    invoke_type="agent",
                    invoke_name="agent",
                    invoke_version=ag_version,
                    status=overall_status,
                    inputs=inputs,
                    outputs=outputs,
                    duration=duration,
                    start_timestamp=0,
                )
                ag_wrapper.child_invokes_execute_info = execute_info_models
                execute_info_list = [
                    ag_wrapper.model_dump(exclude_unset=True, exclude_none=True)
                ]
            else:
                execute_info_models = _extract_summary_execution_info_from_trace_detail(
                    trace_details
                )
                wf_wrapper = InvokeExecuteInfo(
                    invoke_id=business_id,
                    invoke_type="workflow",
                    invoke_name=None,
                    invoke_version=None,
                    status=overall_status,
                    inputs=inputs,
                    outputs=outputs,
                    duration=duration,
                    start_timestamp=0,
                )
                wf_wrapper.child_invokes_execute_info = execute_info_models
                execute_info_list = [
                    wf_wrapper.model_dump(exclude_unset=True, exclude_none=True)
                ]

            # Create TraceSummary data
            trace_summary_data = TraceSummary(
                space_id=space_id,
                business_id=business_id,
                business_type=business_type,
                trace_id=trace_id,
                mode=1,  # Default to published run mode
                duration=duration,
                status=overall_status,
                inputs=inputs,
                outputs=outputs,
                execute_info_list=execute_info_list,
                create_time=_to_datetime(start_time),
            )

            # Create or update TraceSummary record
            summary_base_repo = JiuwenBaseRepository(db, TraceSummaryDB)
            summary_find_id = {"business_id": business_id, "trace_id": trace_id}

            result = summary_base_repo.register_dl_in_sql(
                find_id=summary_find_id,
                dl=trace_summary_data.model_dump(exclude_unset=True),
            )

            return ResponseModel(
                code=result.code,
                message=f"Successfully created TraceSummary from {len(trace_details)} TraceDetail records: {result.message}",
                data={
                    "trace_id": trace_id,
                    "detail_count": len(trace_details),
                    "summary": trace_summary_data,
                },
            )

    @with_exception_handling
    def get_trace_summary_list(
        self, business_id: str, business_type: str
    ) -> ResponseModel:
        """
        Args:
            business_id: agent ID or workflow ID

        Returns:
            ResponseModel: trace summary list
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceSummaryDB)

            find_id = {"business_type": business_type, "business_id": business_id}

            # Query required fields
            result = base_repo.get_dl_in_sql_with_cols(
                find_id=find_id,
                cols_find=["trace_id", "create_time"],
                order_cols_desc=["create_time"],
            )

            if result.code != status.HTTP_200_OK:
                return result

            data_list = [
                {"create_time": d.get("create_time"), "trace_id": d.get("trace_id")}
                for d in (result.data or [])
            ]

            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Retrieved {len(data_list)} trace summary records",
                data=data_list,
            )

    @with_exception_handling
    def get_trace_summary_by_trace_id(self, trace_id: str) -> ResponseModel:
        """Query record by trace_id

        Args:
            trace_id: Trace ID

        Returns:
            ResponseModel: trace summary record
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceSummaryDB)

            find_id = {"trace_id": trace_id}
            result = base_repo.get_dl_in_sql_with_cols(find_id=find_id)

            if result.code != status.HTTP_200_OK:
                return result

            if not result.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Trace summary record not found",
                    data=None,
                )
            row = result.data[0]
            exec_infos = []
            for item in row.get("execute_info_list") or []:
                try:
                    exec_infos.append(InvokeExecuteInfo(**item))
                except Exception as exc:
                    # 兜底其他构造失败
                    logger.warning(
                        "Skip execute_info with wrong types | error=%s item=%r",
                        exc, item
                    )
                    continue
            summary = ExecutionLogSummary(
                trace_id=row.get("trace_id"),
                create_time=row.get("create_time"),
                duration=row.get("duration"),
                status=row.get("status") or "unknown",
                inputs=row.get("inputs"),
                outputs=row.get("outputs"),
                input_tokens=row.get("input_tokens"),
                output_tokens=row.get("output_tokens"),
                execute_info_list=exec_infos or None,
            )
            _normalize_start_timestamp(summary.execute_info_list)
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Trace summary retrieved successfully",
                data=summary.model_dump(),
            )

    @with_exception_handling
    def delete_whole_trace_by_trace_id(self, trace_id: str) -> ResponseModel:
        """Delete trace summary and all related trace detail records by trace_id

        Args:
            trace_id: Trace ID

        Returns:
            ResponseModel: Deletion result
        """
        with get_db_jw() as db:
            # Query trace summary record to delete
            summary_base_repo = JiuwenBaseRepository(db, TraceSummaryDB)
            detail_base_repo = JiuwenBaseRepository(db, TraceDetailDB)

            summary_find_id = {"trace_id": trace_id}
            detail_find_id = {"trace_id": trace_id}

            # Query summary record
            summary_query = summary_base_repo.get_dl_in_sql_with_cols(
                find_id=summary_find_id
            )

            if summary_query.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to query trace summary records",
                    data=None,
                )

            if not summary_query.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Trace summary record not found",
                    data=None,
                )

            # Query detail record count
            detail_query = detail_base_repo.get_dl_in_sql_with_cols(
                find_id=detail_find_id
            )
            detail_count = len(detail_query.data) if detail_query.data else 0

            # Delete detail records
            if detail_count > 0:
                detail_delete = detail_base_repo.unregister_dl_in_sql(
                    find_id=detail_find_id
                )
                if detail_delete.code != status.HTTP_200_OK:
                    return ResponseModel(
                        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        message="Failed to delete trace detail records",
                        data=None,
                    )

            # Delete summary record
            summary_delete = summary_base_repo.unregister_dl_in_sql(
                find_id=summary_find_id
            )

            return ResponseModel(
                code=summary_delete.code,
                message=summary_delete.message,
                data={
                    "summary_count": len(summary_query.data)
                    if summary_query.data
                    else 0,
                    "detail_count": detail_count,
                },
            )

    @with_exception_handling
    def get_latest_trace_summary(
        self, business_id: str, business_type: str
    ) -> ResponseModel:
        """Get latest trace_summary by business_id

        Args:
            business_id: agent ID or workflow ID

        Returns:
            ResponseModel: Complete trace record
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceSummaryDB)

            # Query latest workflow trace summary
            find_id = {"business_type": business_type, "business_id": business_id}

            summary_result = base_repo.get_dl_in_sql_with_cols(
                find_id=find_id,
                order_cols_desc=["create_time"],
            )

            if summary_result.code != status.HTTP_200_OK:
                return summary_result

            if not summary_result.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message=f"No trace summary records found for {business_type}.{business_id}",
                    data=None,
                )
            row = summary_result.data[0]
            exec_infos = []
            for item in row.get("execute_info_list") or []:
                try:
                    exec_infos.append(InvokeExecuteInfo(**item))
                except ValidationError as exc:
                    logger.warning(
                        "Skip invalid execute_info item | error=%s item=%r",
                        exc.errors(), item
                    )
                    continue
                except Exception as exc:
                    logger.warning(
                        "Skip execute_info with wrong types | error=%s item=%r",
                        exc, item
                    )
                    continue
            summary = ExecutionLogSummary(
                trace_id=row.get("trace_id"),
                create_time=row.get("create_time"),
                duration=row.get("duration"),
                status=row.get("status") or "unknown",
                inputs=row.get("inputs"),
                outputs=row.get("outputs"),
                input_tokens=row.get("input_tokens"),
                output_tokens=row.get("output_tokens"),
                execute_info_list=exec_infos or None,
            )
            _normalize_start_timestamp(summary.execute_info_list)
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Complete trace record retrieved successfully",
                data=summary.model_dump(),
            )


trace_summary_repository = TraceSummaryRepository()


def _normalize_start_timestamp(infos: List[InvokeExecuteInfo] | None):
    if not infos:
        return
    for info in infos:
        if info.start_timestamp is None:
            info.start_timestamp = 0
        if info.child_invokes_execute_info:
            _normalize_start_timestamp(info.child_invokes_execute_info)