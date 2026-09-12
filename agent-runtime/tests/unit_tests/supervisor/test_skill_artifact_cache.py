"""Security regression tests for the conversation skill artifact cache."""

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor as DefaultThreadPoolExecutor
import io
from multiprocessing import get_context
import os
from pathlib import Path
import stat
import threading
import time
import zipfile
from unittest.mock import AsyncMock

import pytest

import agent_runtime.supervisor.skill_artifact_cache as skill_artifact_cache_module
from agent_runtime.supervisor.skill_artifact_cache import (
    SkillArtifactCache,
    SkillArtifactError,
    SkillInstructionsMissingError,
)
from agent_runtime.supervisor.skill_model import SkillDescriptor


def descriptor(skill_id: str, version_id: str, name: str, object_key: str) -> SkillDescriptor:
    return SkillDescriptor(
        skill_id=skill_id,
        version_id=version_id,
        name=name,
        description=f"description-{name}",
        object_key=object_key,
    )


def zip_with(member: str, data: bytes, *, compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression) as archive:
        archive.writestr(member, data)
    return output.getvalue()


def skill_zip(name: str, body: str) -> bytes:
    markdown = f"---\nname: {name}\ndescription: test skill\n---\n\n{body}"
    return zip_with(f"{name}/SKILL.md", markdown.encode("utf-8"))


def zip_with_compression(name: str, body: bytes, compression: int) -> bytes:
    return zip_with(f"{name}/SKILL.md", body, compression=compression)


def set_zip_flags(payload: bytes, flags: int) -> bytes:
    patched = bytearray(payload)
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while (index := patched.find(signature, start)) >= 0:
            patched[index + flag_offset : index + flag_offset + 2] = flags.to_bytes(2, "little")
            start = index + len(signature)
    return bytes(patched)


def set_local_flags(payload: bytes, flags: int) -> bytes:
    patched = bytearray(payload)
    local_header = patched.index(b"PK\x03\x04")
    patched[local_header + 6 : local_header + 8] = flags.to_bytes(2, "little")
    return bytes(patched)


def set_central_flags(payload: bytes, flags: int) -> bytes:
    patched = bytearray(payload)
    central_header = patched.index(b"PK\x01\x02")
    patched[central_header + 8 : central_header + 10] = flags.to_bytes(2, "little")
    return bytes(patched)


def replace_raw_member_name(payload: bytes, replacement: bytes) -> bytes:
    patched = bytearray(payload)
    expected = b"x/SKILL.md"
    assert len(replacement) == len(expected)
    for signature, name_offset, name_length_offset in ((b"PK\x03\x04", 30, 26), (b"PK\x01\x02", 46, 28)):
        index = patched.index(signature)
        name_length = int.from_bytes(patched[index + name_length_offset : index + name_length_offset + 2], "little")
        assert name_length == len(expected)
        start = index + name_offset
        patched[start : start + name_length] = replacement
    return bytes(patched)


def corrupt_first_member(payload: bytes) -> bytes:
    corrupted = bytearray(payload)
    central_header = corrupted.index(b"PK\x01\x02")
    corrupted[central_header + 16] ^= 0x01
    return bytes(corrupted)


def set_first_central_file_size(payload: bytes, size: int) -> bytes:
    patched = bytearray(payload)
    central_header = patched.index(b"PK\x01\x02")
    patched[central_header + 24 : central_header + 28] = size.to_bytes(4, "little")
    return bytes(patched)


def set_first_central_compressed_size(payload: bytes, size: int) -> bytes:
    patched = bytearray(payload)
    central_header = patched.index(b"PK\x01\x02")
    patched[central_header + 20 : central_header + 24] = size.to_bytes(4, "little")
    return bytes(patched)


def overlap_second_member(payload: bytes) -> bytes:
    patched = bytearray(payload)
    first_central = patched.index(b"PK\x01\x02")
    second_central = patched.index(b"PK\x01\x02", first_central + 4)
    first_offset = patched[first_central + 42 : first_central + 46]
    patched[second_central + 42 : second_central + 46] = first_offset
    return bytes(patched)


def _load_in_separate_process(root: str, counter, ready, start, queue) -> None:
    async def downloader(_: str) -> bytes:
        with counter.get_lock():
            counter.value += 1
        await asyncio.sleep(0.15)
        return skill_zip("x", "process-safe")

    try:
        skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
        with ready.get_lock():
            ready.value += 1
        start.wait(timeout=5)
        result = asyncio.run(SkillArtifactCache(root, downloader=downloader).load_instructions(skill))
        queue.put(("ok", result))
    except Exception as error:  # pragma: no cover - assertion is made in parent process
        queue.put(("error", repr(error)))


@pytest.mark.asyncio
async def test_same_skill_version_downloads_once(tmp_path):
    downloader = AsyncMock(return_value=skill_zip("meeting-minutes", "正文标记"))
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    skill = descriptor("s1", "v1", "meeting-minutes", "u1/skills/s1/v1/a.zip")

    first = await cache.load_instructions(skill)
    second = await cache.load_instructions(skill)

    assert first == second
    assert first.endswith("正文标记")
    downloader.assert_awaited_once_with(skill.object_key)


@pytest.mark.asyncio
async def test_concurrent_same_skill_version_downloads_once(tmp_path):
    downloader = AsyncMock(return_value=skill_zip("meeting-minutes", "正文标记"))
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    skill = descriptor("s1", "v1", "meeting-minutes", "u1/skills/s1/v1/a.zip")

    loaded = await asyncio.gather(*[cache.load_instructions(skill) for _ in range(8)])

    assert len(set(loaded)) == 1
    assert loaded[0].endswith("正文标记")
    downloader.assert_awaited_once_with(skill.object_key)


@pytest.mark.asyncio
async def test_cancelling_a_waiting_lock_holder_does_not_leak_the_cache_lock(tmp_path):
    entered = asyncio.Event()
    release = asyncio.Event()
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")

    async def failing_downloader(_: str) -> bytes:
        entered.set()
        await release.wait()
        raise RuntimeError("simulated download failure")

    owner = SkillArtifactCache(tmp_path, downloader=failing_downloader)
    waiting = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "unused")))
    owner_task = asyncio.create_task(owner.load_instructions(skill))
    await entered.wait()
    cancelled_task = asyncio.create_task(waiting.load_instructions(skill))
    await asyncio.sleep(0.02)
    cancelled_task.cancel()
    release.set()

    with pytest.raises(RuntimeError, match="simulated download failure"):
        await owner_task
    with pytest.raises(asyncio.CancelledError):
        await cancelled_task

    recovered = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "recovered")))
    assert (await asyncio.wait_for(recovered.load_instructions(skill), timeout=1)).endswith("recovered")


@pytest.mark.asyncio
async def test_lock_waiters_do_not_starve_default_executor(tmp_path):
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0
    calls_lock = threading.Lock()
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")

    async def downloader(_: str) -> bytes:
        nonlocal calls
        with calls_lock:
            calls += 1
        entered.set()
        await release.wait()
        return skill_zip("x", "executor-safe")

    loop = asyncio.get_running_loop()
    previous_executor = loop._default_executor
    executor = DefaultThreadPoolExecutor(max_workers=2)
    loop.set_default_executor(executor)
    try:
        owner = asyncio.create_task(SkillArtifactCache(tmp_path, downloader=downloader).load_instructions(skill))
        await entered.wait()
        waiters = [
            asyncio.create_task(SkillArtifactCache(tmp_path, downloader=downloader).load_instructions(skill))
            for _ in range(3)
        ]
        await asyncio.sleep(0.03)
        release.set()
        results = await asyncio.wait_for(asyncio.gather(owner, *waiters), timeout=2)
    finally:
        loop.set_default_executor(previous_executor)
        executor.shutdown(wait=True)

    assert len(set(results)) == 1
    assert calls == 1


@pytest.mark.asyncio
async def test_double_cancelling_waiter_does_not_unlock_owner(tmp_path):
    entered = asyncio.Event()
    release = asyncio.Event()
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")

    async def owner_downloader(_: str) -> bytes:
        entered.set()
        await release.wait()
        return skill_zip("x", "owner")

    owner = asyncio.create_task(SkillArtifactCache(tmp_path, downloader=owner_downloader).load_instructions(skill))
    await entered.wait()
    waiter_downloader = AsyncMock(return_value=skill_zip("x", "waiter"))
    waiter = asyncio.create_task(SkillArtifactCache(tmp_path, downloader=waiter_downloader).load_instructions(skill))
    await asyncio.sleep(0.02)
    waiter.cancel()
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    waiter_downloader.assert_not_awaited()
    release.set()
    assert (await owner).endswith("owner")
    assert (await SkillArtifactCache(tmp_path, downloader=waiter_downloader).load_instructions(skill)).endswith("owner")


@pytest.mark.asyncio
async def test_cancelled_acquire_releases_a_late_success_without_second_await():
    """A second cancellation cannot prevent cleanup of an executor attempt."""
    executor_entered = threading.Event()
    unblock_executor = threading.Event()
    released = threading.Event()

    class LateLock:
        def try_acquire(self):
            return True

        def release(self):
            released.set()

    def block_executor():
        executor_entered.set()
        unblock_executor.wait(timeout=2)

    skill_artifact_cache_module._LOCK_EXECUTOR.submit(block_executor)
    await asyncio.to_thread(executor_entered.wait, 1)
    task = asyncio.create_task(skill_artifact_cache_module._acquire_lock(LateLock()))
    await asyncio.sleep(0)
    task.cancel()
    unblock_executor.set()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    heartbeat = asyncio.Event()
    asyncio.get_running_loop().call_soon(heartbeat.set)
    await asyncio.wait_for(heartbeat.wait(), timeout=0.1)
    assert await asyncio.to_thread(released.wait, 1)


@pytest.mark.asyncio
async def test_cancelled_acquire_never_reads_a_pending_attempt_result(monkeypatch):
    """Completion callback, not a cancelling task, owns a late lock result."""
    released = 0

    class CountingFuture(Future):
        result_calls = 0

        def result(self, *args, **kwargs):
            self.result_calls += 1
            return super().result(*args, **kwargs)

    class LateLock:
        def try_acquire(self):
            return True

        def release(self):
            nonlocal released
            released += 1

    class ControlledExecutor:
        def __init__(self, attempt):
            self.attempt = attempt
            self.calls = 0

        def submit(self, function, *args):
            self.calls += 1
            if self.calls == 1:
                return self.attempt
            completed = Future()
            try:
                completed.set_result(function(*args))
            except BaseException as error:  # pragma: no cover - test helper
                completed.set_exception(error)
            return completed

    attempt = CountingFuture()
    monkeypatch.setattr(skill_artifact_cache_module, "_LOCK_EXECUTOR", ControlledExecutor(attempt))
    task = asyncio.create_task(skill_artifact_cache_module._acquire_lock(LateLock()))
    await asyncio.sleep(0)
    task.cancel()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert attempt.result_calls == 0

    attempt.set_result(True)
    assert released == 1


@pytest.mark.asyncio
async def test_cancelling_outer_task_keeps_lock_until_background_stage_finishes(tmp_path, monkeypatch):
    entered_stage = threading.Event()
    release_stage = threading.Event()
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
    first = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "first")))
    original_stage = first._stage_and_publish

    def paused_stage(*args, **kwargs):
        entered_stage.set()
        release_stage.wait(timeout=2)
        return original_stage(*args, **kwargs)

    monkeypatch.setattr(first, "_stage_and_publish", paused_stage)
    first_task = asyncio.create_task(first.load_instructions(skill))
    await asyncio.to_thread(entered_stage.wait, 1)
    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task

    second_downloader = AsyncMock(return_value=skill_zip("x", "second"))
    second_task = asyncio.create_task(SkillArtifactCache(tmp_path, downloader=second_downloader).load_instructions(skill))
    await asyncio.sleep(0.03)
    second_downloader.assert_not_awaited()
    release_stage.set()
    assert (await asyncio.wait_for(second_task, timeout=2)).endswith("first")


@pytest.mark.asyncio
async def test_cancelling_inner_stage_task_keeps_lock_until_sync_stage_finishes(tmp_path, monkeypatch):
    """A loop cancelling its wrapper must not release a running stage worker."""
    entered_stage = threading.Event()
    release_stage = threading.Event()
    created_tasks = []
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
    first = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "first")))
    original_stage = first._stage_and_publish
    original_create_task = asyncio.create_task

    def paused_stage(*args, **kwargs):
        entered_stage.set()
        release_stage.wait(timeout=2)
        return original_stage(*args, **kwargs)

    def track_task(coro, *args, **kwargs):
        task = original_create_task(coro, *args, **kwargs)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(first, "_stage_and_publish", paused_stage)
    monkeypatch.setattr(asyncio, "create_task", track_task)
    first_task = original_create_task(first.load_instructions(skill))
    await asyncio.to_thread(entered_stage.wait, 1)
    assert created_tasks
    created_tasks[0].cancel()
    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task

    second_downloader = AsyncMock(return_value=skill_zip("x", "second"))
    second_task = original_create_task(
        SkillArtifactCache(tmp_path, downloader=second_downloader).load_instructions(skill)
    )
    await asyncio.sleep(0.03)
    second_downloader.assert_not_awaited()
    release_stage.set()
    assert (await asyncio.wait_for(second_task, timeout=2)).endswith("first")


def test_lock_permission_failure_releases_local_stripe_for_recovery(tmp_path, monkeypatch):
    """Every failure after local acquisition must make the stripe reusable."""
    cache_key = "0" * 64
    lock_dir = tmp_path / ".locks"
    original_mkdir = Path.mkdir
    failed = False

    def reject_once(path, *args, **kwargs):
        nonlocal failed
        if path == lock_dir and not failed:
            failed = True
            raise PermissionError("blocked")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", reject_once)
    with pytest.raises(SkillArtifactError, match="cache lock failed"):
        skill_artifact_cache_module._CacheFileLock(tmp_path, cache_key).try_acquire()

    recovered = skill_artifact_cache_module._CacheFileLock(tmp_path, cache_key)
    assert recovered.try_acquire()
    recovered.release()


@pytest.mark.asyncio
async def test_lock_backoff_uses_injectable_bounded_jitter(monkeypatch):
    class EventuallyAvailableLock:
        attempts = 0

        def try_acquire(self):
            self.attempts += 1
            return self.attempts == 2

        def release(self):
            pass

    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(skill_artifact_cache_module, "_BACKOFF_RANDOM", lambda: 1.0)
    monkeypatch.setattr(asyncio, "sleep", record_sleep)
    await skill_artifact_cache_module._acquire_lock(EventuallyAvailableLock())

    assert delays == [pytest.approx(0.00625)]


@pytest.mark.asyncio
async def test_lock_backoff_jitter_never_exceeds_the_declared_cap(monkeypatch):
    class EventuallyAvailableLock:
        attempts = 0

        def try_acquire(self):
            self.attempts += 1
            return self.attempts == 6

        def release(self):
            pass

    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(skill_artifact_cache_module, "_BACKOFF_RANDOM", lambda: 1.0)
    monkeypatch.setattr(asyncio, "sleep", record_sleep)
    await skill_artifact_cache_module._acquire_lock(EventuallyAvailableLock())

    assert len(delays) == 5
    assert max(delays) <= 0.05


@pytest.mark.asyncio
async def test_new_version_uses_new_cache_entry(tmp_path):
    downloader = AsyncMock(side_effect=[skill_zip("x", "v1"), skill_zip("x", "v2")])
    cache = SkillArtifactCache(tmp_path, downloader=downloader)

    first = await cache.load_instructions(
        descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
    )
    second = await cache.load_instructions(
        descriptor("s1", "v2", "x", "u/skills/s1/v2/a.zip")
    )
    assert first != second
    assert len([path for path in tmp_path.iterdir() if path.name != ".locks"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("member", ["../escape", "/absolute", "C:/escape"])
async def test_path_traversal_is_rejected(tmp_path, member):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=zip_with(member, b"x")))

    with pytest.raises(SkillArtifactError, match="unsafe zip path"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_object_key_outside_skill_version(tmp_path):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock())
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v2/a.zip")

    with pytest.raises(SkillArtifactError, match="unsafe object key"):
        await cache.load_instructions(skill)


@pytest.mark.asyncio
async def test_rejects_nested_zip(tmp_path):
    nested = zip_with("inner.zip", skill_zip("inner", "x"))
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        archive.writestr("x/inner.zip", nested)
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="nested zip"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_nested_zip_without_zip_suffix(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        archive.writestr("x/embedded-data", skill_zip("inner", "x"))
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="nested zip"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_self_extracting_nested_zip_without_zip_suffix(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        archive.writestr("x/embedded-data", b"SFX-prefix" + skill_zip("inner", "x"))
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="nested zip"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_symbolic_link(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        link = zipfile.ZipInfo("x/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "target")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="unsafe zip member"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_more_than_500_entries(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        for index in range(500):
            archive.writestr(f"x/{index}.txt", b"x")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="too many zip entries"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_archive_larger_than_10_mib(tmp_path):
    payload = zip_with("x/SKILL.md", os.urandom(10 * 1024 * 1024 + 1), compression=zipfile.ZIP_STORED)
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))

    with pytest.raises(SkillArtifactError, match="archive too large"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_uncompressed_content_larger_than_100_mib(tmp_path):
    payload = zip_with("x/SKILL.md", b"x" * (100 * 1024 * 1024 + 1))
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))

    with pytest.raises(SkillArtifactError, match="uncompressed content too large"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_path_deeper_than_10_levels(tmp_path):
    member = "x/" + "/".join(["nested"] * 10) + "/SKILL.md"
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=zip_with(member, b"body")))

    with pytest.raises(SkillArtifactError, match="zip path too deep"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_requires_a_root_skill_markdown(tmp_path):
    cache = SkillArtifactCache(
        tmp_path, downloader=AsyncMock(return_value=zip_with("x/readme.md", b"body"))
    )

    with pytest.raises(SkillInstructionsMissingError):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_unique_root_skill_markdown_is_not_a_missing_instruction_error(tmp_path):
    cache = SkillArtifactCache(
        tmp_path, downloader=AsyncMock(return_value=zip_with("x/SKILL.md", b"body"))
    )

    assert await cache.load_instructions(
        descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
    ) == "body"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "members",
    [
        [("x/SKILL.md", b"one"), ("y/SKILL.md", b"two")],
        [("x/nested/SKILL.md", b"nested")],
    ],
)
async def test_multiple_or_nested_skill_markdown_is_not_missing_error(tmp_path, members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, body in members:
            archive.writestr(name, body)
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=output.getvalue()))

    with pytest.raises(SkillArtifactError) as raised:
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))
    assert not isinstance(raised.value, SkillInstructionsMissingError)


@pytest.mark.asyncio
async def test_rejects_multiple_root_skill_markdown_files(tmp_path):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"one")
        archive.writestr("y/SKILL.md", b"two")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=output.getvalue()))

    with pytest.raises(SkillArtifactError, match="exactly one root SKILL.md"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_additional_nested_skill_markdown_file(tmp_path):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"one")
        archive.writestr("x/nested/SKILL.md", b"two")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=output.getvalue()))

    with pytest.raises(SkillArtifactError, match="exactly one root SKILL.md"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_failed_download_does_not_publish_or_poison_cache(tmp_path):
    downloader = AsyncMock(side_effect=[zip_with("../escape", b"x"), skill_zip("x", "recovered")])
    cache = SkillArtifactCache(tmp_path, downloader=downloader)
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")

    with pytest.raises(SkillArtifactError, match="unsafe zip path"):
        await cache.load_instructions(skill)

    assert (await cache.load_instructions(skill)).endswith("recovered")
    assert [path for path in tmp_path.iterdir() if path.name != ".locks"] == [tmp_path / skill.cache_key]
    assert downloader.await_count == 2


@pytest.mark.asyncio
async def test_separate_cache_instances_reuse_existing_published_artifact(tmp_path):
    downloader = AsyncMock(return_value=skill_zip("x", "published"))
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")
    first_cache = SkillArtifactCache(tmp_path, downloader=downloader)
    second_cache = SkillArtifactCache(tmp_path, downloader=downloader)

    first = await first_cache.load_instructions(skill)
    second = await second_cache.load_instructions(skill)

    assert first == second
    assert first.endswith("published")
    downloader.assert_awaited_once_with(skill.object_key)


def test_threaded_cache_instances_download_and_publish_once(tmp_path, monkeypatch):
    class SharedDownloader:
        def __init__(self) -> None:
            self.calls = 0
            self.lock = threading.Lock()

        async def __call__(self, _: str) -> bytes:
            with self.lock:
                self.calls += 1
            await asyncio.sleep(0.05)
            return skill_zip("x", "thread-safe")

    downloader = SharedDownloader()
    replace_calls = 0
    replace_lock = threading.Lock()
    original_replace = skill_artifact_cache_module.os.replace

    def count_replace(source, target):
        nonlocal replace_calls
        with replace_lock:
            replace_calls += 1
        return original_replace(source, target)

    monkeypatch.setattr(skill_artifact_cache_module.os, "replace", count_replace)
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip")

    def load_in_own_loop() -> str:
        return asyncio.run(SkillArtifactCache(tmp_path, downloader=downloader).load_instructions(skill))

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: load_in_own_loop(), range(2)))

    assert results[0] == results[1]
    assert downloader.calls == 1
    assert replace_calls == 1
    assert len(skill_artifact_cache_module._LOCAL_LOCK_STRIPES) == skill_artifact_cache_module._LOCK_STRIPES


def test_process_cache_instances_download_once(tmp_path):
    context = get_context("spawn")
    counter = context.Value("i", 0)
    ready = context.Value("i", 0)
    start = context.Event()
    queue = context.Queue()
    processes = [
        context.Process(target=_load_in_separate_process, args=(str(tmp_path), counter, ready, start, queue))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    deadline = time.monotonic() + 5
    while ready.value != len(processes) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready.value == len(processes)
    start.set()
    for process in processes:
        process.join(timeout=10)

    assert all(process.exitcode == 0 for process in processes)
    results = [queue.get(timeout=2) for _ in processes]
    assert all(status == "ok" and result.endswith("process-safe") for status, result in results), results
    assert counter.value == 1


@pytest.mark.asyncio
async def test_zip_processing_does_not_block_the_event_loop(tmp_path, monkeypatch):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "body")))
    original_extract = cache._extract_and_validate

    def slow_extract(*args, **kwargs):
        time.sleep(0.1)
        return original_extract(*args, **kwargs)

    monkeypatch.setattr(cache, "_extract_and_validate", slow_extract)
    task = asyncio.create_task(
        cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))
    )
    await asyncio.sleep(0.02)

    assert not task.done()
    await task


@pytest.mark.asyncio
@pytest.mark.parametrize("compression", [zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA])
async def test_rejects_unsupported_zip_compression(tmp_path, compression):
    cache = SkillArtifactCache(
        tmp_path, downloader=AsyncMock(return_value=zip_with_compression("x", b"body", compression))
    )

    with pytest.raises(SkillArtifactError, match="unsupported zip compression"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
@pytest.mark.parametrize("flags", [0x01, 0x20, 0x40])
async def test_rejects_encrypted_strong_or_patched_zip_members(tmp_path, flags):
    cache = SkillArtifactCache(
        tmp_path, downloader=AsyncMock(return_value=set_zip_flags(skill_zip("x", "body"), flags))
    )

    with pytest.raises(SkillArtifactError, match="unsafe zip flags"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    set_local_flags(skill_zip("x", "body"), 0x01),
    set_local_flags(skill_zip("x", "body"), 0x20),
    set_local_flags(skill_zip("x", "body"), 0x40),
    set_local_flags(skill_zip("x", "body"), 0x2000),
    set_central_flags(skill_zip("x", "body"), 0x01),
])
async def test_rejects_local_or_central_unsafe_zip_flags(tmp_path, payload):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))

    with pytest.raises(SkillArtifactError, match="unsafe zip flags"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_accepts_consistent_data_descriptor_flag(tmp_path):
    payload = set_zip_flags(skill_zip("x", "body"), 0x08)
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))

    assert (await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))).endswith("body")


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_name", [b"x\\SKILL.md", b"x/SKILL\x00md"])
async def test_rejects_raw_normalized_or_truncated_zip_member_names(tmp_path, raw_name):
    payload = replace_raw_member_name(skill_zip("x", "body"), raw_name)
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload))

    with pytest.raises(SkillArtifactError, match="unsafe zip path"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_rejects_high_compression_ratio(tmp_path):
    cache = SkillArtifactCache(
        tmp_path,
        downloader=AsyncMock(return_value=zip_with_compression("x", b"x" * (1024 * 1024), zipfile.ZIP_DEFLATED)),
    )

    with pytest.raises(SkillArtifactError, match="zip compression ratio too high"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_crc_error_is_wrapped_as_skill_artifact_error(tmp_path):
    cache = SkillArtifactCache(
        tmp_path, downloader=AsyncMock(return_value=corrupt_first_member(skill_zip("x", "body")))
    )

    with pytest.raises(SkillArtifactError, match="invalid skill archive"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_forged_declared_member_size_is_wrapped_as_skill_artifact_error(tmp_path):
    cache = SkillArtifactCache(
        tmp_path,
        downloader=AsyncMock(return_value=set_first_central_file_size(skill_zip("x", "body"), 1)),
    )

    with pytest.raises(SkillArtifactError, match="invalid skill archive"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_forged_compressed_member_size_is_rejected_before_extraction(tmp_path):
    cache = SkillArtifactCache(
        tmp_path,
        downloader=AsyncMock(
            return_value=set_first_central_compressed_size(skill_zip("x", "body"), 20 * 1024 * 1024)
        ),
    )

    with pytest.raises(SkillArtifactError, match="invalid skill archive"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_overlapping_zip_members_are_wrapped_as_skill_artifact_error(tmp_path):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        archive.writestr("x/extra.txt", b"extra")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=overlap_second_member(payload.getvalue())))

    with pytest.raises(SkillArtifactError, match="invalid skill archive|unsafe zip path"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "member",
    ["x/NUL", "x/nul.txt", "x/COM1.", "x/conout$ ", "x/NUL .txt", "x/COM1 .foo", "x/COM¹.txt", "x/LPT³.log"],
)
async def test_rejects_windows_reserved_device_names(tmp_path, member):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        archive.writestr(member, b"x")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="unsafe zip path"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
@pytest.mark.parametrize("member, is_directory_mode", [("x/dir", True), ("x/dir/", False)])
async def test_rejects_directory_type_inconsistency(tmp_path, member, is_directory_mode):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("x/SKILL.md", b"body")
        malformed = zipfile.ZipInfo(member)
        malformed.create_system = 3
        malformed.external_attr = (
            (stat.S_IFDIR if is_directory_mode else stat.S_IFREG) | 0o755
        ) << 16
        archive.writestr(malformed, b"not-a-directory")
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=payload.getvalue()))

    with pytest.raises(SkillArtifactError, match="unsafe zip member"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["u/./skills/s1/v1/a.zip", "u//skills/s1/v1/a.zip", "u/skills/s1/v1/a.zip/", "u/skills/s1/v1/\x01a.zip"])
async def test_rejects_noncanonical_or_control_object_keys(tmp_path, key):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock())

    with pytest.raises(SkillArtifactError, match="unsafe object key"):
        await cache.load_instructions(descriptor("s1", "v1", "x", key))


@pytest.mark.asyncio
@pytest.mark.parametrize("member", ["x/./SKILL.md", "x//SKILL.md", "x/SKILL.md/"])
async def test_rejects_noncanonical_zip_member_paths(tmp_path, member):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=zip_with(member, b"body")))

    with pytest.raises(SkillArtifactError, match="unsafe zip"):
        await cache.load_instructions(descriptor("s1", "v1", "x", "u/skills/s1/v1/a.zip"))


@pytest.mark.asyncio
async def test_accepts_manager_object_key_with_colon_filename(tmp_path):
    cache = SkillArtifactCache(tmp_path, downloader=AsyncMock(return_value=skill_zip("x", "body")))
    skill = descriptor("s1", "v1", "x", "u/skills/s1/v1/meeting:notes.zip")

    assert (await cache.load_instructions(skill)).endswith("body")
