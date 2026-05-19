"""
Response formatters — convert raw API dicts into human-readable strings.
No MCP or OJ client dependency; pure data transformation.
"""
from typing import Dict, Any


def format_workflows(data: Dict[str, Any]) -> str:
    """Format a list_workflows / search_workflows API response."""
    inner = data.get('data', {})
    items = inner.get('workflow_list', inner.get('list', []))
    total = inner.get('total', len(items))
    if not items:
        return "No workflows found."
    lines = [f"Found {total} workflow(s):\n"]
    for wf in items:
        wf_id = wf.get('id', wf.get('workflow_id', 'unknown'))
        name = wf.get('name', '(unnamed)')
        desc = wf.get('description', wf.get('desc', '')).strip()
        line = f"  • [{wf_id}] {name}"
        if desc:
            line += f"\n      {desc}"
        lines.append(line)
    return "\n".join(lines)


def format_workflow_detail(data: Dict[str, Any]) -> str:
    """Format a single workflow's full definition (name, description, input params)."""
    # Extract workflow from nested structure: data.data.workflow
    wf = data.get('data', {}).get('workflow', data.get('data', data))
    name = wf.get('name', '(unnamed)')
    desc = wf.get('description', wf.get('desc', '')).strip()
    wf_id = wf.get('id', wf.get('workflow_id', 'unknown'))

    lines = [f"Workflow: {name}  (ID: {wf_id})"]
    if desc:
        lines.append(f"Description: {desc}")

    input_params = wf.get('input_parameters', [])
    if input_params:
        lines.append("\nInput parameters:")
        for param in input_params:
            pname = param.get('name', '?')
            ptype = param.get('type', 'string')
            required = param.get('required', param.get('is_required', False))
            pdesc = param.get('description', param.get('desc', '')).strip()
            req_label = " (required)" if required else " (optional)"
            line = f"  • {pname}: {ptype}{req_label}"
            if pdesc:
                line += f" — {pdesc}"
            lines.append(line)
    else:
        lines.append("\nNo input parameters.")

    return "\n".join(lines)
