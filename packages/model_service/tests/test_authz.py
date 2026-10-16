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
    @staticmethod
    def test_none_headers_returns_fallback():
        assert extract_project_id(None) == "0"

    @staticmethod
    def test_empty_headers_returns_fallback():
        assert extract_project_id({}) == "0"

    @staticmethod
    def test_custom_fallback():
        assert extract_project_id(None, fallback="my-fallback") == "my-fallback"

    @staticmethod
    def test_extracts_from_header():
        assert extract_project_id({PROJECT_ID_HEADER: "proj-1"}) == "proj-1"

    @staticmethod
    def test_extracts_lowercase_header():
        assert extract_project_id({"x-owner-project-id": "proj-2"}) == "proj-2"

    @staticmethod
    def test_prefers_canonical_header():
        headers = {PROJECT_ID_HEADER: "canonical", "x-owner-project-id": "lower"}
        assert extract_project_id(headers) == "canonical"

    @staticmethod
    def test_empty_header_value_falls_back():
        assert extract_project_id({PROJECT_ID_HEADER: ""}) == "0"

    @staticmethod
    def test_non_string_value_returned():
        assert extract_project_id({PROJECT_ID_HEADER: 123}) == 123


class TestAssertProjectIdTrusted:
    @staticmethod
    def test_returns_none():
        assert assert_project_id_trusted("p", source="test") is None

    @staticmethod
    def test_empty_project_id():
        assert assert_project_id_trusted("", source="test") is None


class TestCheckAuthz:
    @staticmethod
    def test_returns_none():
        import asyncio

        async def _run():
            assert await check_authz("user", "proj", "svc", "auth") is None

        asyncio.run(_run())
