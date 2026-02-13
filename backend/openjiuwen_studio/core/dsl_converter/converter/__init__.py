#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Workflow Import Module

This module provides functionality to import workflows from various sources:
- OpenJiuwen native format (exported workflows)
- n8n workflow format
- Future: Other workflow platforms

Architecture:
    1. Detector: Identifies workflow format from JSON
    2. Converter: Transforms foreign formats to OpenJiuwen format
    3. Validator: Validates converted workflows
    4. Importer: Orchestrates the import process
"""

from openjiuwen_studio.core.dsl_converter.converter.detector import WorkflowDetector, WorkflowFormat
from openjiuwen_studio.core.dsl_converter.converter.converter import (
    WorkflowConverter,
    ConverterFactory,
    WorkflowImportResult,
)
from openjiuwen_studio.core.dsl_converter.converter.converter_native import NativeWorkflowConverter
from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import N8nWorkflowConverter
from openjiuwen_studio.core.dsl_converter.converter.validator import WorkflowValidator, ValidationResult
from openjiuwen_studio.core.dsl_converter.converter.importer import (
    WorkflowImporter,
    ImportOptions,
    ImportResult,
)

__all__ = [
    "WorkflowDetector",
    "WorkflowFormat",
    "WorkflowConverter",
    "ConverterFactory",
    "WorkflowImportResult",
    "NativeWorkflowConverter",
    "N8nWorkflowConverter",
    "WorkflowValidator",
    "ValidationResult",
    "WorkflowImporter",
    "ImportOptions",
    "ImportResult",
]
