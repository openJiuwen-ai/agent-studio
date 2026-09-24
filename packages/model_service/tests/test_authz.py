# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Unit tests for model_service.authz."""

import pytest

from model_service.authz import (
    PROJECT_ID_HEADER,
    assert_project_id_trusted,
    check_authz,
    extract_project_id,
)


class TestExtractProjectId:
    def test_none_headers_returns_fallback(self):
        assert extract_project_id(None) == "0"

    def test_empty_headers_returns_fallback(self):
        assert extract_project_id({}) == "0"

    def test_custom_fallback(self):
        assert extract_project_id(None, fallback="my-fallback") == "my-fallback"

    def test_extracts_from_header(self):
        assert extract_project_id({PROJECT_ID_HEADER: "proj-1"}) == "proj-1"

    def test_extracts_lowercase_header(self):
        assert extract_project_id({"x-owner-project-id": "proj-2"}) == "proj-2"

    def test_prefers_canonical_header(self):
        headers = {PROJECT_ID_HEADER: "canonical", "x-owner-project-id": "lower"}
        assert extract_project_id(headers) == "canonical"

    def test_empty_header_value_falls_back(self):
        assert extract_project_id({PROJECT_ID_HEADER: ""}) == "0"

    def test_non_string_value_returned(self):
        assert extract_project_id({PROJECT_ID_HEADER: 123}) == 123


class TestAssertProjectIdTrusted:
    def test_returns_none(self):
        assert assert_project_id_trusted("p", source="test") is None

    def test_empty_project_id(self):
        assert assert_project_id_trusted("", source="test") is None


class TestCheckAuthz:
    def test_returns_none(self):
        import asyncio

        async def _run():
            assert await check_authz("user", "proj", "svc", "auth") is None

        asyncio.run(_run())
