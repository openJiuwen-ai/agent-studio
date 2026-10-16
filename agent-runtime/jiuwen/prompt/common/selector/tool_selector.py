#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Tool selector"""

import copy
import json
from typing import List, Dict

import requests
from jiuwen.prompt.common.config import ToolsSelectConfig
from pydantic import BaseModel

REQUEST_TIMEOUT = 100


class ToolSelector(BaseModel):
    """Tool selector"""

    model_server_conf: Dict
    algorithm_paras: Dict

    def __init__(self):
        tool_select_config = ToolsSelectConfig()
        model_server_conf = {
            "url": tool_select_config["selector_url"],
            "headers": {
                "Content-Type": "application/json",
                "csb-token": tool_select_config["selector_csb_token"],
            },
            "timeout": int(tool_select_config["selector_timeout"]),
        }
        algorithm_paras = {
            "batch_size": int(tool_select_config["batch_size"]),
            "topk": int(tool_select_config["topk"]),
            "threshold": float(tool_select_config["threshold"]),
        }

        super().__init__(
            algorithm_paras=algorithm_paras, model_server_conf=model_server_conf
        )

    def select(self, query: str, tools: List[Dict], **kwargs) -> List[Dict]:
        """select tools"""
        if not isinstance(tools, list):
            raise ValueError(
                f"selector: content type is unstructured, content should be list[str] or str; "
                f"but got {type(tools)}"
            )
        algorithm_paras = copy.deepcopy(self.algorithm_paras)
        algorithm_paras.update(
            {key: value for key, value in kwargs.items() if key in self.algorithm_paras}
        )

        return self._perform(query, tools, algorithm_paras)

    def _postprocess(self, tools: List[Dict]) -> List[Dict]:
        count = 0
        for tool in tools:
            if tool.get("score", 0) >= self.algorithm_paras["threshold"]:
                count += 1
        return tools[: max(self.algorithm_paras["topk"], count)]

    def _perform(
        self, query: str, tools: list[Dict], algorithm_paras: Dict
    ) -> List[Dict]:
        """perform tool selection

        Args:
            query: user input query
            tools: tool api list
            algorithm_paras: algorithm_paras when run

        Returns:
            tool list after selection
        """
        tool_desc_list = []
        desc_to_index = {}
        for index, tool in enumerate(tools):
            desc = tool.get("description", "")
            tool_desc_list.append(desc)
            desc_to_index[desc] = index
        request_body = {
            "query": query,
            "tool_desc_list": tool_desc_list,
            "type": "reranker",
            "batch_size": self.algorithm_paras["batch_size"],
        }
        request_body.update(algorithm_paras)
        try:
            res = requests.Session().post(
                url=self.model_server_conf.get("url"),
                headers=self.model_server_conf.get("headers"),
                json=request_body,
                timeout=REQUEST_TIMEOUT,
            )
            res = json.loads(res.content.decode("utf-8"))
            tool_rank_list = res.get("result")
            for tool in tool_rank_list:
                tools[desc_to_index.get(tool[0], 0)].update({"score": tool[1]})
            tools = self._postprocess(
                sorted(tools, key=lambda k: k.get("score", 0), reverse=True)
            )

        except Exception as error:
            raise ValueError("selector perform error.") from error

        if not isinstance(tools, list):
            raise ValueError("selector perform error: answer_list is not list")

        return tools
