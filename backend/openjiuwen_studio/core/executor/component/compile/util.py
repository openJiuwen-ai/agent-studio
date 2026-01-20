from typing import List

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.dsl import Connection
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException
from openjiuwen_studio.core.common.status_code import StatusCode


def get_targets(node_id: str, branch_id: str, workflow_connections: List[Connection]) -> List[str]:
    # 首先检查node_id是否存在于任何连接中
    node_exists = False
    for conn in workflow_connections:
        if conn.source == node_id or conn.target == node_id:
            node_exists = True
            break
    # 如果node_id在连接中完全不存在，直接返回空列表
    results = []
    if node_exists:
        for conn in workflow_connections:
            if not (conn.branch_id and conn.source == node_id and conn.branch_id == branch_id):
                continue
            results.append(conn.target)
        if len(results) == 0:
            logger.error(f"The branches in component id: {node_id} branchid: {branch_id} is empty, please check!")
            raise JiuWenExecuteException(
                StatusCode.COMPONENT_COMPILE_ERROR.code,
                StatusCode.COMPONENT_COMPILE_ERROR.errmsg.format(
                    msg=f"node [{node_id}] branch [{branch_id}] is empty, please check!"),
                node_id=node_id
            )
    return results
