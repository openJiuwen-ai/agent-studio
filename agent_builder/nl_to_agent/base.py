# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Iterator


@dataclass
class OperatorInput:
    """输入数据结构。

    用于统一封装查询内容及检索结果，作为后续工作流或操作单元的输入。
    该类主要承载由检索器获取的多类资源信息，并保持结构化存储。

    Attributes:
        query (Optional[str]): 用户输入的查询字符串。
        plugin_info (Optional[list]): 检索到的插件相关信息列表。
        knowledge_info (Optional[list]): 检索到的知识库相关信息列表。
        sub_workflow_info (Optional[list]): 检索到的子工作流相关信息列表。
    """

    query: Optional[str] = None
    plugin_info: Optional[list] = None
    knowledge_info: Optional[list] = None
    sub_workflow_info: Optional[list] = None


@dataclass
class OperatorOutput:
    """输出数据结构。

    用于封装运算或处理后的最终结果，作为工作流或操作单元的输出。
    该类保持简洁，仅包含结果字段，便于后续模块直接使用。

    Attributes:
        result (str): 运算或处理的输出结果字符串。
    """

    result: str


class BaseOperator(ABC):
    def __init__(self):
        """初始化方法"""
        pass

    @abstractmethod
    def invoke(self, inputs: OperatorInput) -> Iterator[OperatorOutput]:
        """执行操作的方法，接受 OperatorInput 类型的输入并返回 OperatorOutput 类型的输出"""
        pass
