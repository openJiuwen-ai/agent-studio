#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Base Workflow Converter and Factory

Defines abstract converter interface and factory for creating appropriate converters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List

from openjiuwen_studio.core.dsl_converter.converter.detector import WorkflowFormat


@dataclass
class WorkflowImportResult:
    """Result of workflow conversion"""
    workflow_data: Dict[str, Any]  # OpenJiuwen format workflow data
    warnings: List[str] = field(default_factory=list)  # Non-fatal issues
    metadata: Dict[str, Any] = field(default_factory=dict)  # Original source info


class WorkflowConverter(ABC):
    """Abstract base class for workflow converters"""

    @abstractmethod
    def convert(self, json_data: Dict[str, Any]) -> WorkflowImportResult:
        """
        Convert workflow from source format to OpenJiuwen format.

        Args:
            json_data: Source workflow JSON data

        Returns:
            WorkflowImportResult with converted workflow data

        Raises:
            ValueError: If conversion fails
        """
        pass


class ConverterFactory:
    """Factory for creating appropriate workflow converters"""

    @staticmethod
    def create(format_type: WorkflowFormat) -> WorkflowConverter:
        """
        Create appropriate converter for the given format.

        Args:
            format_type: Detected workflow format

        Returns:
            Appropriate WorkflowConverter instance

        Raises:
            ValueError: If format is unsupported
        """
        if format_type == WorkflowFormat.OPENJIUWEN_NATIVE:
            from openjiuwen_studio.core.dsl_converter.converter.converter_native import NativeWorkflowConverter
            return NativeWorkflowConverter()

        elif format_type == WorkflowFormat.N8N:
            from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import N8nWorkflowConverter
            return N8nWorkflowConverter()

        else:
            raise ValueError(f"Unsupported workflow format: {format_type}")
