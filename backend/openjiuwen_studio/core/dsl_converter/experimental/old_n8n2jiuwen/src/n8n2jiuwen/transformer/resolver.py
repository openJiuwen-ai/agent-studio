"""Resolver module for n8n workflow graph resolution using topological sorting."""

from typing import Dict, List, Set
from ..parser import WorkflowData, Node
from enum import Enum


class CycleDetectedError(Exception):
    """Exception raised when a circular dependency is detected in the workflow."""
    pass


def resolve_graph(workflow: WorkflowData) -> List[Node]:
    """
    Resolves the execution order of nodes in the workflow using topological sorting.

    Args:
        workflow: The parsed workflow data

    Returns:
        A list of nodes in execution order

    Raises:
        CycleDetectedError: If a circular dependency is detected
    """
    # Build adjacency list representing the graph
    graph: Dict[str, List[str]] = {}
    all_nodes: Dict[str, Node] = {node.name: node for node in workflow.nodes}

    # Initialize graph with all nodes
    for node_name in all_nodes:
        graph[node_name] = []

    # Build the graph based on connections
    # Connections format: {source_node: {input_type: [[{connection_obj}, ...], ...]}}
    for source_node_name, connections_by_input_type in workflow.connections.items():
        if source_node_name in graph:
            for input_type, connection_lists in connections_by_input_type.items():
                # connection_lists is a list of lists of connection objects
                for connection_list in connection_lists:
                    # connection_list is a list of connection objects
                    for connection in connection_list:
                        # connection is a dict like {'node': 'target_name', 'type': 'main', 'index': 0}
                        target_node_name = connection.get('node')
                        if target_node_name and target_node_name in graph:
                            graph[source_node_name].append(target_node_name)

    # Perform topological sort
    visited: Set[str] = set()
    temp_visited: Set[str] = set()
    order: List[Node] = []

    def dfs(node_name: str):
        if node_name in temp_visited:
            raise CycleDetectedError(f"Circular dependency detected involving node: {node_name}")

        if node_name not in visited:
            temp_visited.add(node_name)

            # Visit all neighbors
            for neighbor in graph.get(node_name, []):
                dfs(neighbor)

            temp_visited.remove(node_name)
            visited.add(node_name)
            order.append(all_nodes[node_name])

    # Visit all unvisited nodes
    for node_name in all_nodes:
        if node_name not in visited:
            dfs(node_name)

    # Reverse the order to get the correct execution sequence
    order.reverse()

    return order