"""
Unit tests for connect/mcp_server/tools/*.

Each tool function is tested in isolation: the underlying channels.client calls
are mocked so no live backend is required.

Run with:
    pytest connect/adapters/mcp_server/tests/          # from project root
    pytest connect/adapters/mcp_server/tests/ -v       # verbose output
"""
from unittest.mock import MagicMock, patch

import pytest

from connect.adapters.mcp_server.tools.agents._formatters import format_agents, format_agent_detail
from connect.adapters.mcp_server.tools.workflows._formatters import format_workflows, format_workflow_detail
from connect.adapters.mcp_server.tools.general.health import health_check_tool
from connect.adapters.mcp_server.tools.agents.list_agents import list_agents_tool
from connect.adapters.mcp_server.tools.agents.search_agents import search_agents_tool
from connect.adapters.mcp_server.tools.agents.get_agent import get_agent_tool
from connect.adapters.mcp_server.tools.agents.run_agent import run_agent_tool
from connect.adapters.mcp_server.tools.agents.reset_agent import reset_agent_tool
from connect.adapters.mcp_server.tools.workflows.list_workflows import list_workflows_tool
from connect.adapters.mcp_server.tools.workflows.search_workflows import search_workflows_tool
from connect.adapters.mcp_server.tools.workflows.get_workflow import get_workflow_tool
from connect.adapters.mcp_server.tools.workflows.run_workflow import run_workflow_tool


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return MagicMock()


# ── Sample data ───────────────────────────────────────────────────────────────

AGENTS_RESPONSE = {
    'data': {
        'agent_items': [
            {'agent_id': 'agent-1', 'agent_name': 'Support Bot', 'description': 'Handles support queries'},
            {'agent_id': 'agent-2', 'agent_name': 'Sales Bot', 'desc': 'Closes deals'},
        ],
        'pagination': {'total': 2, 'page': 1, 'page_size': 10, 'total_pages': 1},
    }
}

WORKFLOWS_RESPONSE = {
    'data': {
        'workflow_list': [
            {'id': 'wf-1', 'name': 'Onboarding', 'description': 'New user flow'},
            {'id': 'wf-2', 'name': 'Invoice', 'desc': 'Generate invoice'},
        ],
        'total': 2,
    }
}

WORKFLOW_DETAIL_RESPONSE = {
    'data': {
        'id': 'wf-42',
        'name': 'Data Pipeline',
        'description': 'Processes raw data',
        'input_parameters': [
            {'name': 'source', 'type': 'string', 'is_required': True, 'desc': 'Input file path'},
            {'name': 'limit', 'type': 'integer', 'required': False},
        ],
    }
}

AGENT_DETAIL_RESPONSE = {
    'data': {
        'agent_id': 'agent-99',
        'agent_name': 'Research Assistant',
        'description': 'Answers research questions',
        'model_name': 'gpt-4o',
        'tools': [
            {'name': 'web_search'},
            {'name': 'code_interpreter'},
        ],
    }
}


# ── Formatter tests ───────────────────────────────────────────────────────────

class TestFormatAgents:
    @staticmethod
    def test_normal():
        result = format_agents(AGENTS_RESPONSE)
        assert "Found 2 agent(s)" in result
        assert "agent-1" in result
        assert "Support Bot" in result
        assert "Handles support queries" in result
        assert "agent-2" in result
        assert "Sales Bot" in result

    @staticmethod
    def test_empty():
        result = format_agents({'data': {'agent_items': [], 'pagination': {'total': 0}}})
        assert result == "No agents found."

    @staticmethod
    def test_no_description():
        data = {'data': {'agent_items': [{'agent_id': 'x', 'agent_name': 'Bot'}], 'pagination': {'total': 1}}}
        result = format_agents(data)
        assert "Bot" in result
        assert "None" not in result

    @staticmethod
    def test_fallback_agent_id_field():
        # Exercises the list fallback path (older API shape)
        data = {'data': {'list': [{'agent_id': 'alt-id', 'agent_name': 'Alt'}], 'total': 1}}
        result = format_agents(data)
        assert "alt-id" in result


class TestFormatWorkflows:
    @staticmethod
    def test_normal():
        result = format_workflows(WORKFLOWS_RESPONSE)
        assert "Found 2 workflow(s)" in result
        assert "wf-1" in result
        assert "Onboarding" in result
        assert "New user flow" in result

    @staticmethod
    def test_empty():
        result = format_workflows({'data': {'workflow_list': [], 'total': 0}})
        assert result == "No workflows found."


class TestFormatWorkflowDetail:
    @staticmethod
    def test_normal():
        result = format_workflow_detail(WORKFLOW_DETAIL_RESPONSE)
        assert "Data Pipeline" in result
        assert "wf-42" in result
        assert "Processes raw data" in result
        assert "source" in result
        assert "required" in result
        assert "limit" in result
        assert "optional" in result

    @staticmethod
    def test_no_params():
        data = {'data': {'id': 'x', 'name': 'Simple', 'input_parameters': []}}
        result = format_workflow_detail(data)
        assert "No input parameters" in result

    @staticmethod
    def test_top_level_data():
        # Some API responses omit the 'data' wrapper
        data = {'id': 'y', 'name': 'Direct', 'input_parameters': []}
        result = format_workflow_detail(data)
        assert "Direct" in result

    @staticmethod
    def test_nested_workflow_object():
        # Actual backend /workflows/canvas returns data nested in 'workflow' field
        data = {
            'data': {
                'workflow': {
                    'workflow_id': 'wf-123',
                    'name': 'Test Workflow',
                    'desc': 'A test workflow',
                    'input_parameters': [
                        {'name': 'param1', 'type': 'string', 'required': True, 'description': 'First param'}
                    ]
                }
            }
        }
        result = format_workflow_detail(data)
        assert "Test Workflow" in result
        assert "wf-123" in result
        assert "A test workflow" in result
        assert "param1" in result
        assert "required" in result


class TestFormatAgentDetail:
    @staticmethod
    def test_normal():
        result = format_agent_detail(AGENT_DETAIL_RESPONSE)
        assert "Research Assistant" in result
        assert "agent-99" in result
        assert "Answers research questions" in result
        assert "gpt-4o" in result
        assert "web_search" in result
        assert "code_interpreter" in result

    @staticmethod
    def test_no_tools():
        data = {'data': {'id': 'x', 'name': 'Simple Bot', 'description': 'Does things'}}
        result = format_agent_detail(data)
        assert "Simple Bot" in result
        assert "x" in result

    @staticmethod
    def test_top_level_data():
        # Some API responses omit the 'data' wrapper
        data = {'id': 'y', 'name': 'Direct Agent'}
        result = format_agent_detail(data)
        assert "Direct Agent" in result


# ── Health check tests ────────────────────────────────────────────────────────

class TestHealthCheckTool:
    @staticmethod
    def test_success(client):
        with patch('connect.adapters.mcp_server.tools.health._health_check', return_value={'status': 'ok'}) as mock:
            result = health_check_tool(client)
        assert "healthy" in result.lower()
        assert "ok" in result
        mock.assert_called_once_with(client)

    @staticmethod
    def test_connection_error(client):
        with patch('connect.adapters.mcp_server.tools.health._health_check', side_effect=ConnectionError("refused")):
            result = health_check_tool(client)
        assert result.startswith("ERROR")
        assert "refused" in result


# ── list_agents tests ─────────────────────────────────────────────────────────

class TestListAgentsTool:
    @staticmethod
    def test_success(client):
        with patch('connect.adapters.mcp_server.tools.list_agents._list_agents', return_value=AGENTS_RESPONSE):
            result = list_agents_tool(client, page=1, page_size=10)
        assert "agent-1" in result
        assert "Support Bot" in result

    @staticmethod
    def test_passes_pagination(client):
        with patch('connect.adapters.mcp_server.tools.list_agents._list_agents', return_value=AGENTS_RESPONSE) as mock:
            list_agents_tool(client, page=3, page_size=5)
        mock.assert_called_once_with(client, page=3, page_size=5)

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.list_agents._list_agents', side_effect=RuntimeError("timeout")):
            result = list_agents_tool(client)
        assert "ERROR" in result
        assert "timeout" in result


# ── search_agents tests ───────────────────────────────────────────────────────

class TestSearchAgentsTool:
    @staticmethod
    def test_success(client):
        with (patch('connect.adapters.mcp_server.tools.search_agents._search_agents', return_value=AGENTS_RESPONSE)
              as mock):
            result = search_agents_tool(client, keyword="support")
        assert "agent-1" in result
        mock.assert_called_once_with(client, keyword="support")

    @staticmethod
    def test_no_results(client):
        empty = {'data': {'list': [], 'total': 0}}
        with patch('connect.adapters.mcp_server.tools.search_agents._search_agents', return_value=empty):
            result = search_agents_tool(client, keyword="zzz")
        assert "No agents found" in result

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.search_agents._search_agents', side_effect=Exception("500")):
            result = search_agents_tool(client, keyword="x")
        assert "ERROR" in result


# ── get_agent tests ───────────────────────────────────────────────────────────

class TestGetAgentTool:
    @staticmethod
    def test_success(client):
        with (patch('connect.adapters.mcp_server.tools.get_agent._get_agent', return_value=AGENT_DETAIL_RESPONSE)
              as mock):
            result = get_agent_tool(client, 'agent-99')
        assert "Research Assistant" in result
        assert "agent-99" in result
        mock.assert_called_once_with(client, 'agent-99')

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.get_agent._get_agent', side_effect=Exception("not found")):
            result = get_agent_tool(client, 'bad-id')
        assert "ERROR" in result
        assert "not found" in result


# ── run_agent tests ───────────────────────────────────────────────────────────

class TestRunAgentTool:
    @staticmethod
    def _mock_events():
        return [{'code': 200, 'data': {'type': 'agent', 'payload': {'result_type': 'answer', 'content': 'Hello!'}},
                 'message': 'Executed successfully'}]

    def test_success(self, client):
        events = self._mock_events()
        with patch('connect.adapters.mcp_server.tools.run_agent._execute_agent', return_value=events), \
             patch('connect.adapters.mcp_server.tools.run_agent.parse_agent_response',
                   return_value=('Hello!', 'conv-xyz', None)):
            result = run_agent_tool(client, 'agent-1', 'Hi', '')
        assert "Hello!" in result
        assert "conv-xyz" in result

    @staticmethod
    def test_conversation_id_always_present(client):
        # Even when the backend doesn't echo conversation_id, the tool generates one.
        with patch('connect.adapters.mcp_server.tools.run_agent._execute_agent', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_agent.parse_agent_response',
                   return_value=('Reply text', None, None)):
            result = run_agent_tool(client, 'agent-1', 'Hi')
        assert "Reply text" in result
        assert "Conversation ID:" in result

    @staticmethod
    def test_agent_error_event(client):
        with patch('connect.adapters.mcp_server.tools.run_agent._execute_agent', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_agent.parse_agent_response',
                   return_value=(None, None, 'rate limit')):
            result = run_agent_tool(client, 'agent-1', 'Hi')
        assert "ERROR from agent" in result
        assert "rate limit" in result

    @staticmethod
    def test_network_exception(client):
        with patch('connect.adapters.mcp_server.tools.run_agent._execute_agent', side_effect=ConnectionError("refused")):
            result = run_agent_tool(client, 'agent-1', 'Hi')
        assert "ERROR running agent" in result

    @staticmethod
    def test_no_reply_placeholder(client):
        with patch('connect.adapters.mcp_server.tools.run_agent._execute_agent', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_agent.parse_agent_response',
                   return_value=(None, 'conv-1', None)):
            result = run_agent_tool(client, 'agent-1', 'Hi')
        assert "(no reply)" in result


# ── reset_agent tests ─────────────────────────────────────────────────────────

class TestResetAgentTool:
    @staticmethod
    def test_returns_confirmation():
        result = reset_agent_tool('conv-abc')
        assert 'conv-abc' in result
        assert 'reset' in result.lower()

    @staticmethod
    def test_no_client_needed():
        # reset_agent_tool takes no client — must not raise
        result = reset_agent_tool('any-id')
        assert isinstance(result, str)


# ── list_workflows tests ──────────────────────────────────────────────────────

class TestListWorkflowsTool:
    @staticmethod
    def test_success(client):
        with patch('connect.adapters.mcp_server.tools.list_workflows._list_workflows',
                   return_value=WORKFLOWS_RESPONSE) as mock:
            result = list_workflows_tool(client, page=2, page_size=5)
        assert "Onboarding" in result
        mock.assert_called_once_with(client, page=2, page_size=5)

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.list_workflows._list_workflows',
                   side_effect=Exception("db error")):
            result = list_workflows_tool(client)
        assert "ERROR" in result


# ── search_workflows tests ────────────────────────────────────────────────────

class TestSearchWorkflowsTool:
    @staticmethod
    def test_success(client):
        with patch('connect.adapters.mcp_server.tools.search_workflows._search_workflows',
                   return_value=WORKFLOWS_RESPONSE) as mock:
            result = search_workflows_tool(client, keyword="invoice")
        assert "Invoice" in result
        mock.assert_called_once_with(client, keyword="invoice")

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.search_workflows._search_workflows',
                   side_effect=Exception("oops")):
            result = search_workflows_tool(client, keyword="x")
        assert "ERROR" in result


# ── get_workflow tests ────────────────────────────────────────────────────────

class TestGetWorkflowTool:
    @staticmethod
    def test_success(client):
        with patch('connect.adapters.mcp_server.tools.get_workflow._get_workflow',
                   return_value=WORKFLOW_DETAIL_RESPONSE) as mock:
            result = get_workflow_tool(client, 'wf-42')
        assert "Data Pipeline" in result
        assert "source" in result
        mock.assert_called_once_with(client, 'wf-42')

    @staticmethod
    def test_error(client):
        with patch('connect.adapters.mcp_server.tools.get_workflow._get_workflow', side_effect=Exception("not found")):
            result = get_workflow_tool(client, 'wf-bad')
        assert "ERROR" in result
        assert "not found" in result


# ── run_workflow tests ────────────────────────────────────────────────────────

class TestRunWorkflowTool:
    @staticmethod
    def test_single_output(client):
        events = [{}]
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow', return_value=events), \
             patch('connect.adapters.mcp_server.tools.run_workflow.parse_workflow_result',
                   return_value=({'result': '42'}, None)):
            result = run_workflow_tool(client, 'wf-1', {'x': 1})
        assert result == '42'

    @staticmethod
    def test_multiple_outputs(client):
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_workflow.parse_workflow_result',
                   return_value=({'a': 'hello', 'b': 'world'}, None)):
            result = run_workflow_tool(client, 'wf-1')
        assert "a: hello" in result
        assert "b: world" in result

    @staticmethod
    def test_empty_output(client):
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_workflow.parse_workflow_result', return_value=({}, None)):
            result = run_workflow_tool(client, 'wf-1')
        assert "no output" in result.lower()

    @staticmethod
    def test_workflow_error_event(client):
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow', return_value=[]), \
             patch('connect.adapters.mcp_server.tools.run_workflow.parse_workflow_result',
                   return_value=(None, 'step failed')):
            result = run_workflow_tool(client, 'wf-1')
        assert "ERROR from workflow" in result
        assert "step failed" in result

    @staticmethod
    def test_network_exception(client):
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow',
                   side_effect=TimeoutError("timed out")):
            result = run_workflow_tool(client, 'wf-1')
        assert "ERROR running workflow" in result

    @staticmethod
    def test_none_inputs_treated_as_empty(client):
        with patch('connect.adapters.mcp_server.tools.run_workflow._execute_workflow', return_value=[]) as mock, \
             patch('connect.adapters.mcp_server.tools.run_workflow.parse_workflow_result',
                   return_value=({'r': '1'}, None)):
            run_workflow_tool(client, 'wf-1', None)
        mock.assert_called_once_with(client, 'wf-1', {})
