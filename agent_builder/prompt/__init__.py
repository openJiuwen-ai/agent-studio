#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""JiuWen Prompt engine"""

__all__ = [
    "TemplateDuplicatedException",
    "TemplateNotFoundException",
    "Document",
]


from agent_builder.prompt.common.document import Document
from agent_builder.prompt.common.exception import (
    TemplateDuplicatedException,
    TemplateNotFoundException,
)
