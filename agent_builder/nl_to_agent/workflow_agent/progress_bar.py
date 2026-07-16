# BASE
MESSAGE_TYPE = "message_type"
ANSWER = "answer"
STATUS = "status"
RESULT = "result"
PROCESS = "progress"
CONTENT = "content"

# Result
SOP = "sop"
MERMAID = "mermaid"
WORKFLOW_AGENT_DL = "workflow_agent_dl"
WORKFLOW_AGENT_IR = "workflow_agent_ir"
MODIFY_PROMPT = "modify_prompt"
CHITCHAT = "chitchat"
QUESTION = "question"
LLM_AGENT_IR = "llm_agent_ir"
QUESTION_WITHOUT_OPTION = "question_no_opt"

# content
MERMAID_CHUNK = "mermaid_chunk"
SOP_CHUNK = "sop_chunk"
CHITCHAT_CHUNK = "chitchat_chunk"
LLM_AGENT_IR_CHUNK = "llm_agent_ir_chunk"

# workflow status
HD0 = "state_0"  # 初始阶段(0)
HD1 = "state_1"  # 流程判断(1)
HD2 = "state_2"  # 流程设计(2)
HD3 = "state_3"  # 流程修改(3)
HD4 = "state_4"  # 工作流生成(4)。

# agent status

# progress
NODE_PROCESS = "node_process"


def status_msg(answer: str, msg_type: str, status_id: str = "null"):
    return {
        "type_label": STATUS,
        "answer": answer,
        "message_type": msg_type,
        "status_id": status_id,
    }


def progress_msg(node, generated_count, total_count, elapsed, progress):
    # 1. 计算剩余节点数
    remaining_nodes = total_count - generated_count

    # 2. 计算剩余时间 (基于每个节点的平均生成时间)
    remaining_time = 0
    if generated_count > 0:
        # 平均每个节点耗时 = 总耗时 / 已生成节点数
        avg_time_per_node = elapsed / generated_count
        # 剩余时间 = 平均耗时 * 剩余节点数
        remaining_time = int(avg_time_per_node * max(0, remaining_nodes))
    details = {
        "generated_count": generated_count,
        "elapsed_time": elapsed,
        "total_num": total_count,
        "remaining_time": remaining_time,
        "node": {
            "id": node.get("id", "null"),
            "type": node.get("type", "null"),
            "parameters": node.get("parameters", "null"),
            "next": node.get("next", "null"),
        },
    }

    return {
        "type_label": PROCESS,
        "message_type": NODE_PROCESS,
        "answer": f"已生成节点: {node.get('id')} ({node.get('type')})",
        "progress": progress,
        "details": details,
    }


def content_msg(answer: str, msg_type: str):
    return {"type_label": CONTENT, "answer": answer, "message_type": msg_type}


def result_msg(answer, message_type):
    return {
        "type_label": RESULT,
        "answer": answer,
        "message_type": message_type,
    }


def mermaid_msg(answer, message_type, info):
    return {
        "type_label": RESULT,
        "answer": answer,
        "message_type": message_type,
        "mermaid_info": info,
    }


def modify_msg(answer, message_type, turn, max_turn):
    return {
        "type_label": RESULT,
        "answer": answer,
        "message_type": message_type,
        "current_turn": turn,
        "max_turn": max_turn,
    }


# HD0 = "HANDLE_STATE_0" #初始阶段(0)
HD0_INIT = status_msg("已接受用户输入，准备开始", HD0, "HD0_INIT")
HD0_SOP_JUDGE = status_msg("正在根据用户输入是否需要构造SOP", HD0, "HD0_SOP_JUDGE")
HD0_CREATE_SOP = status_msg("用户未提供SOP，正在创建SOP", HD0, "HD0_CREATE_SOP")
HD0_TRANSFORM_SOP = status_msg(
    "用户已经提供SOP，正在优化用户SOP", HD0, "HD0_TRANSFORM_SOP"
)

# HD1 = "HANDLE_STATE_1" #流程判断(1)
HD1_DESIGN_SOP = status_msg("开始构建用户SOP", HD1, "HD1_DESIGN_SOP")
# HD2 = "HANDLE_STATE_2" #流程设计(2)
HD2_DESIGN_MERMAID = status_msg("开始构建工作流流程图", HD2, "HD2_DESIGN_MERMAID")

# HD3 = "HANDLE_STATE_3" #流程修改(3)
HD3_MODIFY_MERMAID = status_msg("正在根据用户输入修改流程图", HD3, "HD3_MODIFY_MERMAID")
# HD4 = "HANDLE_STATE_4" #工作流生成(4)。
HD4_CREATE_DL = status_msg("正在根据流程图创建工作流", HD4, "HD4_CREATE_DL")
HD4_VERIFY_DL = status_msg("WorkflowDL已生成，正在校验格式", HD4, "HD4_VERIFY_DL")
HD4_CREATE_DSL = status_msg("校验通过正在创建工作流", HD4, "HD4_CREATE_DSL")

"""执行 LLM Agent 的构建过程。

包括以下步骤：
1. 根据用户输入解析 query，并维护对话历史。
2. 调用输入适配器检索可用外部资源并更新。
3. 执行意图澄清阶段（AgentClarifier）。
    - 如果需要澄清，则返回澄清问题。
    - 如果已澄清，则继续后续阶段。
4. （可选）执行 Agent 设计阶段（AgentDesigner）。
5. 执行 Agent 构造阶段（AgentConstructor），生成最终的 Agent 定义。
"""

AGENT_HD0 = "state_0"  # 根据用户输入解析 query，并维护对话历史
AGENT_HD1 = "state_1"  # 调用输入适配器检索可用外部资源并更新
AGENT_HD2 = "state_2"  # 执行意图澄清阶段（AgentClarifier
AGENT_HD3 = "state_3"  # 如果需要澄清，则返回澄清问题
AGENT_HD4 = "state_4"  # 执行 Agent 构造阶段（AgentConstructor），生成最终的 Agent 定义
