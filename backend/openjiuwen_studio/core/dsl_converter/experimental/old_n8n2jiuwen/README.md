# 🚀 n8n2jiuwen: Specification Document

`n8n2jiuwen` is a high-performance transpiler designed to convert visual n8n workflow JSON exports into clean, executable, and scalable Python code for modern Agent Frameworks (LangGraph, PydanticAI, or CrewAI).

> **Vision:** Break the "No-Code" ceiling. This tool allows developers to prototype logic visually in n8n and "compile" it into a production-ready Python codebase using `uv`.

---

## 1. Project Plan (The Roadmap)

* **Phase 1: Schema Ingestion:** Build strict Pydantic models to mirror n8n's complex JSON export format.
* **Phase 2: Graph Resolution:** Implement a Directed Acyclic Graph (DAG) resolver to handle node execution order and branching logic.
* **Phase 3: Logic Mapping:** Create a registry-based system to translate n8n node parameters (HTTP, LLM, Set) into Pythonic functions.
* **Phase 4: Template Injection:** Use Jinja2 to wrap the logic into the target agent framework's boilerplate.
* **Phase 5: CLI & Reporting:** Finalize the `uv`-based CLI and rich-text reporting system.

---

## 2. System Architecture

The bridge acts as a compiler: **Frontend (n8n JSON) → Intermediate Representation (Parser/Resolver) → Backend (Python Code).**

### Core Components:

1. **Parser (`parser.py`):** Validates inputs against n8n schemas.
2. **Resolver (`resolver.py`):** Sorts the graph. Because n8n is a DAG, we use **Topological Sorting** to ensure nodes execute in the correct order.
3. **Mapper (`mapper/`):** A dictionary of "translators." For every `n8n-nodes-base.xyz`, there is a corresponding Python snippet generator.
4. **Generator:** The engine that pumps the sorted logic into Jinja2 templates.

---

## 3. Project Structure

Designed for compatibility with `uv` and modularity for easy expansion.

```text
n8n2jiuwen/
├── pyproject.toml          # uv configuration & script entry points
├── README.md               # This specification
├── src/
│   └── n8n2jiuwen/
│       ├── __init__.py
│       ├── cli.py          # Entry point (Typer interface)
│       ├── parser.py       # Pydantic models for n8n JSON
│       ├── resolver.py     # Graph logic & Topological sorting
│       ├── mapper/         # Node-to-Code mapping registry
│       │   ├── __init__.py
│       │   ├── base.py     # Mapper interface
│       │   └── nodes/      # Specific node implementations (HTTP, AI, etc.)
│       └── templates/      # Jinja2 templates for target frameworks
│           └── langgraph.j2
└── tests/                  # Pytest suite for graph logic

```

---

## 4. Technical Specifications

### Input Schema (Pydantic)

The `parser.py` must handle the following core structure:

* **Nodes:** ID, Type, Parameters, Position.
* **Connections:** A mapping of outputs to inputs across different nodes.
* **Credentials:** Mapping of encrypted or named credential sets to environment variables.

### The CLI Interface

The CLI must be strictly invoked via `uv run` with the following signature:

```bash
uv run n8_bridge --workflow <path_to_json> --credentials <path_to_creds> --target <output_file> --report <yes/no>

```

### Execution Logic (The State Object)

To mimic n8n's ability to reference any previous node, the generated Python code must maintain a `GlobalWorkflowState`:

```python
class WorkflowState(TypedDict):
    node_outputs: Dict[str, Any]  # Keyed by Node Name
    context: Dict[str, Any]       # Equivalent to n8n's 'Global' variables

```

---

## 5. Node Mapping Logic

| n8n Node Type | jiuwen Equivalent | Transformation Note |
| --- | --- | --- |
| `httpRequest` | `httpx` or `requests` | Map URL, Method, and Headers to a Python function. |
| `openai.chat` | `openai` | Map prompts and model params to an LLM call. |
| `set` | `dict` assignment | Map static values or expressions to the `WorkflowState`. |
| `if` | `if/else` block | Logic gate that determines the next node in the graph. |

---

## 6. Implementation Notes for Qwen CLI

* **Error Handling:** If the resolver detects a circular dependency (not usually allowed in n8n, but possible in custom scripts), it must throw a clear `CycleDetectedError`.
* **Jinja2 Escaping:** Ensure n8n expressions like `{{ $json.id }}` are correctly converted to Python f-string or dictionary access like `state['node_outputs']['PreviousNode']['id']`.
* **Dependencies:** The generated `target` file should include a comment header listing the necessary `pip` or `uv` packages required to run it.
