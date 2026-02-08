"""Parser module for n8n workflow JSON validation using Pydantic models."""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel


class NodeParameter(BaseModel):
    """Represents parameters for an n8n node."""
    name: str
    value: Union[str, int, float, bool, Dict[str, Any], List[Any]]


class Node(BaseModel):
    """Represents an n8n node."""
    id: str
    name: str
    type: str
    position: List[int]  # [x, y] coordinates
    parameters: Dict[str, Any]
    credentials: Optional[Dict[str, str]] = None


# Define flexible types to handle n8n's complex connection structure
# Connections format: {source_node: {input_type: [[{connection_obj}, ...], ...]}}
# So it's Dict[str, Dict[str, List[List[Dict]]]]
ConnectionInfo = List[List[Dict[str, Union[str, int]]]]


class WorkflowData(BaseModel):
    """Main model for n8n workflow JSON structure."""
    name: str
    nodes: List[Node]
    connections: Dict[str, Dict[str, ConnectionInfo]]
    settings: Optional[Dict[str, Any]] = None
    staticData: Optional[Dict[str, Any]] = None


def parse_workflow(workflow_json: Dict[str, Any]) -> WorkflowData:
    """Parse and validate the n8n workflow JSON using Pydantic models."""
    return WorkflowData(**workflow_json)