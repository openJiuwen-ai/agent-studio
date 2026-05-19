"""
CLI launcher — interact with OpenJiuwen workflows and agents from the terminal.

Usage:
    python -m connect.adapters.channels.run cli <command> [args...]

Commands:
    login                         Log in to the backend
    logout                        Log out
    status                        Show login status
    health                        Check backend health

    workflow list                 List all workflows
      [--page N] [--page-size N]  Optional pagination parameters
    workflow search <keyword>     Search workflows
    workflow execute <id>         Execute a workflow
      [--input KEY=VALUE ...]     Provide input parameters
    workflow skip                 Skip optional workflow parameter
    workflow cancel               Cancel workflow execution
    workflow demo1                Demo 1 Runner
    workflow demo2                Demo 2 Runner

    agent list                    List all agents
      [--page N] [--page-size N]  Optional pagination parameters
    agent search <keyword>        Search agents
    agent execute <id> <message>  Send a single message to an agent
    agent chat <id>               Start an interactive chat session
"""
import argparse
import os
from pathlib import Path

# Set token storage path before any token_storage_file import.
os.environ.setdefault('OJ_TOKEN_STORAGE', str(Path(__file__).parent / '.cli_tokens.json'))

from openjiuwen.core.common.logging import logger

from .commands import (
    cmd_login, cmd_logout, cmd_status, cmd_health,
    cmd_workflow_list, cmd_workflow_search, cmd_workflow_run, cmd_demo1, cmd_demo2,
    cmd_agent_list, cmd_agent_search, cmd_agent_run, cmd_agent_chat,
)


# ── Argument parser ─────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="connect.adapters.channels.run cli",
        description="Interact with OpenJiuwen workflows and agents from the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--backend-url",
        default=os.getenv("BACKEND_URL", "http://localhost:8000"),
        metavar="URL",
        help="Backend URL (default: http://localhost:8000, env: BACKEND_URL)",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ── Auth ────────────────────────────────────────────────────────────────
    sub.add_parser("login", help="Log in to the backend")
    sub.add_parser("logout", help="Log out")
    sub.add_parser("status", help="Show login status")
    sub.add_parser("health", help="Check backend health")

    # ── Workflow ─────────────────────────────────────────────────────────────
    wf = sub.add_parser("workflow", help="Workflow commands")
    wf_sub = wf.add_subparsers(dest="workflow_cmd", metavar="<subcommand>")
    wf_sub.required = True

    wf_list = wf_sub.add_parser("list", help="List all workflows")
    wf_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    wf_list.add_argument("--page-size", type=int, default=20, help="Number of items per page (default: 20)")

    wf_search = wf_sub.add_parser("search", help="Search workflows")
    wf_search.add_argument("keyword", help="Search keyword")

    wf_run = wf_sub.add_parser("execute", help="Execute a workflow")
    wf_run.add_argument("workflow_id", help="Workflow ID to execute")
    wf_run.add_argument(
        "--input", "-i",
        action="append",
        metavar="KEY=VALUE",
        dest="inputs",
        help="Input parameter (repeatable: -i key1=val1 -i key2=val2)",
    )

    wf_sub.add_parser("skip", help="Skip optional workflow parameter")
    wf_sub.add_parser("cancel", help="Cancel workflow execution")
    wf_sub.add_parser("demo1", help="Demo 1 Runner")
    wf_sub.add_parser("demo2", help="Demo 2 Runner")

    # ── Agent ────────────────────────────────────────────────────────────────
    ag = sub.add_parser("agent", help="Agent commands")
    ag_sub = ag.add_subparsers(dest="agent_cmd", metavar="<subcommand>")
    ag_sub.required = True

    ag_list = ag_sub.add_parser("list", help="List all agents")
    ag_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    ag_list.add_argument("--page-size", type=int, default=20, help="Number of items per page (default: 20)")

    ag_search = ag_sub.add_parser("search", help="Search agents")
    ag_search.add_argument("keyword", help="Search keyword")

    ag_run = ag_sub.add_parser("execute", help="Send a single message to an agent")
    ag_run.add_argument("agent_id", help="Agent ID")
    ag_run.add_argument("message", nargs="+", help="Message to send")

    ag_chat = ag_sub.add_parser("chat", help="Start interactive chat session with an agent")
    ag_chat.add_argument("agent_id", help="Agent ID")

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    url = args.backend_url

    try:
        _dispatch(args, url)
    except Exception as e:
        logger.error(f"❌ {e}")


def _dispatch(args, url: str) -> None:
    if args.command == "login":
        cmd_login(url)
    elif args.command == "logout":
        cmd_logout()
    elif args.command == "status":
        cmd_status(url)
    elif args.command == "health":
        cmd_health(url)

    elif args.command == "workflow":
        if args.workflow_cmd == "list":
            cmd_workflow_list(url, args.page, args.page_size)
        elif args.workflow_cmd == "search":
            cmd_workflow_search(url, args.keyword)
        elif args.workflow_cmd == "execute":
            cmd_workflow_run(url, args.workflow_id, args.inputs)
        elif args.workflow_cmd == "skip":
            logger.info("Use 'workflow execute <id>' to start a workflow, then reply to skip optional parameters.")
        elif args.workflow_cmd == "cancel":
            logger.info("Workflow cancel is handled interactively. Press Ctrl+C to abort a running workflow.")
        elif args.workflow_cmd == "demo1":
            cmd_demo1(url)
        elif args.workflow_cmd == "demo2":
            cmd_demo2(url)

    elif args.command == "agent":
        if args.agent_cmd == "list":
            cmd_agent_list(url, args.page, args.page_size)
        elif args.agent_cmd == "search":
            cmd_agent_search(url, args.keyword)
        elif args.agent_cmd == "execute":
            cmd_agent_run(url, args.agent_id, ' '.join(args.message))
        elif args.agent_cmd == "chat":
            cmd_agent_chat(url, args.agent_id)
