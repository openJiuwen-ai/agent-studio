"""Login command."""
import getpass

from openjiuwen.core.common.logging import logger
from connect.client.auth.do_login import do_login
from connect.client.auth.token_storage import get_user_token, remove_user_token, set_user_data
from connect.client.auth.verify_token import verify_token as api_verify_token
from connect.client import OpenJiuwenClient
from connect.client.config import ENABLE_PASSWORD_LOGIN

from ...session import CLI_USER_ID


def cmd_login(backend_url: str) -> None:
    token = get_user_token(CLI_USER_ID)
    if token:
        client = OpenJiuwenClient(base_url=backend_url)
        client.set_token(token)
        try:
            api_verify_token(client)
            logger.info("✅ Already logged in. Use 'logout' to sign out.")
            return
        except Exception:
            remove_user_token(CLI_USER_ID)

    username = input("Username (email): ").strip()
    if not username:
        raise RuntimeError("Username cannot be empty.")

    if ENABLE_PASSWORD_LOGIN:
        password = getpass.getpass("Password: ")
    else:
        password = ""

    client = OpenJiuwenClient(base_url=backend_url)
    logger.info("🔐 Logging in...")
    try:
        result = do_login(client, username, password)
        set_user_data(CLI_USER_ID, result['token'], result['space_id'], result['refresh_token'])
        logger.info(f"✅ Logged in as {username}")
    except Exception as e:
        raise RuntimeError(f"Login failed: {e}") from e
