"""Workflow list command."""
from openjiuwen.core.common.logging import logger
from connect.client.workflows import list_workflows
from ...session import require_client
from ...output import print_workflows


def cmd_workflow_list(backend_url: str, page: int = 1, page_size: int = 20) -> None:
    client = require_client(backend_url)
    try:
        result = list_workflows(client, page=page, page_size=page_size)
        workflows = result.get('data', {}).get('workflow_list', [])
        total = result.get('data', {}).get('total', len(workflows))
        if not workflows:
            logger.info("ℹ️  No workflows found.")
            return
        print_workflows(workflows, total)
    except Exception as e:
        error = f"❌ {e}"
        logger.error(error)
        raise RuntimeError(error) from e

