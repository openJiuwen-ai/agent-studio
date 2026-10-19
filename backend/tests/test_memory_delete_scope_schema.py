from openjiuwen_studio.schemas.memory import DeleteScopeLongtermMem


def test_delete_scope_longterm_mem_exposes_user_id_for_authorization():
    """The /memory/delete_longterm_mem_by_scope handler authorizes the caller
    with check_user_space(req.user_id, current_user). Every sibling memory
    request schema (DeleteLongtermMem, DeleteVariable, ...) therefore carries a
    user_id field. DeleteScopeLongtermMem must expose it too, otherwise the
    handler raises AttributeError and the endpoint always returns HTTP 500.
    """
    fields = DeleteScopeLongtermMem.model_fields
    assert "user_id" in fields, "DeleteScopeLongtermMem must expose user_id"

    req = DeleteScopeLongtermMem(scope_id="scope-1", user_id="space-1")
    assert req.scope_id == "scope-1"
    assert req.user_id == "space-1"
