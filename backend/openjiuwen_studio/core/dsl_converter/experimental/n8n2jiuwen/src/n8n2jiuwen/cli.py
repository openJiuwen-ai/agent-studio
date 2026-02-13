"""Command-line interface for n8n2jiuwen transpiler."""

import typer
from pathlib import Path
import json

from .parser.parser import parse_workflow
from .transformer.resolver import resolve_graph
from .mapper.base import generate_python_code

app = typer.Typer(help="n8n2jiuwen: Transpile n8n workflows to Python code")


@app.command()
def transpile(
    workflow: Path = typer.Option(..., "--workflow", "-w", help="Path to n8n workflow JSON file"),
    credentials: Path = typer.Option(None, "--credentials", "-c", help="Path to credentials file"),
    target: Path = typer.Option(..., "--target", "-t", help="Output file for generated Python code"),
    report: bool = typer.Option(False, "--report", "-r", help="Generate detailed report"),
):
    """Transpile n8n workflow JSON to Python code."""
    typer.echo(f"Transpiling workflow from {workflow}")
    
    # Read the workflow JSON
    with open(workflow, 'r') as f:
        workflow_data = json.load(f)
    
    # Parse the workflow
    parsed_workflow = parse_workflow(workflow_data)
    
    # Resolve the execution graph
    resolved_graph = resolve_graph(parsed_workflow)
    
    # Generate Python code
    python_code = generate_python_code(resolved_graph)
    
    # Write the generated code to target file
    with open(target, 'w') as f:
        f.write(python_code)
    
    typer.echo(f"Generated Python code written to {target}")
    
    if report:
        typer.echo("Report generation would go here...")


if __name__ == "__main__":
    app()