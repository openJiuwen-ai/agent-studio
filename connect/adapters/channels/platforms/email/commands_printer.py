"""Prints available commands to stdout on startup."""

from openjiuwen.core.common.logging import logger


def print_bot_commands() -> None:
    logger.info("""
  Email Bot Commands
  ------------------
  Auth:      login | logout | status | cancel
  Workflows: workflows | workflows search <q> | workflow execute <id>
             workflow skip | workflow cancel
  Agents:    agents | agents search <q> | agent execute <id> <msg>
             agent chat <id>
  General:   help | health
    """.strip())
