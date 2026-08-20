# -*- coding: UTF-8 -*-
"""extension 栈 LLMChain._apply_format_instructions 回归测试。

背景(2026-08-19 修复):extension 栈的格式指令注入曾对 ${query} 内容做
html.escape()(与 orchestration 栈 format_prompt 的同源问题),把工作流模板
(模型文本 Prompt)里的 JSON 引号和 "&" 连接符转义成 &quot; / &amp;。
本测试锁定回归:user_content 必须原样注入,不允许任何 HTML 实体转义。
"""

from jiuwen.extension.workflow_node.llm_chain import LLMChain

RENDERED_TEMPLATE = (
    "你是一个智能助手，遵循以下JSON语法：\n"
    "{\n  \"key\": \"value\",\n}\n"
    "示例：用尾号5051的消费卡转账 -> \"card\": \"e5051&n消费卡\""
)

HTML_ENTITIES = ("&quot;", "&amp;", "&lt;", "&gt;", "&#x27;", "&apos;")


def _build_messages():
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": RENDERED_TEMPLATE},
    ]


def _apply(chain: LLMChain, messages):
    """统一入口:单点访问受保护方法,便于 pylint 豁免(G.CLS.11)。"""
    return chain._apply_format_instructions(messages)  # pylint: disable=protected-access


def test_json_instruction_not_html_escaped():
    """json 响应格式:${query} 内容原样注入,不产生任何 HTML 实体。"""
    chain = LLMChain(
        {"responseFormat": {"type": "json", "jsonInstruction": ""}}
    )
    result = _apply(chain, _build_messages())
    content = result[-1]["content"]

    for entity in HTML_ENTITIES:
        assert entity not in content, f"检测到 HTML 实体 {entity}"
    assert '"key": "value"' in content
    assert '"card": "e5051&n消费卡"' in content


def test_markdown_instruction_not_html_escaped():
    """markdown 响应格式:同样不允许 HTML 实体转义。"""
    chain = LLMChain(
        {"responseFormat": {"type": "markdown", "markdownInstruction": ""}}
    )
    result = _apply(chain, _build_messages())
    content = result[-1]["content"]

    for entity in HTML_ENTITIES:
        assert entity not in content
    assert '"key": "value"' in content


def test_text_passthrough():
    """text 响应格式:消息原样返回。"""
    chain = LLMChain({"responseFormat": {"type": "text"}})
    messages = _build_messages()
    result = _apply(chain, messages)

    assert result is messages
    assert result[-1]["content"] == RENDERED_TEMPLATE


def test_wrapper_and_query_substitution():
    """wrapper 注入且 ${query} 被替换为 user_content。"""
    chain = LLMChain(
        {"responseFormat": {"type": "json", "jsonInstruction": ""}}
    )
    result = _apply(chain, _build_messages())
    content = result[-1]["content"]

    assert "The question is:" in content
    assert "${query}" not in content
    assert content.index("The question is:") < content.index('"key": "value"')


def test_system_message_not_touched():
    """只有最后一条 user 消息被包装。"""
    chain = LLMChain(
        {"responseFormat": {"type": "json", "jsonInstruction": ""}}
    )
    result = _apply(chain, _build_messages())
    assert result[0]["content"] == "system prompt"


def test_custom_json_instruction_used():
    """自定义 jsonInstruction 优先生效,${query} 仍在其中被替换。"""
    chain = LLMChain(
        {
            "responseFormat": {
                "type": "json",
                "jsonInstruction": "自定义指令[${query}]",
            }
        }
    )
    result = _apply(chain, _build_messages())
    content = result[-1]["content"]

    assert content.startswith("自定义指令[")
    assert content.endswith("]")
    assert '"key": "value"' in content
