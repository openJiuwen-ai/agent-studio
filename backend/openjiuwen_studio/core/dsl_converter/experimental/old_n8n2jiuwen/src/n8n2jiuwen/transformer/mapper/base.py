"""Base mapper module for translating n8n nodes to Python code."""

from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from ..parser import Node


class BaseMapper:
    """Base class for mapping n8n nodes to Python code snippets."""
    
    def __init__(self):
        # Set up Jinja2 environment
        templates_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(templates_dir)))
    
    def map_node(self, node: Node) -> str:
        """Map an n8n node to a Python code snippet based on its type."""
        node_type = node.type
        
        # Handle different node types
        if node_type.startswith('n8n-nodes-base.httpRequest'):
            return self._map_http_request(node)
        elif node_type.startswith('n8n-nodes-base.openAi'):
            return self._map_openai_chat(node)
        elif node_type.startswith('n8n-nodes-base.set'):
            return self._map_set_operation(node)
        elif node_type.startswith('n8n-nodes-base.if'):
            return self._map_if_condition(node)
        else:
            # Default handler for unknown node types
            return self._map_generic_node(node)
    
    def _map_http_request(self, node: Node) -> str:
        """Map HTTP request node to Python code."""
        params = node.parameters
        url = params.get('url', '')
        method = params.get('requestMethod', 'GET')
        
        # Extract headers if present
        headers = params.get('headerParametersUi', {}).get('parameter', [])
        headers_dict = {h['name']: h['value'] for h in headers}
        
        # Extract body if present
        body = params.get('body', '')
        
        code_template = '''
# HTTP Request Node: {{ node_name }}
import httpx

async def execute_{{ node_name_clean }}(state):
    """Execute HTTP request for node: {{ node_name }}"""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="{{ method }}",
            url="{{ url }}",
            headers={{ headers }},
            {% if body %}json={{ body | tojson }},{% endif %}
        )
        result = response.json() if response.content else {}
        
        # Store result in workflow state
        state['node_outputs']['{{ node_name }}'] = result
        return result

'''
        template = self.env.from_string(code_template)
        return template.render(
            node_name=node.name.replace(' ', '_').replace('-', '_'),
            node_name_clean=node.name.replace(' ', '_').replace('-', '_').lower(),
            method=method,
            url=url,
            headers=headers_dict,
            body=body
        )
    
    def _map_openai_chat(self, node: Node) -> str:
        """Map OpenAI chat node to Python code."""
        params = node.parameters
        model = params.get('model', 'gpt-3.5-turbo')
        prompt = params.get('options', {}).get('systemMessage', '')
        
        code_template = '''
# OpenAI Chat Node: {{ node_name }}
from openai import AsyncOpenAI

async def execute_{{ node_name_clean }}(state):
    """Execute OpenAI chat for node: {{ node_name }}"""
    client = AsyncOpenAI()
    
    response = await client.chat.completions.create(
        model="{{ model }}",
        messages=[
            {"role": "system", "content": "{{ prompt }}"},
            # Add messages from state if needed
        ]
    )
    
    result = response.choices[0].message.content
    
    # Store result in workflow state
    state['node_outputs']['{{ node_name }}'] = result
    return result

'''
        template = self.env.from_string(code_template)
        return template.render(
            node_name=node.name.replace(' ', '_').replace('-', '_'),
            node_name_clean=node.name.replace(' ', '_').replace('-', '_').lower(),
            model=model,
            prompt=prompt
        )
    
    def _map_set_operation(self, node: Node) -> str:
        """Map set operation node to Python code."""
        params = node.parameters
        values_to_set = params.get('values', {})
        
        code_template = '''
# Set Operation Node: {{ node_name }}
def execute_{{ node_name_clean }}(state):
    """Execute set operation for node: {{ node_name }}"""
    result = {}
    
    # Set values in the workflow state
    {% for key, value in values_to_set.items() %}
    result["{{ key }}"] = {{ value | tojson }}
    {% endfor %}
    
    # Store result in workflow state
    state['node_outputs']['{{ node_name }}'] = result
    return result

'''
        template = self.env.from_string(code_template)
        return template.render(
            node_name=node.name.replace(' ', '_').replace('-', '_'),
            node_name_clean=node.name.replace(' ', '_').replace('-', '_').lower(),
            values_to_set=values_to_set
        )
    
    def _map_if_condition(self, node: Node) -> str:
        """Map if condition node to Python code."""
        params = node.parameters
        conditions = params.get('conditions', [])
        
        code_template = '''
# If Condition Node: {{ node_name }}
def execute_{{ node_name_clean }}(state):
    """Execute if condition for node: {{ node_name }}"""
    result = {}
    
    # Evaluate conditions
    {% for condition in conditions %}
    if {{ condition.get('leftValue', '') }} {{ condition.get('operation', '') }} {{ condition.get('rightValue', '') }}:
        result['condition_met'] = True
        result['branch'] = '{{ condition.get('branchName', 'true') }}'
    else:
        result['condition_met'] = False
        result['branch'] = 'false'
    {% endfor %}
    
    # Store result in workflow state
    state['node_outputs']['{{ node_name }}'] = result
    return result

'''
        template = self.env.from_string(code_template)
        return template.render(
            node_name=node.name.replace(' ', '_').replace('-', '_'),
            node_name_clean=node.name.replace(' ', '_').replace('-', '_').lower(),
            conditions=conditions
        )
    
    def _map_generic_node(self, node: Node) -> str:
        """Map generic node to Python code."""
        code_template = '''
# Generic Node: {{ node_name }}
def execute_{{ node_name_clean }}(state):
    """Execute generic operation for node: {{ node_name }}"""
    # TODO: Implement logic for node type: {{ node_type }}
    result = {"node_type": "{{ node_type }}", "params": {{ params | tojson }}}
    
    # Store result in workflow state
    state['node_outputs']['{{ node_name }}'] = result
    return result

'''
        template = self.env.from_string(code_template)
        return template.render(
            node_name=node.name.replace(' ', '_').replace('-', '_'),
            node_name_clean=node.name.replace(' ', '_').replace('-', '_').lower(),
            node_type=node.type,
            params=node.parameters
        )


def generate_python_code(nodes_order: List[Node]) -> str:
    """Generate complete Python code for the workflow."""
    mapper = BaseMapper()

    # Import statements
    imports = '''"""
Generated Python code from n8n workflow.
This code represents the workflow logic transpiled from n8n JSON format.
"""

from typing import Dict, Any, TypedDict


class WorkflowState(TypedDict):
    node_outputs: Dict[str, Any]  # Keyed by Node Name
    context: Dict[str, Any]       # Equivalent to n8n's 'Global' variables

'''

    # Generate code for each node
    node_functions = []
    execution_calls = []

    for node in nodes_order:
        node_code = mapper.map_node(node)
        node_functions.append(node_code)

        # Add execution call
        node_name_clean = node.name.replace(' ', '_').replace('-', '_').lower()
        execution_calls.append(f"    await execute_{node_name_clean}(state)")

    # Combine everything
    full_code = imports
    for func in node_functions:
        full_code += func + "\n"

    full_code += "\nasync def execute_workflow(initial_state: WorkflowState) -> WorkflowState:\n"
    full_code += "    \"\"\"\n    Execute the entire workflow with the given initial state.\n    \"\"\"\n"
    full_code += "    state = initial_state.copy()\n\n"
    full_code += "    # Execute nodes in the resolved order\n"
    full_code += "\n".join(execution_calls)
    full_code += "\n\n    return state\n"

    return full_code