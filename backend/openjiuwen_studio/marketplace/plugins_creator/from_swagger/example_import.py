#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Example script demonstrating how to use the Swagger Importer programmatically.

This script shows how to import OpenAPI/Swagger specs and generate plugin configurations
without using the CLI.
"""
import logging

logger = logging.getLogger(__name__)


# Example 1: Import from URL
def example_from_url():
    """Example: Import from Petstore Swagger URL"""
    from openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer import (
        fetch_openapi_spec,
        convert_openapi_to_plugin
    )
    from openjiuwen_studio.marketplace.plugins_creator.plugins_creator import save_plugin

    # Fetch the OpenAPI spec
    spec = fetch_openapi_spec("https://petstore.swagger.io/v2/swagger.json")

    # Convert to plugin
    plugin = convert_openapi_to_plugin(
        spec=spec,
        plugin_id="petstore_api",
        category="developer",
        limit=10  # Import only first 10 endpoints
    )

    # Save to file
    filepath = save_plugin(plugin, category="developer", filename="petstore_api.json")
    logger.info(f"Plugin saved to: {filepath}")

    return plugin


# Example 2: Import from local file
def example_from_file():
    """Example: Import from local OpenAPI file"""
    from openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer import (
        load_openapi_spec,
        convert_openapi_to_plugin
    )
    from openjiuwen_studio.marketplace.plugins_creator.plugins_creator import save_plugin

    # Load from file
    spec = load_openapi_spec("/path/to/your/swagger.json")

    # Convert to plugin
    plugin = convert_openapi_to_plugin(
        spec=spec,
        plugin_id="my_custom_api",
        category="ai",
        limit=None,  # Import all endpoints
        skip_auth=False  # Process authentication
    )

    # Save to file
    filepath = save_plugin(plugin, category="ai")
    logger.info(f"Plugin saved to: {filepath}")

    return plugin


# Example 3: Custom processing
def example_custom_processing():
    """Example: Import and customize before saving"""
    from openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer import (
        fetch_openapi_spec,
        convert_openapi_to_plugin
    )
    from openjiuwen_studio.marketplace.plugins_creator.plugins_creator import save_plugin

    # Fetch spec
    spec = fetch_openapi_spec("https://api.example.com/swagger.json")

    # Convert to plugin
    plugin = convert_openapi_to_plugin(
        spec=spec,
        plugin_id="example_api",
        category="data"
    )

    # Customize plugin before saving
    plugin["tags"].append("custom")
    plugin["author"] = "My Company"

    # Customize first tool
    if plugin["tools"]:
        plugin["tools"][0]["description"] = "Custom description for better LLM understanding"

    # Add custom header to all tools
    for tool in plugin["tools"]:
        if "headers" not in tool:
            tool["headers"] = {}
        tool["headers"]["X-Custom-Header"] = "custom-value"

    # Save
    filepath = save_plugin(plugin, category="data")
    logger.info(f"Customized plugin saved to: {filepath}")

    return plugin


# Example 4: Inspect before saving
def example_inspect():
    """Example: Inspect the spec and generated plugin"""
    from openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer import (
        fetch_openapi_spec,
        convert_openapi_to_plugin,
        extract_base_url,
        extract_authentication
    )
    import json

    # Fetch spec
    spec = fetch_openapi_spec("https://petstore.swagger.io/v2/swagger.json")

    # Inspect spec
    logger.info(f"API Title: {spec.get('info', {}).get('title')}")
    logger.info(f"Base URL: {extract_base_url(spec)}")
    logger.info(f"Total paths: {len(spec.get('paths', {}))}")

    # Check authentication
    auth = extract_authentication(spec)
    if auth:
        logger.info(f"Authentication type: {auth['type']}")

    # Convert to plugin
    plugin = convert_openapi_to_plugin(
        spec=spec,
        plugin_id="petstore_inspect",
        category="developer",
        limit=5
    )

    # Inspect generated plugin
    logger.info(f"\nGenerated plugin:")
    logger.info(f"  ID: {plugin['plugin_id']}")
    logger.info(f"  Name: {plugin['name']}")
    logger.info(f"  Tools: {len(plugin['tools'])}")

    # Print first tool
    if plugin["tools"]:
        logger.info(f"\nFirst tool:")
        logger.info(json.dumps(plugin["tools"][0], indent=2))

    return plugin


# Example 5: Batch import multiple APIs
def example_batch_import():
    """Example: Import multiple APIs in batch"""
    from openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer import (
        fetch_openapi_spec,
        convert_openapi_to_plugin
    )
    from openjiuwen_studio.marketplace.plugins_creator.plugins_creator import save_plugin

    apis_to_import = [
        {
            "url": "https://petstore.swagger.io/v2/swagger.json",
            "id": "petstore",
            "category": "developer"
        },
        # Add more APIs here
        # {
        #     "url": "https://api.example.com/swagger.json",
        #     "id": "example_api",
        #     "category": "ai"
        # },
    ]

    results = []

    for api_config in apis_to_import:
        try:
            logger.info(f"\nImporting {api_config['id']}...")

            # Fetch and convert
            spec = fetch_openapi_spec(api_config["url"])
            plugin = convert_openapi_to_plugin(
                spec=spec,
                plugin_id=api_config["id"],
                category=api_config["category"],
                limit=10  # Limit to 10 tools per API
            )

            # Save
            filepath = save_plugin(plugin, category=api_config["category"])

            results.append({
                "id": api_config["id"],
                "status": "success",
                "filepath": filepath,
                "tools": len(plugin["tools"])
            })

            logger.info(f"✅ Successfully imported {api_config['id']} ({len(plugin['tools'])} tools)")

        except Exception as e:
            results.append({
                "id": api_config["id"],
                "status": "failed",
                "error": str(e)
            })
            logger.info(f"❌ Failed to import {api_config['id']}: {str(e)}")

    # Summary
    logger.info(f"\n=== Import Summary ===")
    logger.info(f"Total: {len(results)}")
    logger.info(f"Success: {sum(1 for r in results if r['status'] == 'success')}")
    logger.info(f"Failed: {sum(1 for r in results if r['status'] == 'failed')}")

    return results


if __name__ == "__main__":
    logger.info("OpenAPI/Swagger Importer Examples")
    logger.info("=" * 50)

    # Run examples (comment out the ones you don't want to run)

    # logger.info("\n1. Import from URL")
    # example_from_url()

    # logger.info("\n2. Import from file")
    # example_from_file()

    # logger.info("\n3. Custom processing")
    # example_custom_processing()

    logger.info("\n4. Inspect spec")
    example_inspect()

    # logger.info("\n5. Batch import")
    # example_batch_import()

    logger.info("\n" + "=" * 50)
    logger.info("Examples completed!")
