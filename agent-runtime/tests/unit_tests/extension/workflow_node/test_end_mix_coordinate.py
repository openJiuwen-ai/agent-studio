# coding: utf-8
# pylint: disable=protected-access  # Unit tests intentionally verify End internals.

import asyncio
from typing import AsyncGenerator

import pytest
from jiuwen.extension.workflow_node.end import End


async def _recording_generator(consumed: list[str]) -> AsyncGenerator[str, None]:
    for frame in ("A", "B", "C"):
        consumed.append(frame)
        yield frame


async def _empty_generator() -> AsyncGenerator[str, None]:
    return
    yield  # pragma: no cover


async def _value_generator(value: str) -> AsyncGenerator[str, None]:
    yield value


def _mixed_end() -> End:
    end = End({"responseTemplate": "{{result1}}，{{result2}}"})
    end.set_expect_mix(True)
    end.set_mix()
    return end


@pytest.mark.asyncio
async def test_mix_coordinate_never_blocks_or_preconsumes_either_input_lane():
    end = _mixed_end()
    consumed: list[str] = []
    original = _recording_generator(consumed)

    batch_inputs, _, batch_is_renderer = await asyncio.wait_for(
        end._mix_coordinate("batch", {"batch_value": "ready"}, {}),
        timeout=0.05,
    )
    stream_inputs, _, stream_is_renderer = await asyncio.wait_for(
        end._mix_coordinate("stream", {"result1": original}, {}),
        timeout=0.05,
    )

    assert batch_is_renderer is True
    assert stream_is_renderer is True
    assert batch_inputs == {"batch_value": "ready"}
    assert stream_inputs["result1"] is original
    assert consumed == []


class _TemplateSession:
    @staticmethod
    def get_component_id() -> str:
        return "node_end"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        (
            {
                "result1": _value_generator("result1"),
                "result2": _empty_generator(),
            },
            "result1，",
        ),
        (
            {
                "result1": _empty_generator(),
                "result2": _value_generator("result2"),
            },
            "，result2",
        ),
    ],
)
async def test_template_keeps_literal_comma_for_inactive_branch(inputs, expected):
    end = End({"responseTemplate": "{{result1}}，{{result2}}"})

    frames = []
    async for frame in end._template.render_stream(
        inputs, _TemplateSession(), timeout=0.01
    ):
        frames.append(frame["data"])

    assert "".join(frames) == expected
