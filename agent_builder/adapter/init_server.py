# coding=utf-8
"""
Server initialization: local replacement for jiuwen.common.init.

Provides YAML config loading, environment variable management,
and server initialization functions.
"""

import json
import os
from json import JSONDecodeError

import yaml

from agent_builder.adapter.logger_bridge import logger

# Top-level config keys that are allowed to be loaded into environment variables
TOP_LEVEL_WHITELIST = {
    "datasource",
    "llm_service_url",
    "encrypt_n",
    "prompt",
    "plugin",
    "executor",
    "model_cfg",
    "default_models",
    "security_sandbox",
    "workflow",
    "execution",
    "insight",
    "sts",
    "cloud_map",
    "service",
    "examples",
    "store",
    "embedding_base_url",
    "embedding_api",
}


def config_to_env(yaml_cfg: dict, prefix: str = ""):
    """
    Recursively write YAML config values to environment variables.

    Dict keys are joined with underscores and uppercased.
    String values are set directly; other types are JSON-serialized.
    """
    for key, value in yaml_cfg.items():
        if value is None:
            continue
        # Skip top-level keys not in whitelist
        if prefix == "" and key not in TOP_LEVEL_WHITELIST:
            continue
        if isinstance(value, dict):
            config_to_env(value, prefix + key.upper() + "_")
        elif isinstance(value, str):
            os.environ[prefix + key.upper()] = value
        else:
            os.environ[prefix + key.upper()] = json.dumps(value)


def env_to_config(yaml_cfg: dict, prefix: str = ""):
    """
    Recursively override YAML config values with environment variables.

    For each leaf key in yaml_cfg, check if PREFIX_KEY_UPPER exists in env.
    If so, parse it (try JSON first, fall back to string) and overwrite.
    """
    for key, value in yaml_cfg.items():
        if isinstance(value, dict):
            env_to_config(value, prefix + key.upper() + "_")
        else:
            env_var_name = prefix + key.upper()
            if env_var_name and os.environ.get(env_var_name):
                env_var_value = os.environ.get(env_var_name)
                try:
                    yaml_cfg[key] = json.loads(env_var_value)
                except JSONDecodeError:
                    yaml_cfg[key] = env_var_value


def load_yaml_config(cfg_file: str = None) -> None:
    """
    Load configuration from a YAML file into environment variables.

    This replaces jiuwen's init_cfg() function.

    Args:
        cfg_file: Path to YAML config file.
                  None = skip loading.
                  Default (not passed) = try ./application.yaml.
    """
    if cfg_file is None:
        logger.info("User skip loading yaml configuration file by cfg_file=None")
        return

    if not cfg_file:
        # Default: try ./application.yaml
        cfg_file = os.path.join("./", "application.yaml")
        if not os.path.exists(cfg_file):
            logger.warning(
                f"Default 'application.yaml' not found in '{os.getcwd()}'. "
                "Skip loading configuration."
            )
            return
        logger.info(f"Loading config from default 'application.yaml' in '{os.getcwd()}'.")

    if not os.path.isfile(cfg_file):
        logger.warning(f"Config file not found: {cfg_file}. Skip loading.")
        return

    with open(cfg_file, "r", encoding="utf-8") as f:
        try:
            cfg_data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to parse YAML config: {e}")
            return

    if cfg_data:
        env_to_config(cfg_data)
        config_to_env(cfg_data)


def load_server_config(config: dict) -> dict:
    """
    Apply environment variable overrides to a server config dict.

    This replaces jiuwen's _env_to_config().
    """
    env_to_config(config)
    return config
