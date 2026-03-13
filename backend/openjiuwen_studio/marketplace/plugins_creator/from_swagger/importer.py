#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
OpenAPI/Swagger Importer for OpenJiuwen Plugin Generator

This module automatically generates plugin configurations from OpenAPI/Swagger specifications.

Usage:
    # From URL
    python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --url
    https://petstore.swagger.io/v2/swagger.json

    # From file
    python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer
    --file /path/to/swagger.json

    # With custom options
    python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --url <url>
    --category ai --limit 10
"""

import argparse
import json
import os
import sys
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin
from openjiuwen.core.common.logging import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available. URL fetching will be disabled.")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML library not available. YAML parsing will be disabled.")

from backend.openjiuwen_studio.marketplace.plugins_creator.categories import CATEGORIES
from backend.openjiuwen_studio.marketplace.plugins_creator.templates import create_plugin_template, add_tool_to_plugin
from backend.openjiuwen_studio.marketplace.plugins_creator.plugins_creator import save_plugin


# Parameter type mapping from OpenAPI to plugin format
OPENAPI_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object"
}

# Parameter location mapping to send_method
OPENAPI_LOCATION_MAP = {
    "query": "Query",
    "header": "Header",
    "path": "Path",
    "body": "Body",
    "formData": "Body"
}


def fetch_openapi_spec(url: str) -> Dict[str, Any]:
    """
    Fetch OpenAPI/Swagger specification from a URL.

    Args:
        url: URL to the OpenAPI/Swagger JSON or YAML file

    Returns:
        Parsed OpenAPI specification as dictionary
    """
    if not REQUESTS_AVAILABLE:
        raise RuntimeError("requests library is required for URL fetching. Install with: pip install requests")

    logger.info(f"Fetching OpenAPI spec from: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Try to parse as JSON first
        try:
            return response.json()
        except json.JSONDecodeError:
            # Try YAML if JSON fails
            if YAML_AVAILABLE:
                return yaml.safe_load(response.text)
            else:
                raise RuntimeError("Failed to parse as JSON and PyYAML not available for YAML parsing")
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch OpenAPI spec from URL: {str(e)}")


def load_openapi_spec(filepath: str) -> Dict[str, Any]:
    """
    Load OpenAPI/Swagger specification from a file.

    Args:
        filepath: Path to the OpenAPI/Swagger JSON or YAML file

    Returns:
        Parsed OpenAPI specification as dictionary
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    logger.info(f"Loading OpenAPI spec from: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

        # Try JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try YAML if JSON fails
            if YAML_AVAILABLE:
                return yaml.safe_load(content)
            else:
                raise RuntimeError("Failed to parse as JSON and PyYAML not available for YAML parsing")


def extract_base_url(spec: Dict[str, Any]) -> str:
    """
    Extract base URL from OpenAPI specification.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        Base URL for the API
    """
    # OpenAPI 3.x
    if "servers" in spec and spec["servers"]:
        return spec["servers"][0]["url"]

    # Swagger 2.0
    if "host" in spec:
        scheme = spec.get("schemes", ["https"])[0]
        host = spec["host"]
        base_path = spec.get("basePath", "")
        return f"{scheme}://{host}{base_path}"

    return ""


def extract_authentication(spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract authentication configuration from OpenAPI specification.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        header_configuration dictionary or None
    """
    auth_config = None

    # OpenAPI 3.x
    if "components" in spec and "securitySchemes" in spec["components"]:
        schemes = spec["components"]["securitySchemes"]
        # Take first security scheme
        if schemes:
            scheme_name, scheme_data = next(iter(schemes.items()))
            auth_config = _parse_security_scheme(scheme_name, scheme_data)

    # Swagger 2.0
    elif "securityDefinitions" in spec:
        schemes = spec["securityDefinitions"]
        if schemes:
            scheme_name, scheme_data = next(iter(schemes.items()))
            auth_config = _parse_security_scheme(scheme_name, scheme_data)

    return auth_config


def _parse_security_scheme(name: str, scheme: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a security scheme into header_configuration format."""
    scheme_type = scheme.get("type", "").lower()

    if scheme_type == "oauth2":
        return {
            "Authorization": {
                "value": f"Bearer YOUR_{name.upper()}_TOKEN",
                "description": f"OAuth 2.0 Bearer token for {name} authentication"
            }
        }
    elif scheme_type == "apikey":
        header_name = scheme.get("name", "X-API-Key")
        return {
            header_name: {
                "value": f"YOUR_{name.upper()}_API_KEY",
                "description": f"API key for {name} authentication"
            }
        }
    elif scheme_type == "http":
        http_scheme = scheme.get("scheme", "").lower()
        if http_scheme == "bearer":
            return {
                "Authorization": {
                    "value": f"Bearer YOUR_{name.upper()}_BEARER_TOKEN",
                    "description": f"Bearer token for {name} authentication"
                }
            }
        elif http_scheme == "basic":
            return {
                "Authorization": {
                    "value": "Basic YOUR_BASE64_CREDENTIALS",
                    "description": f"Basic authentication credentials for {name} (Base64 encoded username:password)"
                }
            }

    return None


def extract_parameters(
    parameters: List[Dict[str, Any]],
    spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract and convert OpenAPI parameters to plugin format.

    Args:
        parameters: List of OpenAPI parameter objects
        spec: Full OpenAPI spec (for resolving $ref)

    Returns:
        Dictionary of parameters in plugin format
    """
    plugin_params = {}

    for param in parameters:
        # Resolve $ref if present
        if "$ref" in param:
            param = resolve_ref(param["$ref"], spec)

        name = param.get("name", "")
        if not name:
            continue

        # Get parameter type
        param_type = "string"
        if "schema" in param:
            param_type = OPENAPI_TYPE_MAP.get(param["schema"].get("type", "string"), "string")
        elif "type" in param:
            param_type = OPENAPI_TYPE_MAP.get(param.get("type", "string"), "string")

        # Get parameter location
        location = param.get("in", "query")
        send_method = OPENAPI_LOCATION_MAP.get(location, "Query")

        # Build parameter config
        param_config = {
            "type": param_type,
            "description": param.get("description", f"{name} parameter"),
            "required": param.get("required", False),
            "send_method": send_method
        }

        # Add default value if present
        if "default" in param:
            param_config["default"] = param["default"]
        elif "schema" in param and "default" in param["schema"]:
            param_config["default"] = param["schema"]["default"]

        # Add enum values if present
        if "enum" in param:
            param_config["enum"] = param["enum"]
        elif "schema" in param and "enum" in param["schema"]:
            param_config["enum"] = param["schema"]["enum"]

        plugin_params[name] = param_config

    return plugin_params


def extract_request_body_params(
    request_body: Dict[str, Any],
    spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract parameters from OpenAPI 3.x requestBody.

    Args:
        request_body: OpenAPI requestBody object
        spec: Full OpenAPI spec (for resolving $ref)

    Returns:
        Dictionary of parameters in plugin format
    """
    plugin_params = {}

    # Resolve $ref if present
    if "$ref" in request_body:
        request_body = resolve_ref(request_body["$ref"], spec)

    content = request_body.get("content", {})

    # Try application/json first, then other content types
    schema = None
    for content_type in ["application/json", "application/x-www-form-urlencoded", "*/*"]:
        if content_type in content:
            schema = content[content_type].get("schema")
            break

    if not schema:
        # Take first available content type
        if content:
            schema = next(iter(content.values())).get("schema")

    if schema:
        # Resolve $ref if present
        if "$ref" in schema:
            schema = resolve_ref(schema["$ref"], spec)

        # Extract properties from schema
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            # Resolve $ref if present
            if "$ref" in prop_schema:
                prop_schema = resolve_ref(prop_schema["$ref"], spec)

            param_type = OPENAPI_TYPE_MAP.get(prop_schema.get("type", "string"), "string")

            param_config = {
                "type": param_type,
                "description": prop_schema.get("description", f"{prop_name} field"),
                "required": prop_name in required_fields,
                "send_method": "Body"
            }

            # Add default value if present
            if "default" in prop_schema:
                param_config["default"] = prop_schema["default"]

            # Add enum values if present
            if "enum" in prop_schema:
                param_config["enum"] = prop_schema["enum"]

            plugin_params[prop_name] = param_config

    return plugin_params


def resolve_ref(ref: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve a $ref pointer in OpenAPI spec.

    Args:
        ref: Reference string (e.g., "#/definitions/Pet")
        spec: Full OpenAPI specification

    Returns:
        Resolved object
    """
    if not ref.startswith("#/"):
        return {}

    path_parts = ref[2:].split("/")
    result = spec

    for part in path_parts:
        if isinstance(result, dict) and part in result:
            result = result[part]
        else:
            return {}

    return result


def convert_openapi_to_plugin(
    spec: Dict[str, Any],
    plugin_id: str = None,
    category: str = "other",
    limit: int = None,
    skip_auth: bool = False
) -> Dict[str, Any]:
    """
    Convert OpenAPI specification to plugin configuration.

    Args:
        spec: OpenAPI specification dictionary
        plugin_id: Optional custom plugin ID
        category: Plugin category
        limit: Optional limit on number of tools to generate
        skip_auth: Skip authentication processing

    Returns:
        Plugin configuration dictionary
    """
    # Extract basic info
    info = spec.get("info", {})
    title = info.get("title", "API Plugin")
    description = info.get("description", title)
    version = info.get("version", "1.0.0")

    # Generate plugin ID if not provided
    if not plugin_id:
        plugin_id = re.sub(r'[^a-z0-9_]', '_', title.lower())

    # Extract base URL
    api_prefix = extract_base_url(spec)

    # Extract authentication
    authentication = None
    if not skip_auth:
        authentication = extract_authentication(spec)

    # Create plugin template
    # Swagger-imported plugins default to ready=False until manually reviewed
    plugin = create_plugin_template(
        plugin_id=plugin_id,
        name=title,
        description=description,
        category=category,
        metadata={
            "ready": False,
            "icon": CATEGORIES.get(category, CATEGORIES["other"])["icon"],
            "api_prefix": api_prefix,
            "author": "OpenJiuwen",
            "version": version
        }
    )

    # Add header_configuration if found
    if authentication:
        plugin["header_configuration"] = authentication

    # Extract paths/endpoints
    paths = spec.get("paths", {})
    tool_count = 0

    for path, path_item in paths.items():
        if limit and tool_count >= limit:
            break

        # Resolve $ref if present
        if "$ref" in path_item:
            path_item = resolve_ref(path_item["$ref"], spec)

        # Extract common parameters (apply to all operations)
        common_params = path_item.get("parameters", [])

        # Process each HTTP method
        for method in ["get", "post", "put", "delete", "patch"]:
            if limit and tool_count >= limit:
                break

            if method not in path_item:
                continue

            operation = path_item[method]

            # Resolve $ref if present
            if "$ref" in operation:
                operation = resolve_ref(operation["$ref"], spec)

            # Generate tool name
            operation_id = operation.get("operationId")
            summary = operation.get("summary", "")

            if operation_id:
                tool_name = operation_id.replace("_", " ").title()
            elif summary:
                tool_name = summary
            else:
                tool_name = f"{method.upper()} {path}"

            # Get description
            tool_desc = operation.get("description") or summary or f"{method.upper()} request to {path}"

            # Extract parameters
            operation_params = operation.get("parameters", [])
            all_params = common_params + operation_params
            request_params = extract_parameters(all_params, spec)

            # Extract request body (OpenAPI 3.x)
            if "requestBody" in operation:
                body_params = extract_request_body_params(operation["requestBody"], spec)
                request_params.update(body_params)

            # Create tool
            tool = {
                "name": tool_name,
                "path": path,
                "method": method.upper(),
                "description": tool_desc,
                "request_params": request_params
            }

            add_tool_to_plugin(plugin, tool)
            tool_count += 1

            logger.info(f"  Added tool: {tool_name} [{method.upper()} {path}]")

    logger.info(f"Generated plugin with {tool_count} tools")

    return plugin


def interactive_import():
    """Interactive mode for importing from OpenAPI/Swagger."""
    logger.info("\n🔌 OpenAPI/Swagger Plugin Importer - Interactive Mode\n")

    # Get source
    source_type = input("Import from (1) URL or (2) file? [1/2]: ").strip()

    spec = None
    if source_type == "1":
        url = input("Enter OpenAPI/Swagger URL: ").strip()
        spec = fetch_openapi_spec(url)
    else:
        filepath = input("Enter path to OpenAPI/Swagger file: ").strip()
        spec = load_openapi_spec(filepath)

    # Show API info
    info = spec.get("info", {})
    logger.info(f"\n📋 API Information:")
    logger.info(f"   Title: {info.get('title', 'Unknown')}")
    logger.info(f"   Description: {info.get('description', 'N/A')}")
    logger.info(f"   Version: {info.get('version', 'N/A')}")
    logger.info(f"   Base URL: {extract_base_url(spec)}")
    logger.info(f"   Total endpoints: {sum(len([m for m in p.keys() if m in ['get', 'post', 'put', 'delete', 'patch']]) 
                                           for p in spec.get('paths', {}).values())}")

    # Get plugin config
    plugin_id = input("\nPlugin ID (press Enter to auto-generate): ").strip() or None

    # Category
    logger.info("\nAvailable categories:")
    for key, cat in CATEGORIES.items():
        logger.info(f"  {key}: {cat['icon']} {cat['name']}")
    category = input("Category [other]: ").strip() or "other"

    if category not in CATEGORIES:
        logger.warning(f"Unknown category '{category}', using 'other'")
        category = "other"

    # Limit tools
    limit_input = input("\nLimit number of tools to import (press Enter for all): ").strip()
    limit = int(limit_input) if limit_input else None

    # Skip auth
    skip_auth = input("Skip authentication processing? (y/n) [n]: ").strip().lower() == 'y'

    # Convert
    plugin = convert_openapi_to_plugin(spec, plugin_id, category, limit, skip_auth)

    # Save
    filename = input(f"\nOutput filename [{plugin['plugin_id']}.json]: ").strip()
    filepath = save_plugin(plugin, category, filename or None)

    if filepath:
        logger.info("\n💡 Next steps:")
        logger.info("   1. Review the generated plugin file and adjust as needed")
        logger.info(f"   2. Validate: python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger."
                    f"from_swagger --validate {filepath}")
        logger.info("   3. Test loading in the plugin marketplace")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OpenAPI/Swagger Plugin Importer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --interactive

  # Import from URL
  python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer 
  --url https://petstore.swagger.io/v2/swagger.json --category developer

  # Import from file with limit
  python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --file swagger.json 
  --category ai --limit 10

  # Import with custom ID
  python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --url <url> 
  --id my_api_plugin --category data
        """
    )

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Interactive mode')
    parser.add_argument('--url', type=str,
                        help='URL to OpenAPI/Swagger specification')
    parser.add_argument('--file', type=str,
                        help='Path to OpenAPI/Swagger specification file')
    parser.add_argument('--id', type=str,
                        help='Plugin ID (auto-generated if not provided)')
    parser.add_argument('--category', type=str, choices=list(CATEGORIES.keys()),
                        default='other',
                        help='Plugin category (default: other)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of tools to import')
    parser.add_argument('--skip-auth', action='store_true',
                        help='Skip authentication processing')
    parser.add_argument('--output', '-o', type=str,
                        help='Output filename')

    args = parser.parse_args()

    # Interactive mode
    if args.interactive:
        interactive_import()
        return

    # Require either URL or file
    if not args.url and not args.file:
        parser.error("Either --url or --file is required (or use --interactive)")

    # Load spec
    try:
        if args.url:
            spec = fetch_openapi_spec(args.url)
        else:
            spec = load_openapi_spec(args.file)
    except Exception as e:
        logger.error(f"Failed to load OpenAPI spec: {str(e)}")
        sys.exit(1)

    # Convert to plugin
    try:
        plugin = convert_openapi_to_plugin(
            spec,
            plugin_id=args.id,
            category=args.category,
            limit=args.limit,
            skip_auth=args.skip_auth
        )
    except Exception as e:
        logger.error(f"Failed to convert OpenAPI spec to plugin: {str(e)}")
        sys.exit(1)

    # Save plugin
    filepath = save_plugin(plugin, args.category, args.output)
    if filepath:
        logger.info("\n💡 Next steps:")
        logger.info("   1. Review the generated plugin file and adjust as needed")
        logger.info("   2. Test loading in the plugin marketplace")


if __name__ == "__main__":
    main()
