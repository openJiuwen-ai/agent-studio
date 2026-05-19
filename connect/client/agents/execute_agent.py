import json as _json
import uuid as _uuid
from typing import Dict, Any, List, Tuple

from openjiuwen.core.common.logging import logger


def execute_agent(client, agent_id: str, message: str, conversation_id: str = '') -> Tuple[List[Dict[str, Any]], str]:
    """Execute an agent and collect all SSE events.

    Returns:
        (events, conversation_id) — conversation_id is generated if not supplied,
        and should be passed back on subsequent calls to maintain context.
    """
    if not conversation_id:
        conversation_id = str(_uuid.uuid4())

    url = client.get_url('/execution/agent')
    payload = {
        'id': agent_id,
        'space_id': client.space_id or '',
        'inputs': {'query': message, 'conversation_id': conversation_id},
        'version': '',
        'conversation_id': conversation_id,
    }
    events = []
    with client.session.post(url, json=payload, stream=True, timeout=120) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode('utf-8') if isinstance(raw_line, bytes) else raw_line
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        events.append(_json.loads(data_str))
                    except _json.JSONDecodeError as exc:
                        logger.debug("Skipping non-JSON SSE line in agent stream: %s", exc)
    return events, conversation_id
