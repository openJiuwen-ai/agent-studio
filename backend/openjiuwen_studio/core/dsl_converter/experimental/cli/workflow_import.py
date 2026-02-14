#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
CLI Tool for Workflow Import

Usage:
    python -m cli.workflow_import workflow.json --space-id abc123 --user-id user456

Examples:
    # Import as draft
    python -m cli.workflow_import workflow.json --space-id space1 --user-id user1

    # With strict validation
    python -m cli.workflow_import workflow.json --space-id space1 --user-id user1 --validate
"""

import json
import sys
import asyncio
from pathlib import Path

import click
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.dsl_converter.converter.importer import WorkflowImporter, ImportOptions


@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.option('--space-id', required=True, help='Target workspace ID')
@click.option('--user-id', required=True, help='User ID for import')
@click.option('--validate/--no-validate', default=False,
              help='Strict validation (compile workflow)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def import_workflow(json_file, space_id, user_id, validate, verbose):
    """
    Import workflow from JSON file.

    Supported formats:
    - OpenJiuwen native export
    - n8n workflow JSON

    The workflow will be imported as a draft only.
    """
    # Set logging level
    if verbose:
        logger.setLevel("DEBUG")

    click.echo(f"\n{'='*60}")
    click.echo("OpenJiuwen Workflow Import Tool")
    click.echo(f"{'='*60}\n")

    # Load JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        click.echo(f"✓ Loaded workflow JSON: {json_file}")
    except json.JSONDecodeError as e:
        click.echo(f"✗ ERROR: Invalid JSON file: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ ERROR: Failed to read file: {e}", err=True)
        sys.exit(1)

    # Show file info
    file_size = Path(json_file).stat().st_size
    click.echo(f"  File size: {file_size:,} bytes")

    # Detect format
    from openjiuwen_studio.core.dsl_converter.converter.detector import WorkflowDetector
    detector = WorkflowDetector()
    format_type = detector.detect_format(json_data)
    click.echo(f"  Detected format: {format_type.value}")

    if format_type.value == "unsupported":
        click.echo("\n✗ ERROR: Unsupported workflow format", err=True)
        click.echo("  Supported formats: OpenJiuwen native, n8n")
        sys.exit(1)

    click.echo()

    # Build current_user context
    current_user = {"code": 200, "data": {"user_id_str": user_id}}

    # Build import options
    options = ImportOptions(
        validate_strict=validate
    )

    # Show import settings
    click.echo("Import settings:")
    click.echo(f"  Space ID: {space_id}")
    click.echo(f"  User ID: {user_id}")
    click.echo(f"  Strict validation: {validate}")
    click.echo()

    # Perform import
    click.echo("Importing workflow...")
    click.echo()

    importer = WorkflowImporter()

    try:
        result = asyncio.run(
            importer.import_workflow(
                json_data=json_data,
                space_id=space_id,
                current_user=current_user,
                options=options
            )
        )

        # Display result
        if result.success:
            click.echo(f"{'='*60}")
            click.echo("✓ Import Successful!")
            click.echo(f"{'='*60}\n")
            click.echo(f"Workflow ID: {result.workflow_id}")
            click.echo(f"Workflow Name: {result.workflow_name}")

            if result.metadata:
                click.echo("\nMetadata:")
                for key, value in result.metadata.items():
                    click.echo(f"  {key}: {value}")

            if result.warnings:
                click.echo(f"\n⚠ Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    click.echo(f"  • {warning}")

            sys.exit(0)

        else:
            click.echo(f"{'='*60}")
            click.echo("✗ Import Failed")
            click.echo(f"{'='*60}\n")

            if result.errors:
                click.echo(f"Errors ({len(result.errors)}):")
                for error in result.errors:
                    click.echo(f"  ✗ {error}")

            if result.warnings:
                click.echo(f"\nWarnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    click.echo(f"  ⚠ {warning}")

            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n\n✗ Import cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n✗ ERROR: Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            click.echo("\nTraceback:")
            click.echo(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    import_workflow()
