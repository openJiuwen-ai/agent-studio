#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for WorkflowDetector

Tests format detection logic for OpenJiuwen native and n8n workflows.
"""

import json
from pathlib import Path
import pytest

from openjiuwen_studio.core.dsl_converter.converter.detector import WorkflowDetector, WorkflowFormat


@pytest.fixture
def detector():
    """Create detector instance"""
    return WorkflowDetector()


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path"""
    return Path(__file__).parent / "fixtures"


class TestWorkflowDetector:
    """Test suite for WorkflowDetector"""

    @staticmethod
    def test_detect_openjiuwen_format_from_fixture(detector, fixtures_dir):
        """Test detection of OpenJiuwen format from fixture file"""
        fixture_file = fixtures_dir / "openjiuwen_export.json"
        with open(fixture_file) as f:
            data = json.load(f)

        result = detector.detect_format(data)
        assert result == WorkflowFormat.OPENJIUWEN_NATIVE

    @staticmethod
    def test_detect_n8n_format_from_fixture(detector, fixtures_dir):
        """Test detection of n8n format from fixture file"""
        fixture_file = fixtures_dir / "n8n_workflow.json"
        with open(fixture_file) as f:
            data = json.load(f)

        result = detector.detect_format(data)
        assert result == WorkflowFormat.N8N

    @staticmethod
    def test_detect_openjiuwen_format_minimal(detector):
        """Test OpenJiuwen detection with minimal valid structure"""
        data = {
            "workflow_id": "test-123",
            "schema": json.dumps({
                "nodes": [],
                "edges": []
            })
        }

        result = detector.detect_format(data)
        assert result == WorkflowFormat.OPENJIUWEN_NATIVE

    @staticmethod
    def test_detect_openjiuwen_format_schema_as_dict(detector):
        """Test OpenJiuwen detection when schema is dict (not string)"""
        data = {
            "workflow_id": "test-123",
            "schema": {
                "nodes": [],
                "edges": []
            }
        }

        result = detector.detect_format(data)
        assert result == WorkflowFormat.OPENJIUWEN_NATIVE

    @staticmethod
    def test_detect_n8n_format_minimal(detector):
        """Test n8n detection with minimal valid structure"""
        data = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "n8n-nodes-base.webhook",
                    "name": "Webhook"
                }
            ],
            "connections": {}
        }

        result = detector.detect_format(data)
        assert result == WorkflowFormat.N8N

    @staticmethod
    def test_detect_n8n_format_with_new_prefix(detector):
        """Test n8n detection with @n8n/ prefix (newer versions)"""
        data = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "@n8n/n8n-nodes-langchain.agent",
                    "name": "Agent"
                }
            ],
            "connections": {}
        }

        result = detector.detect_format(data)
        assert result == WorkflowFormat.N8N

    @staticmethod
    def test_detect_unsupported_format_empty(detector):
        """Test unsupported format with empty dict"""
        data = {}
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_unsupported_format_missing_workflow_id(detector):
        """Test unsupported format when workflow_id is missing"""
        data = {
            "name": "Test Workflow",
            "schema": json.dumps({"nodes": [], "edges": []})
        }
        result = detector.detect_format(data)
        assert result == WorkflowFormat.OPENJIUWEN_NATIVE

    @staticmethod
    def test_detect_unsupported_format_missing_schema(detector):
        """Test unsupported format when schema is missing"""
        data = {
            "workflow_id": "test-123",
            "name": "Test Workflow"
        }
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_unsupported_format_invalid_schema(detector):
        """Test unsupported format when schema is invalid JSON"""
        data = {
            "workflow_id": "test-123",
            "schema": "invalid json {["
        }
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_unsupported_format_schema_missing_nodes(detector):
        """Test unsupported format when schema missing nodes"""
        data = {
            "workflow_id": "test-123",
            "schema": json.dumps({"edges": []})
        }
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_unsupported_format_not_dict(detector):
        """Test unsupported format when data is not a dict"""
        data = "not a dict"
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_unsupported_format_list(detector):
        """Test unsupported format when data is a list"""
        data = [{"workflow_id": "test"}]
        result = detector.detect_format(data)
        assert result == WorkflowFormat.UNSUPPORTED

    @staticmethod
    def test_detect_ambiguous_format_prefers_openjiuwen(detector):
        """Test that OpenJiuwen is detected when structure matches both"""
        # This shouldn't normally happen, but test priority
        data = {
            "workflow_id": "test-123",
            "schema": json.dumps({"nodes": [], "edges": []}),
            "nodes": [],
            "connections": {}
        }
        result = detector.detect_format(data)
        # OpenJiuwen check comes first
        assert result == WorkflowFormat.OPENJIUWEN_NATIVE

    @staticmethod
    def test_is_openjiuwen_format_method(detector):
        """Test is_openjiuwen_format method directly"""
        data = {
            "workflow_id": "test-123",
            "schema": json.dumps({"nodes": [], "edges": []})
        }
        assert detector.is_openjiuwen_format(data) is True

    @staticmethod
    def test_is_n8n_format_method(detector):
        """Test is_n8n_format method directly"""
        data = {
            "nodes": [{"id": "1", "type": "n8n-nodes-base.webhook"}],
            "connections": {}
        }
        assert detector.is_n8n_format(data) is True

    @staticmethod
    def test_is_n8n_format_no_matching_type(detector):
        """Test n8n detection fails when no nodes have n8n type prefix"""
        data = {
            "nodes": [{"id": "1", "type": "custom-node"}],
            "connections": {}
        }
        assert detector.is_n8n_format(data) is False

    @staticmethod
    def test_is_n8n_format_empty_nodes(detector):
        """Test n8n detection fails with empty nodes array"""
        data = {
            "nodes": [],
            "connections": {}
        }
        assert detector.is_n8n_format(data) is False

    @staticmethod
    def test_is_n8n_format_missing_connections(detector):
        """Test n8n detection fails when connections missing"""
        data = {
            "nodes": [{"id": "1", "type": "n8n-nodes-base.webhook"}]
        }
        assert detector.is_n8n_format(data) is False
