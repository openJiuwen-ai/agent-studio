import pytest

from agent_runtime.extension.workflow_node.kb_adapter.factory import KBAdapterFactory
from agent_runtime.extension.workflow_node.kb_adapter.base import KBServiceAdapter
from agent_runtime.extension.workflow_node.kb_adapter.lakesearch_adapter import (
    LakeSearchAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.koosearch_adapter import (
    KooSearchAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.ragflow_adapter import RagFlowAdapter
from agent_runtime.extension.workflow_node.kb_adapter.general_kb_adapter import (
    GeneralKBAdapter,
)
from agent_runtime.extension.workflow_node.kb_adapter.openjiuwen_adapter import (
    OpenJiuwenKBAdapter,
)


@pytest.mark.parametrize(
    "connector_type,expected_cls",
    [
        ("LakeSearch", LakeSearchAdapter),
        ("LakeSearchInside", LakeSearchAdapter),
        ("KooSearch", KooSearchAdapter),
        ("KooSearchInside", KooSearchAdapter),
        ("Ragflow", RagFlowAdapter),
        ("General", GeneralKBAdapter),
        ("Custom", LakeSearchAdapter),  # Custom 复用 LakeSearch
        ("OpenJiuwen", OpenJiuwenKBAdapter),
    ],
)
def test_create_returns_correct_adapter(connector_type, expected_cls):
    adapter = KBAdapterFactory.create(connector_type)
    assert isinstance(adapter, expected_cls)
    assert isinstance(adapter, KBServiceAdapter)


@pytest.mark.parametrize(
    "connector_type,expected_cls",
    [
        ("lakesearch", LakeSearchAdapter),
        ("KOOSEARCH", KooSearchAdapter),
        ("ragflow", RagFlowAdapter),
        ("GENERAL", GeneralKBAdapter),
        ("openjiuwen", OpenJiuwenKBAdapter),
    ],
)
def test_create_is_case_insensitive(connector_type, expected_cls):
    assert isinstance(KBAdapterFactory.create(connector_type), expected_cls)


def test_create_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported connector type"):
        KBAdapterFactory.create("NoSuchConnector")
