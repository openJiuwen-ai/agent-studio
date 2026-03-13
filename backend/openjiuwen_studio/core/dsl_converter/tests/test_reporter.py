#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for Reporter

Tests the step tracking and reporting functionality.
"""

import logging
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone

from openjiuwen_studio.core.dsl_converter.converter.reporter import Reporter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures (used when running under pytest)
# ---------------------------------------------------------------------------

try:
    import pytest

    @pytest.fixture
    def reporter():
        """Pytest fixture: a fresh Reporter instance."""
        return Reporter()

except ImportError:
    pytest = None


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestReporter:
    """Test suite for Reporter"""

    # --- Initialization ---

    @staticmethod
    def test_init_creates_empty_steps_list():
        """Reporter starts with an empty steps list"""
        reporter = Reporter()
        assert reporter.steps == []

    @staticmethod
    def test_init_multiple_instances_independent():
        """Multiple Reporter instances have independent steps lists"""
        reporter1 = Reporter()
        reporter2 = Reporter()
        
        reporter1.add_step("Step 1", True)
        
        assert len(reporter1.steps) == 1
        assert len(reporter2.steps) == 0

    # --- add_step: Basic functionality ---

    @staticmethod
    def test_add_successful_step():
        """Successful step is stored with correct fields"""
        reporter = Reporter()
        reporter.add_step("Initialize database", True)

        assert len(reporter.steps) == 1
        step = reporter.steps[0]
        assert step["step_name"] == "Initialize database"
        assert step["success"] is True
        assert step["error"] == ""
        assert "timestamp" in step

    @staticmethod
    def test_add_failed_step_with_error():
        """Failed step is stored with the provided error message"""
        reporter = Reporter()
        reporter.add_step("Connect to API", False, "Connection timeout after 30 seconds")

        step = reporter.steps[0]
        assert step["step_name"] == "Connect to API"
        assert step["success"] is False
        assert step["error"] == "Connection timeout after 30 seconds"

    @staticmethod
    def test_successful_step_error_field_is_empty():
        """Error field is always empty for a successful step, even if one is passed"""
        reporter = Reporter()
        reporter.add_step("Load config", True, "this should be ignored")

        assert reporter.steps[0]["error"] == ""

    @staticmethod
    def test_add_multiple_steps_preserved_in_order():
        """Multiple steps are preserved in insertion order"""
        reporter = Reporter()
        reporter.add_step("Step A", True)
        reporter.add_step("Step B", False, "err")
        reporter.add_step("Step C", True)

        names = [s["step_name"] for s in reporter.steps]
        assert names == ["Step A", "Step B", "Step C"]

    @staticmethod
    def test_add_step_timestamp_is_iso_format():
        """Step timestamp is in ISO format"""
        reporter = Reporter()
        reporter.add_step("Test step", True)

        timestamp = reporter.steps[0]["timestamp"]
        # Should be able to parse as ISO format
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            assert False, f"Timestamp '{timestamp}' is not in ISO format"

    @staticmethod
    def test_add_step_timestamp_is_recent():
        """Step timestamp is close to current time"""
        before = datetime.now(timezone.utc)
        reporter = Reporter()
        reporter.add_step("Test step", True)
        after = datetime.now(timezone.utc)

        timestamp = datetime.fromisoformat(reporter.steps[0]["timestamp"])
        assert before <= timestamp <= after

    # --- add_step: Edge cases ---

    @staticmethod
    def test_add_step_empty_step_name():
        """Step with empty name is allowed"""
        reporter = Reporter()
        reporter.add_step("", True)

        assert len(reporter.steps) == 1
        assert reporter.steps[0]["step_name"] == ""

    @staticmethod
    def test_add_step_special_characters_in_name():
        """Step name with special characters is preserved"""
        reporter = Reporter()
        special_name = "Step with <special> & 'chars'!"
        reporter.add_step(special_name, True)

        assert reporter.steps[0]["step_name"] == special_name

    @staticmethod
    def test_add_step_unicode_in_name():
        """Step name with unicode characters is preserved"""
        reporter = Reporter()
        unicode_name = "步骤测试 🚀"
        reporter.add_step(unicode_name, True)

        assert reporter.steps[0]["step_name"] == unicode_name

    @staticmethod
    def test_add_step_empty_error_message():
        """Failed step with empty error message is allowed"""
        reporter = Reporter()
        reporter.add_step("Failed step", False, "")

        assert reporter.steps[0]["success"] is False
        assert reporter.steps[0]["error"] == ""

    @staticmethod
    def test_add_step_multiline_error_message():
        """Failed step with multiline error message is preserved"""
        reporter = Reporter()
        error_msg = "Error line 1\nError line 2\nError line 3"
        reporter.add_step("Failed step", False, error_msg)

        assert reporter.steps[0]["error"] == error_msg

    # --- log_trace ---

    @staticmethod
    def test_log_trace_empty():
        """log_trace returns empty list when no steps"""
        reporter = Reporter()
        trace = reporter.log_trace()

        assert trace == []
        assert isinstance(trace, list)

    @staticmethod
    def test_log_trace_single_success():
        """log_trace formats a single successful step"""
        reporter = Reporter()
        reporter.add_step("Initialize", True)

        trace = reporter.log_trace()
        assert len(trace) == 1
        assert "Initialize" in trace[0]
        assert "[success]" in trace[0]

    @staticmethod
    def test_log_trace_single_failure():
        """log_trace formats a single failed step with error"""
        reporter = Reporter()
        reporter.add_step("Connect", False, "Connection refused")

        trace = reporter.log_trace()
        assert len(trace) == 1
        assert "Connect" in trace[0]
        assert "[failed]" in trace[0]
        assert "Connection refused" in trace[0]

    @staticmethod
    def test_log_trace_multiple_steps():
        """log_trace formats multiple steps in order"""
        reporter = Reporter()
        reporter.add_step("Step 1", True)
        reporter.add_step("Step 2", False, "Error 1")
        reporter.add_step("Step 3", True)
        reporter.add_step("Step 4", False, "Error 2")

        trace = reporter.log_trace()
        assert len(trace) == 4
        assert "[success]" in trace[0]
        assert "[failed]" in trace[1]
        assert "[success]" in trace[2]
        assert "[failed]" in trace[3]
        assert "Error 1" in trace[1]
        assert "Error 2" in trace[3]

    @staticmethod
    def test_log_trace_returns_list_of_strings():
        """log_trace returns a list of strings"""
        reporter = Reporter()
        reporter.add_step("Test", True)

        trace = reporter.log_trace()
        assert isinstance(trace, list)
        assert all(isinstance(item, str) for item in trace)

    @staticmethod
    def test_log_trace_step_order_matches_internal():
        """log_trace returns steps in the same order as internal storage"""
        reporter = Reporter()
        reporter.add_step("A", True)
        reporter.add_step("B", False, "err")
        reporter.add_step("C", True)

        trace = reporter.log_trace()
        step_names_from_trace = [t.split(" [")[0] for t in trace]
        step_names_from_steps = [s["step_name"] for s in reporter.steps]
        
        assert step_names_from_trace == step_names_from_steps

    # --- Integration scenarios ---

    @staticmethod
    def test_full_workflow_simulation():
        """Simulate a complete workflow with multiple steps"""
        reporter = Reporter()
        
        # Simulate a workflow import process
        reporter.add_step("Starting import workflow", True)
        reporter.add_step("Validate workflow JSON structure", True)
        reporter.add_step("Detect workflow format", True)
        reporter.add_step("Validate format support", True)
        reporter.add_step("Convert to OpenJiuwen format", True)
        reporter.add_step("Validate workflow structure", True)
        reporter.add_step("Create workflow in database", True)
        reporter.add_step("Save canvas schema", True)
        reporter.add_step("Complete workflow import successfully", True)

        assert len(reporter.steps) == 9
        assert all(s["success"] for s in reporter.steps)

        trace = reporter.log_trace()
        assert len(trace) == 9
        assert all("[success]" in t for t in trace)

    @staticmethod
    def test_workflow_with_failures():
        """Simulate a workflow that fails at some step"""
        reporter = Reporter()
        
        reporter.add_step("Starting import workflow", True)
        reporter.add_step("Validate workflow JSON structure", True)
        reporter.add_step("Detect workflow format", False, "Unsupported format")
        
        trace = reporter.log_trace()
        assert len(trace) == 3
        assert trace[2].endswith("[failed]: Unsupported format")

    @staticmethod
    def test_error_propagation_through_trace():
        """Error messages are properly propagated through log_trace"""
        reporter = Reporter()
        error_messages = [
            "Invalid JSON: expected object",
            "Connection timeout",
            "Database constraint violation",
        ]
        
        for error in error_messages:
            reporter.add_step(f"Step failing with: {error}", False, error)

        trace = reporter.log_trace()
        for i, error in enumerate(error_messages):
            assert error in trace[i]


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Configure logging for standalone run
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Collect all test methods from TestReporter
    test_methods = [
        method for method in dir(TestReporter)
        if method.startswith("test_") and callable(getattr(TestReporter, method))
    ]

    passed = failed = 0
    logger.info("=" * 60)
    logger.info("Running TestReporter")
    logger.info("=" * 60)

    for method_name in sorted(test_methods):
        test_fn = getattr(TestReporter, method_name)
        try:
            test_fn()
            logger.info(f"  ✓  {method_name}")
            passed += 1
        except Exception:
            logger.error(f"  ✗  {method_name}")
            traceback.print_exc()
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    sys.exit(0 if failed == 0 else 1)
