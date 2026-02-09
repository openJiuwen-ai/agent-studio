from typing import Callable, Any, Awaitable
from functools import wraps
from pydantic import ValidationError
from fastapi import status
from openjiuwen_studio.memory_engine_start import MemoryEngineManager
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.schemas.memory import (
    DeleteLongtermMem, DeleteVariable, UpdateLongtermMem,
    UpdateVariable, SearchLongtermMem, GetUserVar, DeleteScopeLongtermMem)

from openjiuwen.core.memory.manage.mem_model.memory_unit import MemoryType
from openjiuwen.core.common.logging import logger


def get_memory_engine():
    return MemoryEngineManager.get_instance()


def safe_get_memory_type(value_str: str) -> MemoryType:
    try:
        return MemoryType(value_str.lower())
    except ValueError:
        logger.error(f"'{value_str}' 不是有效的 MemoryType 值")
        return MemoryType.UNKNOWN  # 返回默认值


def with_exception_handling(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)  # 必须 await
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=type(e).__name__
            )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=type(e).__name__
            )

    return wrapper


@with_exception_handling
async def get_longterm_mem(req: SearchLongtermMem):
    memory_engine = get_memory_engine()
    memory_data = await memory_engine.get_user_mem_by_page(
        user_id=req.user_id,
        scope_id=req.group_id,
        page_size=req.num,
        page_idx=req.page,
        memory_type=safe_get_memory_type(req.memory_type)
    )
    return {"longterm_mem_data": memory_data}


@with_exception_handling
async def get_user_variable(req: GetUserVar):
    memory_engine = get_memory_engine()
    memory_data = await memory_engine.get_variables(
        user_id=req.user_id,
        scope_id=req.group_id,
        names=req.names
    )

    return {"variable_data": memory_data}


@with_exception_handling
async def delete_longterm_mem(req: DeleteLongtermMem):
    memory_engine = get_memory_engine()
    result = await memory_engine.delete_mem_by_id(
        user_id=req.user_id,
        scope_id=req.group_id,
        mem_id=req.mem_id,
    )
    return {"result": result}


@with_exception_handling
async def delete_user_variable(req: DeleteVariable):
    memory_engine = get_memory_engine()
    result = await memory_engine.delete_variables(
        user_id=req.user_id,
        scope_id=req.group_id,
        names=[req.name]
    )
    return {"result": result}


@with_exception_handling
async def update_longterm_mem(req: UpdateLongtermMem):
    memory_engine = get_memory_engine()
    result = await memory_engine.update_mem_by_id(
        user_id=req.user_id,
        scope_id=req.group_id,
        mem_id=req.mem_id,
        memory=req.content
    )
    return {"result": result}


@with_exception_handling
async def update_user_variable(req: UpdateVariable):
    memory_engine = get_memory_engine()
    result = await memory_engine.update_variables(
        user_id=req.user_id,
        scope_id=req.group_id,
        variables={req.name: req.mem}
    )
    return {"result": result}


@with_exception_handling
async def delete_longterm_mem_by_scope_id(req: DeleteScopeLongtermMem):
    memory_engine = get_memory_engine()
    result = await memory_engine.delete_mem_by_scope(
        scope_id=req.scope_id,
    )
    return {"result": result}
