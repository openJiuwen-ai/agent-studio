# -*- coding: UTF-8 -*-
"""issue 1752 AC3: FlowApi 工具错误语义（execute_tool span ERROR）。"""
import pytest

from jiuwen.extension.workflow_node.flow_api import (
    _ErrorRaisingApi,
    _raise_if_api_error,
)
from jiuwen.common.exception import JiuWenBaseException


class _FakeApi:
    def __init__(self, result):
        self._result = result
        self.card = type("Card", (), {"name": "healthtag"})()

    async def ainvoke(self, inputs, **kwargs):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result

    async def astream(self, inputs, **kwargs):
        if isinstance(self._result, Exception):
            raise self._result
        for item in self._result:
            yield item


def test_success_response_not_raised():
    _raise_if_api_error({"data": {"ok": 1}, "errCode": 0, "errMessage": ""})


def test_non_dict_output_not_raised():
    _raise_if_api_error("plain")


def test_error_response_raised_with_code():
    with pytest.raises(JiuWenBaseException) as exc:
        _raise_if_api_error({"errCode": 105011, "errMessage": "http code error"})
    assert "105011" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_adapter_success_passthrough_and_card_forwarded():
    api = _ErrorRaisingApi(_FakeApi({"data": {}, "errCode": 0}))
    out = await api.invoke({"q": 1})
    assert out["errCode"] == 0
    assert api.card.name == "healthtag"


@pytest.mark.asyncio
async def test_adapter_error_response_raised():
    api = _ErrorRaisingApi(_FakeApi({"errCode": 105011, "errMessage": "boom"}))
    with pytest.raises(JiuWenBaseException):
        await api.invoke({})


@pytest.mark.asyncio
async def test_adapter_astream_error_frame_raised():
    api = _ErrorRaisingApi(_FakeApi([{"errCode": 0}, {"errCode": 105011}]))
    collected = []
    with pytest.raises(JiuWenBaseException):
        async for item in api.astream({}):
            collected.append(item)
    assert len(collected) == 1