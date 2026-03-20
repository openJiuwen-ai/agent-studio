#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum
from typing import Any, Dict
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field
T = TypeVar('T')


class DeployRequest(BaseModel):
    agent_id: str
    agent_name: str
    agent_version: str
    deployer_type: Optional[str] = None
    port: Optional[int] = None
    space_id: Optional[str] = None


class ResponseModel(BaseModel, Generic[T]):
    code: int
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
