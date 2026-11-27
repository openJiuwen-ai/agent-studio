"""知识库列表：越权与数据库故障不能再伪装成"空列表"。"""

import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("SQLITE_DB_PATH", str(Path(__file__).resolve().parent / ".tmp-db"))
os.environ.setdefault("OPS_SQLITE_DB", "ops-test.db")
os.environ.setdefault("AGENT_SQLITE_DB", "agent-test.db")

from fastapi import HTTPException, status  # noqa: E402

import openjiuwen_studio.core.manager.knowledge_base as kb_mod  # noqa: E402
from openjiuwen_studio.schemas.common import ResponseModel  # noqa: E402
from openjiuwen_studio.schemas.knowledge_base import KnowledgeBaseListRequest  # noqa: E402

USER = {"data": {"user_id_str": "u-1", "user_id": "u-1"}}
SPACE = "space-1"


class _FakeRepo:
    def __init__(self, list_result):
        self._list_result = list_result
        self.graph_calls = []

    def knowledge_base_list(self, kb, page, size):
        return self._list_result

    def has_graph_enhancement_documents(self, space_id, kb_id):
        self.graph_calls.append(("document", kb_id))
        return False

    def has_graph_enhancement_weblinks(self, space_id, kb_id):
        self.graph_calls.append(("weblink", kb_id))
        return True


def _ok_list_result(items, total=None):
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="ok",
        data={"items": items, "total": len(items) if total is None else total},
    )


def _req(space_id=SPACE):
    return KnowledgeBaseListRequest(space_id=space_id, page=1, size=10)


@pytest.fixture()
def space_check(monkeypatch):
    def install(behavior):
        def fake_check(space_id, current_user):
            if isinstance(behavior, Exception):
                raise behavior
            return behavior

        monkeypatch.setattr(kb_mod, "check_user_space", fake_check, raising=True)

    return install


@pytest.fixture()
def repo(monkeypatch):
    def install(list_result):
        fake = _FakeRepo(list_result)
        monkeypatch.setattr(kb_mod, "knowledge_base_repository", fake, raising=True)
        return fake

    return install


def test_access_denied_is_propagated(space_check, repo):
    """403 必须冒泡：吞掉后前端会显示成"该空间没有知识库"。"""
    space_check(HTTPException(status_code=403, detail="Access Denied"))
    repo(_ok_list_result([]))

    with pytest.raises(HTTPException) as excinfo:
        kb_mod.knowledge_base_list(_req(), USER)

    assert excinfo.value.status_code == 403


def test_unexpected_space_check_error_becomes_500(space_check, repo):
    space_check(RuntimeError("db down"))
    repo(_ok_list_result([]))

    with pytest.raises(HTTPException) as excinfo:
        kb_mod.knowledge_base_list(_req(), USER)

    assert excinfo.value.status_code == 500


def test_database_failure_is_reported_not_hidden(space_check, repo):
    space_check(object())
    repo(ResponseModel(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="query failed", data=None))

    res = kb_mod.knowledge_base_list(_req(), USER)

    assert res.code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert res.data is None


def test_success_path_maps_items(space_check, repo):
    space_check(object())
    fake = repo(
        _ok_list_result(
            [
                {"kb_id": "kb-1", "name": "doc kb", "config": {"type": "document"}},
                {"kb_id": "kb-2", "name": "link kb", "config": {"type": "weblink"}},
            ]
        )
    )

    res = kb_mod.knowledge_base_list(_req(), USER)

    assert res.code == status.HTTP_200_OK
    assert res.data["total"] == 2
    assert [item["id"] for item in res.data["items"]] == ["kb-1", "kb-2"]
    assert fake.graph_calls == [("document", "kb-1"), ("weblink", "kb-2")]
    assert res.data["items"][1]["has_graph_enhancement"] is True


def test_empty_space_id_still_returns_empty_list(space_check, repo):
    """前端在未选空间时会先调一次 list，这条路径保持 200 空列表。

    space_id 目前是 min_length=1 的必填字段，这里用 model_construct 直接构造，
    保证这段防御性分支的行为没有被本次改动带偏。
    """
    space_check(AssertionError("check_user_space 不应被调用"))
    repo(_ok_list_result([{"kb_id": "never", "name": "x"}]))
    req = KnowledgeBaseListRequest.model_construct(space_id="", page=1, size=10)

    res = kb_mod.knowledge_base_list(req, USER)

    assert res.code == status.HTTP_200_OK
    assert res.data["items"] == []
    assert res.data["total"] == 0
