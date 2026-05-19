"""CLI session management — one user per machine (OS username as ID)."""
import getpass
from typing import Optional

from openjiuwen.core.common.logging import logger
from connect.client import OpenJiuwenClient
from connect.client.auth.token_storage import (
    get_user_token,
    get_user_space_id,
    get_user_refresh_token,
    remove_user_token,
)
from connect.client.auth.token_manager import verify_and_refresh

# Use the OS username so multiple accounts on the same machine stay separate.
CLI_USER_ID: str = getpass.getuser()


def get_client(backend_url: str) -> Optional[OpenJiuwenClient]:
    """Return an authenticated OpenJiuwenClient, or None if not logged in / token expired."""
    token = get_user_token(CLI_USER_ID)
    if not token:
        return None
    client = OpenJiuwenClient(base_url=backend_url)
    client.set_token(token)
    client.set_space_id(get_user_space_id(CLI_USER_ID))
    ok, _ = verify_and_refresh(client, CLI_USER_ID, get_user_refresh_token(CLI_USER_ID))
    if not ok:
        remove_user_token(CLI_USER_ID)
        return None
    return client


def require_client(backend_url: str) -> OpenJiuwenClient:
    """Like get_client but raises RuntimeError if not authenticated."""
    client = get_client(backend_url)
    if client is None:
        raise RuntimeError("Not logged in. Run:  connect.adapters.channels.run cli login")
    return client
