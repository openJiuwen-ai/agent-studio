from enum import Enum
from openjiuwen_studio.core.common.language_thread_context import get_language


class AgentDefaults(Enum):
    """Agent default messages with multi-language support."""

    OPENING_REMARKS = (
        "OPENING_REMARKS",
        "您好！我是您的智能助手，很高兴为您服务。请问有什么可以帮助您的吗？",
        "Hello! I'm your AI assistant. What can I do for you?"
    )
    DEFAULT_RESPONSE = (
        "DEFAULT_RESPONSE",
        "抱歉，我无法理解您的问题，请换一种方式表达",
        "Sorry, I cannot understand your question. Please try rephrasing it."
    )

    @property
    def msg(self):
        language = get_language()
        if language == 'zh-cn' or language == 'zh':
            return self.value[1]
        else:
            return self.value[2]
