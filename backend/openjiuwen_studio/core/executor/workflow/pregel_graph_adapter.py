import json
from typing import Any, Dict, List, Tuple

import networkx as nx
from openjiuwen_studio.core.common.exceptions import BaseError
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.dsl import BaseFlow, Connection, Component, ComponentType
from openjiuwen_studio.core.common.exceptions import JiuWenExecuteException, JiuWenComponentException
from openjiuwen_studio.core.common.status_code import StatusCode

EMPTY_NODE_ID_PREFIX = 'empty_node_'


class JiuWenGraphException(BaseError):
    """workflow图异常"""


class PregelGraphAdapter():
    def __init__(self, workflow: BaseFlow) -> None:
        self._workflow: BaseFlow = workflow
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._pending_nodes: List[str] = []
        for component in self._workflow.components:
            self._graph.add_node(component.id, type=component.type)
        for connection in self._workflow.connections:
            self._graph.add_edge(connection.source, connection.target, visited=False, branch_id=connection.branch_id)

    # cba for closest branch ancestor
    @staticmethod
    def _add_cba_map(cba_map: Dict[str, Dict[str, Any]], d: Dict[str, Any]) -> None:
        cba = d.get('cba', False)
        if cba:
            if cba_map.get(cba):
                cba_map[cba]['cur_branches'] += d['cur_branches']
            else:
                cba_map[cba] = {'cur_branches': d['cur_branches'], "total_branches": d['total_branches']}

    # 拥有相同cba的边，如果全部都已汇合，进行消减
    def _reduce_cba_map(self, cba_map: Dict[str, Dict[str, Any]]) -> None:
        need_reduce = True
        while need_reduce:
            need_reduce = False
            for k, v in list(cba_map.items()):
                if v['cur_branches'] == v['total_branches']:
                    cba_map.pop(k)
                    d = self._graph.nodes.data()[k]
                    PregelGraphAdapter._add_cba_map(cba_map, d)
                    need_reduce = True

    # 计算多个branch list的笛卡尔积
    @staticmethod
    def _cartesian_product(lists: List[List[str]]) -> List[List[str]]:
        result = [[]]
        for one in lists:
            result = [x + [y] for x in result for y in one]
        return result

    def _is_switch_like_component(self, node: str) -> bool:
        if self._graph.nodes[node]['type'] in [ComponentType.COMPONENT_TYPE_IF, ComponentType.COMPONENT_TYPE_INTENT,
                                               ComponentType.COMPONENT_TYPE_CODE]:
            return True
        else:
            return False

    def _is_ancestor_descendant(self, node1: str, node2: str) -> bool:
        """检查node1是否是node2的祖先节点"""
        try:
            # 检查从node1到node2是否存在路径
            return nx.has_path(self._graph, node1, node2)
        except:
            return False

    def _merge_ancestor_descendant_in_branch_parents(self, branch_parents: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """合并branch_parents中的祖先-子孙关系：将子孙的value合并进祖先的value中，删除子孙的key"""
        logger.debug(f"[MERGE_ANCESTOR_DESCENDANT] Initial branch_parents: {branch_parents}")

        merged = True
        while merged:
            merged = False
            keys = list(branch_parents.keys())
            logger.debug(f"[MERGE_ANCESTOR_DESCENDANT] Checking keys: {keys}")

            for i in range(len(keys)):
                for j in range(len(keys)):
                    if i == j:
                        continue

                    ancestor_candidate = keys[i]
                    descendant_candidate = keys[j]

                    # 检查是否是祖先-子孙关系
                    if self._is_ancestor_descendant(ancestor_candidate, descendant_candidate):
                        logger.debug(
                            f"[MERGE_ANCESTOR_DESCENDANT] Found ancestor-descendant relationship: {ancestor_candidate} -> {descendant_candidate}")
                        # 将子孙的value合并进祖先的value中
                        if descendant_candidate in branch_parents:
                            # 合并去重
                            old_values = branch_parents[ancestor_candidate].copy()
                            to_merge = branch_parents[descendant_candidate].copy()
                            branch_parents[ancestor_candidate] = list(
                                set(branch_parents[ancestor_candidate] + branch_parents[descendant_candidate])
                            )
                            # 删除子孙的key
                            del branch_parents[descendant_candidate]
                            logger.debug(
                                f"[MERGE_ANCESTOR_DESCENDANT] Merged: ancestor={ancestor_candidate}, old={old_values}, merged={to_merge}, result={branch_parents[ancestor_candidate]}")
                            merged = True
                            break

                if merged:
                    break

        logger.debug(f"[MERGE_ANCESTOR_DESCENDANT] Final branch_parents: {branch_parents}")
        return branch_parents

    # 节点入度大于1，需要计算依赖：所有普通入边+[branch入边的组合]
    def _multiple_dependency(self, node: str) -> None:
        normal_parents: List[str] = []
        branch_parents: Dict[str, List[str]] = {}
        for u, v, d in self._graph.in_edges(node, data=True):
            if d.get('cba', False):
                cba = d.get('cba')
                if self._is_switch_like_component(cba):
                    if branch_parents.get(cba):
                        branch_parents[cba].append(u)
                    else:
                        branch_parents[cba] = [u]
                else:
                    normal_parents.append(u)

        # 校验branch_parents，合并祖先-子孙关系（仅当size > 1时）
        if len(branch_parents) > 1:
            branch_parents = self._merge_ancestor_descendant_in_branch_parents(branch_parents)

        cartesian_results = PregelGraphAdapter._cartesian_product(list(branch_parents.values()))
        for cartesian_result in cartesian_results:
            self._workflow.connections.append(
                Connection(source=normal_parents + cartesian_result, target=node, branch_id=None))

    def _single_dependency(self, node: str) -> None:
        for u, v, d in self._graph.in_edges(node, data=True):
            self._workflow.connections.append(Connection(source=u, target=v, branch_id=d.get('branch_id', "")))

    # 重新计算节点的connection
    def _rebuild_connections(self, node: str) -> None:
        if len(self._graph.in_edges(node)) <= 1:
            self._single_dependency(node)
        else:
            self._multiple_dependency(node)

    # 如果节点的入边至少有一条携带cba信息，需要进行cba消减，并计算节点的cba信息
    def _cba_reduce(self, node: str) -> None:
        cba_map: Dict[str, Dict[str, Any]] = {}
        in_edges: List[str] = []
        for u, v, d in self._graph.in_edges(node, data=True):
            PregelGraphAdapter._add_cba_map(cba_map, d)
            in_edges.append(f'{u}-{v}')
        self._reduce_cba_map(cba_map)
        if len(cba_map) > 1:
            raise JiuWenExecuteException(code=StatusCode.WORKFLOW_GRAPH_BRANCH_REDUCE_ERROR.code,
                                         message=StatusCode.WORKFLOW_GRAPH_BRANCH_REDUCE_ERROR.errmsg, node_id=node, )
        elif len(cba_map) == 1:
            (k, v) = cba_map.popitem()
            self._graph.nodes[node]['cba'] = k
            self._graph.nodes[node]['total_branches'] = v['total_branches']
            self._graph.nodes[node]['cur_branches'] = v['cur_branches']
            logger.debug(f'node-{node}: data:{self._graph.nodes[node]}')

    # 校验break/continue节点是否存在未汇合普通分支（非Switch分支）
    def _check_loop_control_node(self, node: str) -> None:
        if not self._is_loop_control_node(node):
            return
        cba = self._graph.nodes[node].get('cba', False)
        while cba:
            if not self._is_switch_like_component(cba):
                raise JiuWenGraphException(code=StatusCode.WORKFLOW_GRAPH_LOOP_CONTROL_NODE_REDUCE_ERROR.code,
                                           message=StatusCode.WORKFLOW_GRAPH_LOOP_CONTROL_NODE_REDUCE_ERROR.errmsg.format(
                                               msg=node))
            cba = self._graph.nodes[cba].get('cba', False)

    def _travel_in_edges(self, node: str) -> bool:
        self._cba_reduce(node)
        self._check_loop_control_node(node)
        self._rebuild_connections(node)
        return True

    # 分支起始节点，为出边增加cba信息
    def _split_branch(self, node: str) -> None:
        for u, v, d in self._graph.out_edges(node, data=True):
            d['cba'] = node
            d['total_branches'] = len(self._graph.out_edges(node))
            d['cur_branches'] = 1
            logger.debug(f'edge{u}-{v}: data:{d}')

    # 如果节点存在cba信息，并且出度为1，则对出边透传cba信息
    def _passthrough_branch(self, node: str) -> None:
        if self._graph.nodes[node].get('cba', False):
            for u, v, d in self._graph.out_edges(node, data=True):
                d['cba'] = self._graph.nodes[node]['cba']
                d['total_branches'] = self._graph.nodes[node]['total_branches']
                d['cur_branches'] = self._graph.nodes[node]['cur_branches']

    # 遍历所有出边
    def _travel_out_edges(self, node: str) -> None:
        for u, v, d in self._graph.out_edges(node, data=True):
            d['visited'] = True
        if len(self._graph.out_edges(node)) > 1:
            self._split_branch(node)
        elif len(self._graph.out_edges(node)) == 1:
            self._passthrough_branch(node)
        else:
            pass

    def _travel_one_node(self, node: str) -> bool:
        in_edges = self._graph.in_edges(node, data=True)
        for u, v, d in in_edges:
            if not d['visited']:
                return False

        self._travel_in_edges(node)
        self._travel_out_edges(node)
        return True

    # 遍历节点时，如果入边还未遍历，加入pending_nodes，最后重新遍历
    def _travel_pending_nodes(self) -> None:
        while self._pending_nodes:
            i = len(self._pending_nodes) - 1
            while i >= 0:
                if self._travel_one_node(node=self._pending_nodes[i]):
                    del self._pending_nodes[i]
                i -= 1

    def _travel_all_nodes(self) -> None:
        self._pending_nodes.clear()
        for cur_node in self._graph.nodes():
            if not self._travel_one_node(cur_node):
                self._pending_nodes.append(cur_node)
        self._travel_pending_nodes()

    # 整个图校验，是否存在环
    def _validate_graph(self) -> None:
        # 先校验孤立起始节点
        self._validate_isolated_source_nodes()
        self._validate_connectivity()  # 检查连通性
        # 再校验是否存在环
        cycles: List[List[str]] = list(nx.simple_cycles(self._graph))
        if cycles:
            raise JiuWenGraphException(code=StatusCode.WORKFLOW_GRAPH_CIRCLE_ERROR.code,
                                       message=StatusCode.WORKFLOW_GRAPH_CIRCLE_ERROR.errmsg.format(
                                           msg=json.dumps(cycles)))

    # 校验：出度大于0且入度为0的节点必须是start节点
    def _validate_isolated_source_nodes(self) -> None:
        """校验图中孤立起始节点的类型

        如果一个节点的出度大于0且入度等于0（即孤立起始节点），
        那么这个节点的类型必须是 COMPONENT_TYPE_START

        注意：循环体内部的空开始节点（如 block_start_*）会被排除在校验之外

        Raises:
            JiuWenGraphException: 如果存在非start类型的孤立起始节点
        """
        for node in self._graph.nodes():
            # 跳过循环体内部的开始节点
            if node.startswith('block_start_'):
                continue

            out_degree = self._graph.out_degree(node)
            in_degree = self._graph.in_degree(node)

            # 出度大于0且入度为0的节点必须是start节点
            if out_degree > 0 and in_degree == 0:
                node_type = self._graph.nodes[node]['type']
                if node_type != ComponentType.COMPONENT_TYPE_START:
                    raise JiuWenComponentException(
                        code=StatusCode.WORKFLOW_GRAPH_START_NODE_ERROR.code,
                        message=StatusCode.WORKFLOW_GRAPH_START_NODE_ERROR.errmsg,
                        component_id=node,
                        component_type=node_type
                    )

    def _is_loop_control_node(self, node: str) -> bool:
        if self._graph.nodes[node]['type'] in [ComponentType.COMPONENT_TYPE_CONTINUE,
                                               ComponentType.COMPONENT_TYPE_BREAK]:
            return True
        else:
            return False

    # 对图进行预处理 为分支节点增加空的子节点 为break/continue连接到end
    def _pre_process_graph(self) -> None:
        edges_to_add: List[Tuple[str, str, Any]] = []
        edges_to_remove: List[Tuple[str, str]] = []
        nodes_to_add: List[str] = []
        for cur_node in self._graph.nodes():
            if self._is_loop_control_node(cur_node):
                self._graph.add_edge(cur_node, self._workflow.end_id[0], visited=False)
                continue
            if not self._is_switch_like_component(cur_node):
                continue
            for u, v, d in self._graph.out_edges(cur_node, data=True):
                branch_id = d['branch_id']
                empty_node = f'{EMPTY_NODE_ID_PREFIX}{u}_{branch_id}_{v}'
                nodes_to_add.append(empty_node)
                edges_to_add.append((u, empty_node, branch_id))
                edges_to_add.append((empty_node, v, None))
                edges_to_remove.append((u, v))

        for node in nodes_to_add:
            self._graph.add_node(node, type=ComponentType.COMPONENT_TYPE_EMPTY)
            self._workflow.components.append(Component(type=ComponentType.COMPONENT_TYPE_EMPTY, id=node))
        for edge in edges_to_remove:
            self._graph.remove_edge(edge[0], edge[1])
        for edge in edges_to_add:
            self._graph.add_edge(edge[0], edge[1], visited=False, branch_id=edge[2])

    def _dfx(self) -> None:
        for component in self._workflow.components:
            logger.info(f'component: {component.id} type: {component.type}')
        for connection in self._workflow.connections:
            logger.info(f'connection: {connection.source}-{connection.target} branch_id: {connection.branch_id}')

    def _validate_connectivity(self) -> None:
        """验证从开始节点到结束节点的连通性
        """
        # 获取开始节点和结束节点
        start_id = self._workflow.start_id[0]
        end_id = self._workflow.end_id[0]
        # 检查从开始节点是否能到达结束节点
        # 使用 networkx 检查是否存在从 start_id 到 end_id 的路径
        if not nx.has_path(self._graph, start_id, end_id):
            error_msg = f"开始节点: {start_id}, 结束节点: {end_id}"
            raise JiuWenGraphException(
                code=StatusCode.WORKFLOW_GRAPH_CONNECTIVITY_ERROR.code,
                message=StatusCode.WORKFLOW_GRAPH_CONNECTIVITY_ERROR.errmsg.format(msg=error_msg)
            )
        logger.debug(
            f"[VALIDATE_CONNECTIVITY] Connectivity check passed - "
            f"Start node: {start_id}, End node: {end_id}.")

    def convert(self) -> BaseFlow:
        """将用户定义的workflow图转换为适配pregel算法的workflow图

        Args:

        Returns:
            BaseFlow: 转换后的workflow

        Raises:
            JiuWenGraphCircleError: 如果图中存在环
            JiuWenGraphBranchReduceError: 如果拥有不同祖先的分支在同一节点汇合时，消减后有多于1个祖先
            JiuWenGraphException: 如果从开始节点无法到达结束节点

        """
        self._workflow.connections = []
        self._pre_process_graph()
        self._validate_graph()  # 再检查环
        self._travel_all_nodes()
        self._dfx()
        return self._workflow
