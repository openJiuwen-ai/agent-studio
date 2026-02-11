#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Base Workflow Convertor and Factory

Defines abstract convertor interface and factory for creating appropriate convertors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List

from openjiuwen_studio.core.dsl_converter.convertor.detector import WorkflowFormat


@dataclass
class WorkflowImportResult:
    """Result of workflow conversion"""
    workflow_data: Dict[str, Any]  # OpenJiuwen format workflow data
    warnings: List[str] = field(default_factory=list)  # Non-fatal issues
    metadata: Dict[str, Any] = field(default_factory=dict)  # Original source info


class WorkflowConvertor(ABC):
    """Abstract base class for workflow convertors"""

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


class ConvertorFactory:
    """Factory for creating appropriate workflow convertors"""

    @staticmethod
    def create(format_type: WorkflowFormat) -> WorkflowConvertor:
        """
        Create appropriate convertor for the given format.

        Args:
            format_type: Detected workflow format

        Returns:
            Appropriate WorkflowConvertor instance

        Raises:
            ValueError: If format is unsupported
        """
        if format_type == WorkflowFormat.OPENJIUWEN_NATIVE:
            from openjiuwen_studio.core.dsl_converter.convertor.convertor_native import NativeWorkflowConvertor
            return NativeWorkflowConvertor()

        elif format_type == WorkflowFormat.N8N:
            from openjiuwen_studio.core.dsl_converter.convertor.convertor_n8n import N8nWorkflowConvertor
            return N8nWorkflowConvertor()

        else:
            raise ValueError(f"Unsupported workflow format: {format_type}")
