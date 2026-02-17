#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict, List

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.dsl import (
    HttpRequestConfig,
    ExceptHandlingMethod,
    ExceptConfig,
    Connection
)
from openjiuwen_studio.core.executor.component.compile import util
from openjiuwen_studio.core.executor.component.component_impl.http_request_comp import (
    HttpRequestComponent,
    ExceptedCondition,
    DefaultCondition,
)
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


class HttpRequestCompCompiler(BaseCompCompiler):
    def __init__(
        self, node_id: str, comp_config_dict: Dict[str, Any], workflow_connections: List[Connection]
    ) -> None:
        super().__init__()
        self.comp_config_dict: Dict[str, Any] = comp_config_dict
        self.node_id: str = node_id
        self.workflow_connections: List[Connection] = workflow_connections

    def compile(self) -> HttpRequestComponent:
        if not self.comp_config_dict:
            raise JiuWenExecuteException(
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.code,
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.errmsg.format(
                    msg="Node data <comp_config_dict> is empty"
                ),
                node_id=self.node_id,
            )
        try:
            http_request_config = HttpRequestConfig.model_validate(self.comp_config_dict)
        except Exception as e:
            raise JiuWenExecuteException(
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.code,
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.errmsg.format(
                    msg=f"Node parameter configuration validation failed: {str(e)}"
                ),
                node_id=self.node_id,
            ) from e

        http_request_component = HttpRequestComponent(self.node_id, http_request_config)

        # Only add exception routing if the exception handling method requires it
        if (
            http_request_config.exception_config.except_handling_method
            == ExceptHandlingMethod.EXECUTE_EXCEPT_STEP
        ):
            http_request_component = self._add_except_router(
                http_request_config.exception_config, http_request_component
            )
        else:
            # For BREAK or RETURN_CONTENT, add simple routing to next node
            excepted_condition = ExceptedCondition()
            default_condition = DefaultCondition(excepted_condition)
            http_request_component.set_excepted_condition(excepted_condition)

            # Get all targets from this node (regardless of branch)
            all_targets = []
            for conn in self.workflow_connections:
                # Connection.source can be a string or list of strings
                source = conn.source if isinstance(conn.source, list) else [conn.source]
                if self.node_id in source:
                    all_targets.append(conn.target)

            if all_targets:
                http_request_component.add_branch(default_condition, all_targets, "default")

        return http_request_component

    def _add_except_router(
        self, exception_config: ExceptConfig, http_request_component: HttpRequestComponent
    ) -> HttpRequestComponent:
        router = exception_config.execute_exception_step
        if not router:
            logger.error(f"The branches in component id: {self.node_id} branchid is empty, please check!")
            raise JiuWenExecuteException(
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.code,
                StatusCode.HTTP_REQUEST_COMP_COMPILER_ERROR.errmsg.format(
                    msg=(
                        f"Failed to add exception route: Component [{self.node_id}] "
                        f"exception branch configuration is empty"
                    )
                ),
                node_id=self.node_id,
            )

        excepted_condition = ExceptedCondition()
        default_condition = DefaultCondition(excepted_condition)
        http_request_component.set_excepted_condition(excepted_condition)

        targets = util.get_targets(self.node_id, router.default_router_id, self.workflow_connections)
        logger.info(
            f"[DEBUG] Adding HTTP request component branch: node_id={self.node_id}, "
            f"condition=default_condition, target={targets}, branch_id={router.default_router_id}"
        )
        http_request_component.add_branch(default_condition, targets, router.default_router_id)

        if exception_config.except_handling_method == ExceptHandlingMethod.EXECUTE_EXCEPT_STEP:
            targets = util.get_targets(self.node_id, router.error_router_id, self.workflow_connections)
            logger.info(
                f"[DEBUG] Adding HTTP request component error branch: node_id={self.node_id}, "
                f"condition=excepted_condition, target={targets}, branch_id={router.error_router_id}"
            )
            http_request_component.add_branch(excepted_condition, targets, router.error_router_id)

        return http_request_component
