# -*- coding: UTF-8 -*-
"""orchestration 栈 format_prompt 回归测试。

背景(2026-08-19 修复):format_prompt 曾对填入 ${query} 的整条 user 消息做
html.escape(),把工作流模板(模型文本 Prompt)里的 JSON 示例引号("key": "value")
和 "&" 连接符(e5051&n消费卡)转义成 &quot; / &amp;,破坏模型收到的格式指令,
导致弱模型输出劣化(card 前缀 cn借记卡 而非 n借记卡)。

本测试锁定回归:渲染后的模板内容必须原样进入 prompt,不允许任何 HTML 实体转义。
"""

from jiuwen.prompt.agent.common.utils import format_prompt

# 模拟渲染后的工作流模板:合法包含 JSON 引号、"&" 连接符、尖括号、单引号
RENDERED_TEMPLATE = (
    "你是一个智能助手，遵循以下JSON语法：\n"
    "{\n  \"key\": \"value\",\n}\n"
    "示例：用尾号5051的消费卡转账 -> \"card\": \"e5051&n消费卡\""
)

OUTPUTS_CONFIG_LIST = [
    {"id": "name", "type": "string", "description": "收款人"},
    {"id": "card", "type": "string"},
]

HTML_ENTITIES = ("&quot;", "&amp;", "&lt;", "&gt;", "&#x27;", "&apos;")


def _build_history():
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": RENDERED_TEMPLATE},
    ]


def test_json_query_not_html_escaped():
    """json 响应格式:${query} 内容原样注入,不产生任何 HTML 实体。"""
    history = _build_history()
    result = format_prompt(
        history, {"type": "json", "jsonInstruction": ""}, OUTPUTS_CONFIG_LIST
    )
    content = result[-1]["content"]

    for entity in HTML_ENTITIES:
        assert entity not in content, f"检测到 HTML 实体 {entity}"
    # 模板原文(引号、& 分隔符、尖括号)必须原样保留
    assert '"key": "value"' in content
    assert '"card": "e5051&n消费卡"' in content


def test_json_wrapper_and_schema_substituted():
    """json 分支:wrapper 注入、${json_schema} 替换、${query} 替换均生效。"""
    result = format_prompt(
        _build_history(),
        {"type": "json", "jsonInstruction": ""},
        OUTPUTS_CONFIG_LIST,
    )
    content = result[-1]["content"]

    assert "The question is:" in content
    assert "${query}" not in content
    assert "${json_schema}" not in content
    # outputs_config_list 生成的 schema 字段被注入
    assert "name" in content and "收款人" in content
    # 模板在 ${query} 位置
    assert content.index("The question is:") < content.index('"key": "value"')


def test_markdown_query_not_html_escaped():
    """markdown 响应格式:同样不允许 HTML 实体转义。"""
    result = format_prompt(
        _build_history(),
        {"type": "markdown", "markdownInstruction": ""},
        [],
    )
    content = result[-1]["content"]

    for entity in HTML_ENTITIES:
        assert entity not in content
    assert '"key": "value"' in content
    assert '"card": "e5051&n消费卡"' in content


def test_text_returns_history_unchanged():
    """text 响应格式:原样返回,不做任何包装。"""
    history = _build_history()
    result = format_prompt(history, {"type": "text"}, [])

    assert result is history
    assert result[-1]["content"] == RENDERED_TEMPLATE


def test_system_message_not_touched():
    """只有最后一条 user 消息被包装,system 等其它消息不受影响。"""
    result = format_prompt(
        _build_history(),
        {"type": "json", "jsonInstruction": ""},
        OUTPUTS_CONFIG_LIST,
    )
    assert result[0]["content"] == "system prompt"
