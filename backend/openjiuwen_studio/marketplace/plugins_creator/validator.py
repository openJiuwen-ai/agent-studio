#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Plugin validation utilities for OpenJiuwen Studio.
"""

import json
import os
from typing import Dict, Any, Tuple
from openjiuwen.core.common.logging import logger

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger.warning("jsonschema library not available")


def get_schema_path() -> str:
    """Get the path to the plugin schema file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "../ready_plugins/schema.json")


def load_schema() -> Dict[str, Any]:
    """Load the plugin JSON schema."""
    schema_path = get_schema_path()
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_plugin(plugin_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate plugin data against the schema.

    Args:
        plugin_data: Plugin configuration dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not JSONSCHEMA_AVAILABLE:
        return True, "Validation skipped (jsonschema not installed)"

    try:
        schema = load_schema()
        jsonschema.validate(instance=plugin_data, schema=schema)
        return True, "Validation successful"
    except jsonschema.ValidationError as e:
        return False, f"Validation error: {e.message} at path {'.'.join(str(p) for p in e.path)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_file(filepath: str):
    """
    Validate an existing plugin file.

    Args:
        filepath: Path to the plugin JSON file
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            plugin_data = json.load(f)

        is_valid, message = validate_plugin(plugin_data)

        if is_valid:
            logger.info(f"{message}")
            logger.info(f"   Plugin: {plugin_data.get('name', 'Unknown')}")
            logger.info(f"   ID: {plugin_data.get('plugin_id', 'Unknown')}")
            logger.info(f"   Tools: {len(plugin_data.get('tools', []))}")
            return True
        else:
            logger.error(f"{message}")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False
