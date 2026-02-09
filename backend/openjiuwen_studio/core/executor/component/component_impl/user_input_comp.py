#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
from typing import Any, List

from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.session.node import Session
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.dsl import UserInputsConfig, UserInputElem
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


# {
#     "id": "UserInput1",
#     "version": "",
#     "name": "",
#     "description": "",
#     "type": "jiuwen.UserInputComponent",
#     "typeVersion": "1.0.0",
#     "inputs": {},
#     "outputs": {},
#     "configs": {
#        "inputs": {
#         {"input_name": "AA", "description": "", "type":"str", "required": True},
#         {"input_name": "BB", "description": "", "type":"int", "required": True},
#         {"input_name": "CC", "description": "", "type":"bool", "required": False}
#        }
#     }
# }

# user_input = InteractiveInput()
# user_input.update(self.node_id, {"AA": "ishshe", "BB": 444, "CC": 1})


class UserInputComponent(WorkflowComponent):
    def __init__(self, conf: UserInputsConfig) -> None:
        super().__init__()
        self.input_conf_list: List[UserInputElem] = conf.inputs

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        result = await session.interact(self.input_conf_list)
        for input_elem in self.input_conf_list:
            if not isinstance(input_elem, UserInputElem):
                raise ValueError("Node data type is wrong")

            value = result.get(input_elem.input_name)
            if value is None:
                if input_elem.required is True:
                    raise JiuWenExecuteException(
                        StatusCode.USERINPUT_COMPONENT_INVOKE_ERROR.code,
                        StatusCode.USERINPUT_COMPONENT_INVOKE_ERROR.errmsg,
                    )
                continue

            if input_elem.type:
                try:
                    if input_elem.type == "integer":
                        result[input_elem.input_name] = int(value)
                    elif input_elem.type == "number":
                        result[input_elem.input_name] = float(value)
                    elif input_elem.type == "string":
                        result[input_elem.input_name] = str(value)
                    elif input_elem.type == "boolean":
                        if isinstance(value, str):
                            if value.lower() == "true":
                                result[input_elem.input_name] = True
                            elif value.lower() == "false":
                                result[input_elem.input_name] = False
                        else:
                            result[input_elem.input_name] = bool(value)
                except Exception as e:
                    logger.warning(
                        f"Failed to convert input value '{value}' to type '{input_elem.type}' "
                        f"for field '{input_elem.input_name}': {e}"
                    )
        return result
