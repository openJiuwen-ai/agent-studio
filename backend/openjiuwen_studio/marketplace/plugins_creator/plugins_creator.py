#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
OpenJiuwen Plugin Generator CLI

This CLI tool helps you create new plugin configuration files for the OpenJiuwen Studio plugin marketplace.

Usage:
    python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --interactive
    python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --name "My Plugin" --category social
                                                                                               --id my_plugin
    python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --validate /path/to/plugin.json
"""

import argparse
import json
import os
import sys
from typing import Dict, Any
from openjiuwen.core.common.logging import logger

from .categories import CATEGORIES
from .validator import validate_plugin, validate_file
from .templates import create_plugin_template, create_tool_template, add_tool_to_plugin


def get_plugins_dir(category: str) -> str:
    """Get the directory path for a plugin category."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, f"../ready_plugins/{category}")


def get_index_path() -> str:
    """Get the path to the index.json file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "../ready_plugins/index.json")


def update_index(category: str, plugin_filename: str):
    """
    Update the index.json file to include the new plugin.

    Args:
        category: Plugin category
        plugin_filename: Name of the plugin JSON file
    """
    try:
        index_path = get_index_path()

        if not os.path.exists(index_path):
            logger.warning(f"index.json not found at {index_path}")
            return

        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        # Ensure category exists
        if category not in index_data.get("categories", {}):
            logger.warning(f"Category '{category}' not found in index.json")
            logger.info(f"   Available categories: {', '.join(index_data.get('categories', {}).keys())}")
            return

        # Add plugin to category if not already there
        plugin_path = f"{category}/{plugin_filename}"
        category_plugins = index_data["categories"][category].get("plugins", [])

        if plugin_path not in category_plugins:
            category_plugins.append(plugin_path)
            index_data["categories"][category]["plugins"] = category_plugins

            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Updated index.json to include {plugin_path}")
        else:
            logger.info(f"Plugin {plugin_path} already in index.json")
    except Exception as e:
        logger.error(f"Error updating index.json: {str(e)}", exc_info=True)


def interactive_mode():
    """Interactive mode for creating a plugin."""
    logger.info("\n🎨 OpenJiuwen Plugin Generator - Interactive Mode\n")

    # Basic info
    plugin_id = input("Plugin ID (lowercase, underscores only): ").strip()
    name = input("Plugin Name: ").strip()
    description = input("Description: ").strip()

    # Category
    logger.info("\nAvailable categories:")
    for key, cat in CATEGORIES.items():
        logger.info(f"  {key}: {cat['icon']} {cat['name']}")
    category = input("Category: ").strip()

    if category not in CATEGORIES:
        logger.warning(f"Unknown category '{category}', using 'other'")
        category = "other"

    icon = input(f"Icon (default: {CATEGORIES[category]['icon']}): ").strip() or CATEGORIES[category]['icon']
    api_prefix = input("API Base URL: ").strip()
    author = input("Author (default: OpenJiuwen): ").strip() or "OpenJiuwen"
    version = input("Version (default: 1.0.0): ").strip() or "1.0.0"

    # Header configuration
    header_configuration = {}
    add_headers = input("\nAdd header configuration (e.g., API keys)? (y/n): ").strip().lower()
    if add_headers == 'y':
        logger.info("\n🔑 Header Configuration")
        while True:
            header_name = input("  Header name (or enter to finish): ").strip()
            if not header_name:
                break

            env_var = input(f"  Environment variable for {header_name}: ").strip()
            header_desc = input(f"  Description for {header_name}: ").strip()

            header_configuration[header_name] = {
                "value": env_var,
                "description": header_desc
            }
            logger.info(f"  ✅ Added header: {header_name}")

    # Readiness status
    ready_input = input("\nIs this plugin ready for production use? (y/n, default: n): ").strip().lower()
    ready = ready_input == 'y'

    # Create plugin
    metadata = {
        "icon": icon,
        "author": author,
        "version": version,
        "ready": ready
    }

    if api_prefix:
        metadata["api_prefix"] = api_prefix

    if header_configuration:
        metadata["header_configuration"] = header_configuration

    plugin = create_plugin_template(
        plugin_id=plugin_id,
        name=name,
        description=description,
        category=category,
        metadata=metadata
    )

    # Add tools
    logger.info("\n📦 Add Tools (endpoints)")
    while True:
        add_tool = input("\nAdd a tool? (y/n): ").strip().lower()
        if add_tool != 'y':
            break

        tool_name = input("  Tool name: ").strip()
        tool_path = input("  API path: ").strip()
        tool_method = input("  HTTP method (GET/POST/PUT/DELETE/PATCH): ").strip().upper()
        tool_desc = input("  Description: ").strip()

        tool = create_tool_template(tool_name, tool_path, tool_method, tool_desc)

        # Add parameters
        choice = input("  Add request parameters? (y/n): ").strip().lower()
        if choice == 'y':
            while True:
                param_name = input("    Parameter name (or enter to finish): ").strip()
                if not param_name:
                    break

                param_type = input("    Type (string/integer/number/boolean/array/object): ").strip()
                param_desc = input("    Description: ").strip()
                param_required = input("    Required? (y/n): ").strip().lower() == 'y'

                # Ask for send_method
                logger.info("    Parameter method:")
                logger.info("      0 = None (unused)")
                logger.info("      1 = Header (HTTP header)")
                logger.info("      2 = Query (query string)")
                logger.info("      3 = Body (request body)")
                logger.info("      4 = Path (URL path parameter)")
                send_method_input = input("    Choose (0/1/2/3/4, default=2 for Query): ").strip()
                send_method_map = {"0": "None", "1": "Header", "2": "Query", "3": "Body", "4": "Path"}
                send_method = send_method_map.get(send_method_input, "Query")

                # Ask for runtime flag
                is_runtime = input("    Is runtime parameter? (y/n, default=y): ").strip().lower()
                is_runtime = is_runtime != 'n'  # Default to True unless explicitly 'n'

                # If not runtime, ask for default value
                default_value = None
                if not is_runtime:
                    default_input = input("    Default value: ").strip()
                    if default_input:
                        # Try to parse based on type
                        if param_type == "integer":
                            try:
                                default_value = int(default_input)
                            except ValueError:
                                default_value = default_input
                        elif param_type == "number":
                            try:
                                default_value = float(default_input)
                            except ValueError:
                                default_value = default_input
                        elif param_type == "boolean":
                            default_value = default_input.lower() in ('true', 'yes', 'y', '1')
                        else:
                            default_value = default_input

                param_config = {
                    "type": param_type,
                    "description": param_desc,
                    "required": param_required,
                    "send_method": send_method,
                    "is_runtime": is_runtime
                }

                if default_value is not None:
                    param_config["default"] = default_value

                tool["request_params"][param_name] = param_config

        # Add output/response parameters
        choice = input("  Add response/output parameters? (y/n): ")
        if choice == 'y':
            tool["response_params"] = {}
            while True:
                param_name = input("    Output parameter name (or enter to finish): ").strip()
                if not param_name:
                    break

                param_type = input("    Type (string/integer/number/boolean/array/object): ").strip()
                param_desc = input("    Description: ").strip()

                tool["response_params"][param_name] = {
                    "type": param_type,
                    "description": param_desc
                }

        # Add headers
        choice = input(" Add HTTP headers? (y/n): ").strip().lower()
        if choice == 'y':
            tool["headers"] = {}
            while True:
                header_name = input("    Header name (or enter to finish): ").strip()
                if not header_name:
                    break

                header_value = input("    Header value: ").strip()

                tool["headers"][header_name] = header_value

        add_tool_to_plugin(plugin, tool)
        logger.info(f"  ✅ Added tool: {tool_name}")

    return plugin


def save_plugin(plugin: Dict[str, Any], category: str, filename: str = None) -> str:
    """
    Save a plugin configuration to a file.

    Args:
        plugin: Plugin configuration dictionary
        category: Plugin category
        filename: Optional output filename

    Returns:
        Path to the saved file, or None if not saved
    """
    # Ensure category directory exists
    plugins_dir = get_plugins_dir(category)
    os.makedirs(plugins_dir, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        filename = f"{plugin['plugin_id']}.json"

    if not filename.endswith('.json'):
        filename += '.json'

    filepath = os.path.join(plugins_dir, filename)

    # Validate before saving
    is_valid, message = validate_plugin(plugin)
    if not is_valid:
        logger.error(f"Validation failed: {message}")
        save_anyway = input("Save anyway? (y/n): ").strip().lower()
        if save_anyway != 'y':
            return None
    else:
        logger.info(f"{message}")

    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(plugin, f, ensure_ascii=False, indent=2)

    logger.info(f"Plugin saved to: {filepath}")

    # Update index
    logger.info(f"Updating index.json...")
    update_index(category, filename)

    return filepath


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OpenJiuwen Plugin Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --interactive

  # Create from command line
  python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --name "Slack API" --category social --id slack_api

  # Validate existing plugin
  python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --validate backend/openjiuwen_studio/marketplace/ready_plugins/social/twitter.json
        """
    )

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive mode')
    parser.add_argument('--name', type=str,
                        help='Plugin name')
    parser.add_argument('--id', type=str,
                        help='Plugin ID')
    parser.add_argument('--description', '--desc', type=str,
                        help='Plugin description')
    parser.add_argument('--category', type=str, choices=list(CATEGORIES.keys()),
                        help='Plugin category')
    parser.add_argument('--icon', type=str,
                        help='Plugin icon (emoji or URL)')
    parser.add_argument('--api-prefix', type=str,
                        help='API base URL')
    parser.add_argument('--author', type=str, default='OpenJiuwen',
                        help='Plugin author')
    parser.add_argument('--version', type=str, default='1.0.0',
                        help='Plugin version')
    parser.add_argument('--output', '-o', type=str,
                        help='Output filename')
    parser.add_argument('--validate', type=str,
                        help='Validate an existing plugin file')

    args = parser.parse_args()

    # Validate mode
    if args.validate:
        success = validate_file(args.validate)
        sys.exit(0 if success else 1)

    # Interactive mode
    if args.interactive:
        plugin = interactive_mode()
        category = plugin.get('category', 'other')
        filepath = save_plugin(plugin, category, args.output)
        if filepath:
            logger.info("\n💡 Next steps:")
            logger.info("   1. Edit the plugin file to add more tools and parameters")
            logger.info(f"   2. Validate: python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator "
                        f"--validate {filepath}")
            logger.info("   3. Test loading in the plugin marketplace")
        return

    # Command line mode
    if not args.name or not args.id or not args.category:
        parser.error("--name, --id, and --category are required (or use --interactive)")

    if not args.description:
        args.description = f"{args.name} plugin for OpenJiuwen Studio"

    icon = args.icon or CATEGORIES[args.category]['icon']

    plugin = create_plugin_template(
        plugin_id=args.id,
        name=args.name,
        description=args.description,
        category=args.category,
        metadata={
            "icon": icon,
            "api_prefix": args.api_prefix or "",
            "author": args.author,
            "version": args.version
        }
    )

    filepath = save_plugin(plugin, args.category, args.output)
    if filepath:
        logger.info("\n💡 Next steps:")
        logger.info("   1. Edit the plugin file to add tools and parameters")
        logger.info(f"   2. Validate: python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator "
                    f"--validate {filepath}")
        logger.info("   3. Test loading in the plugin marketplace")


if __name__ == "__main__":
    main()
