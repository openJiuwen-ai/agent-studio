#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, List

from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow import BranchComponent
from openjiuwen.core.workflow.components.condition.condition import AlwaysTrue

from openjiuwen_studio.core.common.dsl import Connection, Branch
from openjiuwen_studio.core.executor.component.compile import util
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class BranchCompCompiler(BaseCompCompiler):
    """Branch Component Compiler"""

    def __init__(
            self,
            node_id: str,
            branch_comp_branches: List[Branch],
            workflow_connections: List[Connection]
    ) -> None:
        super().__init__()
        self.component_id = node_id
        self.branch_list = branch_comp_branches
        self.workflow_connections = workflow_connections

    def compile(self) -> BranchComponent:
        """Compile branch component"""
        branch_comp = BranchComponent()
        if not self.branch_list:
            logger.error(
                f"The branches in component id: {self.component_id} is empty, please check!"
            )
            raise JiuWenExecuteException(StatusCode.BRANCH_COMPONENT_COMPILE_ERROR.code,
                                         StatusCode.BRANCH_COMPONENT_COMPILE_ERROR.errmsg.format(
                                             msg=f"Failed to add branches: Component [{self.component_id}] branch configuration is empty"),
                                         node_id=self.component_id)

        for branch_info in self.branch_list:
            targets = util.get_targets(self.component_id, branch_info.branch_id, self.workflow_connections)
            logger.info(f"[DEBUG] 调用 branch_comp.add_branch: component_id={self.component_id}, condition={branch_info.bool_expression if branch_info.bool_expression else AlwaysTrue()}, target={targets}, branch_id={branch_info.branch_id}")
            branch_comp.add_branch(
                condition=branch_info.bool_expression if branch_info.bool_expression else AlwaysTrue(),
                target=targets, branch_id=branch_info.branch_id)
        return branch_comp
