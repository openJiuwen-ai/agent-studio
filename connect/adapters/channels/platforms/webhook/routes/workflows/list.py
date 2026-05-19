"""List workflows endpoint."""
from connect.client import OpenJiuwenClient
from connect.client.workflows import list_workflows
from ...auth import client_dep


def workflow_list(page: int = 1, page_size: int = 20, client: OpenJiuwenClient = client_dep):
    try:
        result = list_workflows(client, page=page, page_size=page_size)
        return {"success": True, "data": result.get("data", {}), "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}
