from typing import Optional
from pydantic import BaseModel, Field
from openjiuwen.core.memory.manage.mem_model.memory_unit import MemoryType


class GetUserVar(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    names: Optional[list[str] | str] = Field(default=None, description="变量名称列表或单个名称")


class SearchLongtermMem(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    page: int = Field(default=1, ge=1, description="页码")
    num: int = Field(default=999, ge=1, description="每页数量")
    memory_type: str = Field(default=MemoryType.UNKNOWN.value, description="记忆类型")


class DeleteLongtermMem(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    mem_id: str = Field(..., description="记忆ID")


class DeleteVariable(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    name: str = Field(..., description="删除的变量名")


class UpdateLongtermMem(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    mem_id: str = Field(..., description="记忆ID")
    content: str = Field(..., description="更新后的记忆内容")


class UpdateVariable(BaseModel):
    user_id: str = Field(..., description="用户ID")
    group_id: str = Field(..., description="作用域ID")
    name: str = Field(..., description="变量名")
    mem: str = Field(..., description="更新后的变量值")


class DeleteScopeLongtermMem(BaseModel):
    scope_id: str = Field(..., description="作用域ID")
