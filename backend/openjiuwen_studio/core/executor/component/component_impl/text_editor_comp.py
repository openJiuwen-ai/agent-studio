#!/usr/bin/python3.10
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved
import re
from typing import Any, Dict, List
from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.workflow.components import Session

from openjiuwen_studio.core.executor.component.component_impl.user_output_comp import has_double_braces
from openjiuwen_studio.core.common.dsl import TextEditorConfig, TextEditorType
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode

# {
# 	"id": "TextEditor1",
# 	"version": "",
# 	"name": "",
# 	"description": "",
# 	"type": "jiuwen.TextEditorComponent",
# 	"typeVersion": "1.0.0",
# 	"inputs": {
# 		"input1": "${LLM1}",
# 		"input2": "${LLM2}"
# 	},
# 	"outputs": {},
# 	"configs": {
# 		"edit_type": "StringConcatenation #(or StringSplitting)",
# 		"delimiter": ",",
# 		"concatenate_format": "THE LLM RESULT IS: {{input1}} AND THE OTHER LLM RESULT IS: {{input2}}"
# 	}
# }


class TextEditorComponent(WorkflowComponent):
    def __init__(self, node_id: str, conf: TextEditorConfig, output_name: str) -> None:
        super().__init__()
        self.conf: TextEditorConfig = conf
        self.node_id: str = node_id
        self.edit_type: str = self.conf.edit_type
        self.output_name: str = output_name

    def render_complex_template(self, template: str, inputs: Dict[str, Any]) -> str:
        # 匹配 {{...}} 格式
        pattern = re.compile(r'\{\{([^}]+)\}\}')

        def replacer(match) -> str:
            expr = match.group(1).strip()  # 获取表达式内容
            # 解析对象属性{{变量名.子变量名}}
            if '.' in expr:
                parts = expr.split('.')
                current = inputs
                for part in parts:
                    if '[' in part and ']' in part:
                        array_name = part.split('[')[0]
                        index = int(part.split('[')[1].split(']')[0])
                        current = current[array_name][index]
                    else:
                        current = current[part]
                return str(current)
            # 解析{{变量名[数组索引]}}
            elif '[' in expr and ']' in expr:
                array_name = expr.split('[')[0]
                index = int(expr.split('[')[1].split(']')[0])
                return str(inputs[array_name][index])
            # 解析{{变量名}}
            else:
                return str(inputs.get(expr, match.group(0)))

        return pattern.sub(replacer, template)

    def multi_delimiter_split(self, text: str, delimiters: List[str]) -> List[str]:
        if not delimiters:
            return [text]
        split_result = [text]
        for d in delimiters:
            new_result = []
            for item in split_result:
                if item:
                    new_result.extend([part.strip() for part in item.split(d)])
            split_result = new_result
        return split_result

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        output_result = None
        if self.edit_type == TextEditorType.CONCATENATION.value:
            concatenate_format = self.conf.concatenate_format
            if has_double_braces(concatenate_format):
                output_result = self.render_complex_template(concatenate_format, inputs)
            else:
                output_result = concatenate_format
        else:
            if not self.conf.delimiters:
                raise JiuWenExecuteException(
                    StatusCode.TEXTEDITOR_COMPONENT_INVOKE_ERROR.code,
                    StatusCode.TEXTEDITOR_COMPONENT_INVOKE_ERROR.errmsg.format(msg="文本编辑节点分隔符异常"),
                    node_id=self.node_id
                )
            input_value = list(inputs.values())[0]
            output_result = self.multi_delimiter_split(str(input_value), self.conf.delimiters)
        return {self.output_name: output_result}


