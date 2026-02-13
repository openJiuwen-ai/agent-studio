"""
Test for the n8n2jiuwen transpiler.
"""
import json
from n8n2jiuwen.parser import parse_workflow
from n8n2jiuwen.resolver import resolve_graph
from n8n2jiuwen.mapper.base import generate_python_code


def test_transpile_process():
    # Load sample workflow
    with open('sample_workflow.json', 'r') as f:
        workflow_data = json.load(f)
    
    # Parse the workflow
    parsed_workflow = parse_workflow(workflow_data)
    print(f"Parsed workflow with {len(parsed_workflow.nodes)} nodes")
    
    # Resolve the execution graph
    resolved_graph = resolve_graph(parsed_workflow)
    print(f"Resolved execution order for {len(resolved_graph)} nodes")
    
    # Generate Python code
    python_code = generate_python_code(resolved_graph)
    
    # Write the generated code to a file
    with open('generated_workflow.py', 'w') as f:
        f.write(python_code)
    
    print("Generated Python code written to generated_workflow.py")
    print("\nFirst 500 characters of generated code:")
    print(python_code[:500] + "..." if len(python_code) > 500 else python_code)


if __name__ == "__main__":
    test_transpile_process()