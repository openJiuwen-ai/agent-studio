"""
Trace Detail Repository Implementation

Based on design document: WORKFLOW_TRACE_SCHEMA.md
Unified trace data repository, replacing the original workflow and agent separate design
"""

from functools import wraps
from typing import Any, Dict, List, Optional

from fastapi import status

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.models.trace_detail import TraceDetailDB
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.trace_detail import TraceDetail


def with_exception_handling(func):
    """Exception handling decorator"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Trace detail repository error: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Operation failed: {str(e)}",
                data=None,
            )

    return wrapper


class TraceDetailRepository:
    """Unified Trace Detail Repository"""

    def __init__(self):
        pass

    @with_exception_handling
    def create_trace_detail(self, trace_data: TraceDetail) -> ResponseModel:
        """Create trace detail record

        Args:
            trace_data: TraceDetail model data

        Returns:
            ResponseModel: Creation result
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceDetailDB)

            # Convert Pydantic model to dictionary
            trace_dict = trace_data.model_dump(exclude_unset=True)
            return base_repo.register_dl_in_sql(find_id=None, dl=trace_dict)

    @with_exception_handling
    def create_trace_details(self, trace_data_list: List[TraceDetail]) -> ResponseModel:
        """Batch create trace detail records for performance optimization

        Args:
            trace_data_list: List of TraceDetail model data

        Returns:
            ResponseModel: Batch creation result
        """
        if not trace_data_list:
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="No trace details to save",
                data=None
            )
        
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceDetailDB)

            # Convert Pydantic models to dictionaries
            trace_dicts = [trace_data.model_dump() for trace_data in trace_data_list]
            return base_repo.bulk_register_dl(trace_dicts)

    @with_exception_handling
    def get_trace_details_by_trace_id(self, trace_id: str) -> ResponseModel:
        """Get trace detail record list by trace_id

        Args:
            trace_id: Trace ID

        Returns:
            ResponseModel: Trace record list
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceDetailDB)

            find_id = {"trace_id": trace_id}
            result = base_repo.get_dl_in_sql_with_cols(
                find_id=find_id,
                order_cols_asc=["start_time_micros"]
            )

            if result.code != status.HTTP_200_OK:
                # Query failed, return failure status code
                return result

            if not result.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Trace records not found",
                    data=[]
                )

            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Retrieved {len(result.data)} trace records",
                data=result.data
            )

    @with_exception_handling
    def delete_trace_detail_by_trace_id(self, trace_id: str) -> ResponseModel:
        """Delete all related records by trace_id

        Args:
            trace_id: Trace ID

        Returns:
            ResponseModel: Deletion result
        """
        with get_db_jw() as db:
            base_repo = JiuwenBaseRepository(db, TraceDetailDB)

            find_id = {"trace_id": trace_id}

            # First query records to be deleted
            query_result = base_repo.get_dl_in_sql_with_cols(
                find_id=find_id
            )

            if query_result.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to query records for deletion",
                    data=None
                )

            if not query_result.data:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="No records found to delete",
                    data=0
                )

            # Delete all matching records
            delete_result = base_repo.unregister_dl_in_sql(find_id)

            # Return deleted record count
            deleted_count = len(query_result.data) if query_result.data else 0
            return ResponseModel(
                code=delete_result.code,
                message=delete_result.message,
                data=deleted_count
            )


trace_detail_repository = TraceDetailRepository()