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
    2. Convertor: Transforms foreign formats to OpenJiuwen format
    3. Validator: Validates converted workflows
    4. Importer: Orchestrates the import process
"""

from openjiuwen_studio.core.dsl_converter.convertor.detector import WorkflowDetector, WorkflowFormat
from openjiuwen_studio.core.dsl_converter.convertor.convertor import (
    WorkflowConvertor,
    ConvertorFactory,
    WorkflowImportResult,
)
from openjiuwen_studio.core.dsl_converter.convertor.convertor_native import NativeWorkflowConvertor
from openjiuwen_studio.core.dsl_converter.convertor.convertor_n8n import N8nWorkflowConvertor
from openjiuwen_studio.core.dsl_converter.convertor.validator import WorkflowValidator, ValidationResult
from openjiuwen_studio.core.dsl_converter.convertor.importer import (
    WorkflowImporter,
    ImportOptions,
    ImportResult,
)

__all__ = [
    "WorkflowDetector",
    "WorkflowFormat",
    "WorkflowConvertor",
    "ConvertorFactory",
    "WorkflowImportResult",
    "NativeWorkflowConvertor",
    "N8nWorkflowConvertor",
    "WorkflowValidator",
    "ValidationResult",
    "WorkflowImporter",
    "ImportOptions",
    "ImportResult",
]
