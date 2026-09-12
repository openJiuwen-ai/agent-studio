# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
基于 card1.json IR 的工作流测试
测试 LLMChain 和 FlowCard 的集成工作

使用实际的 SiliconFlow 模型，不使用 mock
"""

import json
import os
import sys

import pytest

sys.path.insert(0, r"E:\backend")

from openjiuwen.core.workflow import Workflow, create_workflow_session
from openjiuwen.core.workflow import WorkflowExecutionState

from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_card import FlowCard, FlowCardConfig
from jiuwen.extension.workflow_node.llm_chain import LLMChain


def load_env_from_file(env_file_path):
    """从文件加载环境变量"""
    if os.path.exists(env_file_path):
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        print(f"已从 {env_file_path} 加载环境变量")
    else:
        print(f"警告: 环境变量文件 {env_file_path} 不存在")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Use Real Model")
async def test_complete_workflow_from_ir():
    """测试基于 card1.json 的完整工作流"""
    print("\n" + "=" * 60)
    print("测试基于 card1.json 的完整工作流 (使用实际模型)")
    print("=" * 60)

    # 打印环境配置
    print("\n模型配置:")
    print(f"  Provider: {os.getenv('LLM_PROVIDER', 'SiliconFlow')}")
    print(f"  API Base: {os.getenv('LLM_API_BASE', 'https://api.siliconflow.cn/v1')}")
    print(f"  Model: {os.getenv('LLM_MODEL_NAME', 'Qwen/Qwen3-32B')}")

    # 1. 创建工作流
    flow = Workflow()

    # 2. 添加开始组件（根据 card1.json 配置）
    start_config = {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [],
        },
    }

    start = Start(start_config)
    flow.set_start_comp("node_start", start, inputs_schema={"query": "${query}"})

    # 3. 添加 LLMChain 组件（根据 card1.json 配置）
    llm_config = {
        "model": {
            "provider": os.getenv("LLM_PROVIDER", "SiliconFlow"),
            "apiBase": os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1"),
            "apiKey": os.getenv("LLM_API_KEY", ""),
            "clientId": "siliconflow_client",
            "modelName": os.getenv("LLM_MODEL_NAME", "Qwen/Qwen3-32B"),
            "hyperParameters": {
                "top_p": float(os.getenv("LLM_TOP_P", "0.5")),
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0.5")),
                "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2048")),
            },
            "modelType": "qwen",
            "extension": {},
        },
        "templateContent": [{"content": "{{query}}", "role": "user"}],
        "responseFormat": {"type": "text"},
        "enableHistory": False,
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": False,
                }
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "该节点原始输出",
                    "id": "raw_output",
                    "type": "string",
                    "required": False,
                }
            ],
        },
        "deployMode": "workflow",
    }

    llm_chain = LLMChain(llm_config)

    flow.add_workflow_comp(
        "node_llm",
        llm_chain,
        inputs_schema={"userFields": {"query": "${node_start.systemFields.query}"}},
    )

    # 4. 添加 FlowCard 组件（根据 card1.json 配置）
    card_config = FlowCardConfig(
        template='{"title": "{{title}}", "content": "{{content}}", "URL": "{{URL}}"}',
        output_mode="separate",
    )

    flow_card = FlowCard(card_config)

    flow.add_workflow_comp(
        "node_173684576893",
        flow_card,
        inputs_schema={
            "title": "标题",
            "content": "${node_llm.userFields.raw_output}",
            "URL": "相关链接",
        },
    )

    # 5. 添加结束组件
    end_config = {
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "最终输出",
                    "id": "result",
                    "type": "string",
                    "required": False,
                }
            ],
            "outputs": [],
        },
        "responseTemplate": "{{result}}",
        "isStreamOut": False,
    }

    end = End(end_config)
    flow.set_end_comp(
        "node_end", end, inputs_schema={"result": "${node_173684576893.result}"}
    )

    # 6. 连接组件（根据 card1.json 的连接）
    flow.add_connection("node_start", "node_llm")
    flow.add_connection("node_llm", "node_173684576893")
    flow.add_connection("node_173684576893", "node_end")

    # 7. 执行工作流
    print("\n开始执行工作流...")
    print("正在调用大模型，请稍候...")
    session = create_workflow_session()

    result = await flow.invoke(
        inputs={"query": "你好，请简要介绍一下你自己"}, session=session
    )

    # 8. 验证结果
    print("\n工作流执行结果:")
    print(f"  状态: {result.state}")

    assert result.state == WorkflowExecutionState.COMPLETED, "工作流应该成功完成"

    if hasattr(result, "result") and result.result:
        if "response" in result.result:
            print(f"  输出: {result.result['response'][:200]}...")

    # 9. 打印完整结果
    print("\n" + "=" * 60)
    print("完整响应:")
    print("=" * 60)
    if hasattr(result, "result"):
        print(json.dumps(result.result, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("  工作流测试通过!")
    print("=" * 60)
    print("\n说明:")
    print("  - Start 组件: 正常工作")
    print("  - LLMChain 组件: 正常工作（使用实际 SiliconFlow 模型）")
    print("  - FlowCard 组件: 正常工作（已迁移）")
    print("  - End 组件: 正常工作")
    print("  - 工作流连接: 正常工作")
    print("=" * 60)


def print_ir_reference():
    """显示 card1.json 参考"""
    try:
        with open(
            r"E:\backend\openjiuwen_studio\extensions\card1.json", "r", encoding="utf-8"
        ) as f:
            ir_data = json.load(f)

        print("\n" + "=" * 60)
        print("card1.json 参考结构")
        print("=" * 60)
        print(f"工作流: {ir_data.get('workflowName')}")
        print(f"描述: {ir_data.get('description')}")
        print(f"\n组件 ({len(ir_data.get('components', []))}):")
        for comp in ir_data.get("components", []):
            print(f"  - {comp.get('name')} ({comp.get('type')})")
        print(f"\n连接 ({len(ir_data.get('connections', []))}):")
        for conn in ir_data.get("connections", []):
            src = conn.get("source", {}).get("componentId", "")
            tgt = conn.get("target", {}).get("componentId", "")
            print(f"  {src} -> {tgt}")
        print("=" * 60)

    except Exception as e:
        print(f"读取 card1.json 失败: {e}")


# 添加 pytest 夹具用于加载环境变量
@pytest.fixture(scope="session", autouse=True)
def load_environment():
    """加载测试环境变量"""
    env_file = r"E:\backend\openjiuwen_studio\extensions\memory_env"
    load_env_from_file(env_file)


if __name__ == "__main__":
    # 使用 pytest 运行测试
    import subprocess

    # 先打印 IR 参考
    print_ir_reference()

    # 运行测试
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    if result.returncode == 0:
        print("\n  迁移验证成功完成!")
    else:
        print(f"\nTests failed with return code: {result.returncode}")
        sys.exit(result.returncode)
