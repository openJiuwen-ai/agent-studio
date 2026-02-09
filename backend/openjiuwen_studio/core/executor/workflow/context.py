#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode

DEPTH_LIMIT = 5

class Context:

    def __init__(self, parent = None):
        if parent is None:
            self.depth = 0
        else:
            self.depth = parent.get_depth() + 1
        if self.depth > DEPTH_LIMIT:
            raise JiuWenExecuteException(
                StatusCode.WORKFLOW_NESTING_DEPTH_ERROR.code,
                StatusCode.WORKFLOW_NESTING_DEPTH_ERROR.errmsg.format(msg=str(DEPTH_LIMIT))
            )
        self.parent = parent

    def get_depth(self) -> int:
        return self.depth
