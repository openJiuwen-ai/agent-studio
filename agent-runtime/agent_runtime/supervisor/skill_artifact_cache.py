"""Safe, version-isolated cache for conversation skill ZIP artifacts."""

import asyncio
import errno
from collections.abc import Awaitable, Callable
import io
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import random
import re
import shutil
import stat
import struct
import tempfile
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor

from agent_runtime.common.config import settings
from storage import get_storage_provider

from .skill_model import SkillDescriptor


MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 500
MAX_PATH_DEPTH = 10
MAX_COMPRESSION_RATIO = 100
_FORBIDDEN_ZIP_FLAGS = 0x01 | 0x20 | 0x40
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_WORKER_LIMIT = threading.BoundedSemaphore(2)
_LOCK_STRIPES = 64
_LOCAL_LOCK_STRIPES = [threading.Lock() for _ in range(_LOCK_STRIPES)]
_LOCK_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="skill-lock")
_STAGE_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="skill-stage")
_BACKOFF_RANDOM = random.random
_LOCK_BACKOFF_CAP_SECONDS = 0.05
_LOCAL_HEADER = struct.Struct("<IHHHHHIIIHH")
_LOCAL_HEADER_SIGNATURE = 0x04034B50
_ALLOWED_ZIP_FLAGS = 0x02 | 0x04 | 0x08 | 0x800


class SkillArtifactError(ValueError):
    """Raised when a skill artifact cannot safely enter the local cache."""


class SkillInstructionsMissingError(SkillArtifactError):
    """Raised only when an otherwise valid archive contains no SKILL.md at all."""


Downloader = Callable[[str], Awaitable[bytes]]


async def _download(object_key: str) -> bytes:
    provider = get_storage_provider()
    return await provider.get_object_bytes(object_key)


class _CacheFileLock:
    """A cache-key lock shared by cache instances and operating-system processes."""

    def __init__(self, root: Path, cache_key: str) -> None:
        self._root = root
        self._cache_key = cache_key
        self._stripe = int(cache_key[:8], 16) % _LOCK_STRIPES
        self._local_lock = _LOCAL_LOCK_STRIPES[self._stripe]
        self._file = None
        self._local_owned = False
        self._locked = False

    def try_acquire(self) -> bool:
        if not self._local_lock.acquire(blocking=False):
            return False
        self._local_owned = True
        try:
            lock_dir = self._root / ".locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_path = lock_dir / f"stripe-{self._stripe:02d}.lock"
            self._file = lock_path.open("a+b")
            self._file.seek(0, os.SEEK_END)
            if self._file.tell() == 0:
                self._file.write(b"\0")
                self._file.flush()
            self._file.seek(0)
            if not self._try_lock_file():
                self._file.close()
                self._file = None
                self._local_owned = False
                self._local_lock.release()
                return False
            self._locked = True
            return True
        except OSError as error:
            self.release()
            raise SkillArtifactError("cache lock failed") from error

    def release(self) -> None:
        local_owned = self._local_owned
        try:
            if self._file is not None:
                self._file.close()
        finally:
            self._file = None
            self._locked = False
            self._local_owned = False
            if local_owned:
                self._local_lock.release()

    def _try_lock_file(self) -> bool:
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                    return False
                raise
        else:
            import fcntl

            try:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except OSError as error:
                if error.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                    return False
                raise

    def _unlock_file(self) -> None:
        if os.name == "nt":
            import msvcrt

            self._file.seek(0)
            self._file.seek(self._stripe)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)


class _LockLease:
    """Make lock release idempotent across coroutine and worker lifetimes."""

    def __init__(self, lock: _CacheFileLock) -> None:
        self._lock = lock
        self._state_lock = threading.Lock()
        self._stage_started = False
        self._released = False

    def begin_stage(self) -> None:
        with self._state_lock:
            if self._released:
                raise RuntimeError("cache lock already released")
            self._stage_started = True

    def abort_stage(self) -> None:
        with self._state_lock:
            self._stage_started = False

    def release_before_stage(self) -> None:
        with self._state_lock:
            if self._stage_started or self._released:
                return
            self._released = True
        self._lock.release()

    def release_after_stage(self) -> None:
        with self._state_lock:
            if self._released:
                return
            self._released = True
        self._lock.release()


class SkillArtifactCache:
    """Download, validate, and atomically cache one skill version at a time."""

    def __init__(self, root: Path, *, downloader: Downloader) -> None:
        self._root = Path(root)
        self._downloader = downloader

    async def load_instructions(self, skill: SkillDescriptor) -> str:
        """Return the sole root ``SKILL.md`` after safely caching ``skill``."""
        self._validate_object_key(skill)
        cache_dir = self._root / skill.cache_key
        cached = await self._run_blocking(self._read_cached_instructions, cache_dir)
        if cached is not None:
            return cached

        lock = _CacheFileLock(self._root, skill.cache_key)
        await _acquire_lock(lock)
        lease = _LockLease(lock)
        work = asyncio.create_task(self._load_while_locked(skill, cache_dir, lease))
        work.add_done_callback(lambda _: _schedule_release(lease))
        try:
            return await asyncio.shield(work)
        except asyncio.CancelledError:
            raise

    async def _load_while_locked(
        self, skill: SkillDescriptor, cache_dir: Path, lease: _LockLease
    ) -> str:
        cached = await self._run_blocking(self._read_cached_instructions, cache_dir)
        if cached is not None:
            return cached
        artifact = await self._downloader(skill.object_key)
        if not isinstance(artifact, bytes) or len(artifact) > MAX_ARCHIVE_BYTES:
            raise SkillArtifactError("archive too large")
        lease.begin_stage()
        try:
            stage = _STAGE_EXECUTOR.submit(
                _run_limited, self._stage_and_release, artifact, cache_dir, lease
            )
        except BaseException:
            lease.abort_stage()
            raise
        return await asyncio.shield(asyncio.wrap_future(stage))

    @staticmethod
    async def _run_blocking(function, *args):
        return await asyncio.to_thread(_run_limited, function, *args)

    @staticmethod
    def _validate_object_key(skill: SkillDescriptor) -> None:
        key = skill.object_key
        if not key or "\\" in key:
            raise SkillArtifactError("unsafe object key")
        parts = _raw_posix_parts(key, allow_directory=False, local_path=False)
        if PureWindowsPath(key).is_absolute() or re.match(r"^[A-Za-z]:", key):
            raise SkillArtifactError("unsafe object key")
        expected = ("skills", skill.skill_id, skill.version_id)
        if not all(expected) or any("/" in part or "\\" in part for part in expected):
            raise SkillArtifactError("unsafe object key")
        if not any(tuple(parts[index : index + 3]) == expected for index in range(len(parts) - 2)):
            raise SkillArtifactError("unsafe object key")

    @staticmethod
    def _read_cached_instructions(cache_dir: Path) -> str | None:
        instruction_file = cache_dir / "SKILL.md"
        if not instruction_file.is_file() or instruction_file.is_symlink():
            return None
        try:
            return instruction_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SkillArtifactError("cached SKILL.md cannot be read") from error

    def _stage_and_publish(self, artifact: bytes, cache_dir: Path) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{cache_dir.name}.", dir=self._root))
        staged_dir = temp_dir / "artifact"
        try:
            instructions = self._extract_and_validate(artifact, staged_dir)
            cached = self._read_cached_instructions(cache_dir)
            if cached is not None:
                return cached
            if cache_dir.exists() or cache_dir.is_symlink():
                raise SkillArtifactError("invalid existing cache entry")
            try:
                os.replace(staged_dir, cache_dir)
            except OSError as error:
                cached = self._read_cached_instructions(cache_dir)
                if cached is not None:
                    return cached
                raise SkillArtifactError("cache publish failed") from error
            return instructions
        except SkillArtifactError:
            raise
        except (OSError, EOFError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
            raise SkillArtifactError("invalid skill archive") from error
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _stage_and_release(
        self, artifact: bytes, cache_dir: Path, lease: _LockLease
    ) -> str:
        """Release only from the synchronous stage worker's real completion."""
        try:
            return self._stage_and_publish(artifact, cache_dir)
        finally:
            lease.release_after_stage()

    def _extract_and_validate(self, artifact: bytes, staged_dir: Path) -> str:
        try:
            archive = zipfile.ZipFile(io.BytesIO(artifact))
        except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as error:
            raise SkillArtifactError("invalid skill archive") from error

        with archive:
            members = archive.infolist()
            if len(members) > MAX_ZIP_ENTRIES:
                raise SkillArtifactError("too many zip entries")
            validated_members = [
                (member, self._validate_member(member, artifact)) for member in members
            ]
            skill_members = [
                member for member, path in validated_members
                if not member.is_dir() and path.name == "SKILL.md" and len(path.parts) == 2
            ]
            all_skills = sum(
                not member.is_dir() and path.name == "SKILL.md" for member, path in validated_members
            )
            if all_skills == 0:
                raise SkillInstructionsMissingError("root SKILL.md is missing")
            if len(skill_members) != 1 or all_skills != 1:
                raise SkillArtifactError("exactly one root SKILL.md is required")

            root_name: str | None = None
            declared_total = 0
            for member, path in validated_members:
                if root_name is None:
                    root_name = path.parts[0]
                elif path.parts[0] != root_name:
                    raise SkillArtifactError("unsafe zip path")
                if member.is_dir():
                    continue
                declared_total += member.file_size
                if declared_total > MAX_UNCOMPRESSED_BYTES:
                    raise SkillArtifactError("uncompressed content too large")

            staged_dir.mkdir()
            actual_total = 0
            instructions: str | None = None
            for member, path in validated_members:
                if member.is_dir():
                    continue
                target = staged_dir.joinpath(*path.parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with archive.open(member) as source, target.open("xb") as destination:
                    while chunk := source.read(64 * 1024):
                        written += len(chunk)
                        actual_total += len(chunk)
                        if written > MAX_FILE_BYTES or actual_total > MAX_UNCOMPRESSED_BYTES:
                            raise SkillArtifactError("uncompressed content too large")
                        destination.write(chunk)
                if written != member.file_size:
                    raise SkillArtifactError("invalid skill archive")
                if zipfile.is_zipfile(target):
                    raise SkillArtifactError("nested zip")
                if member is skill_members[0]:
                    try:
                        instructions = target.read_text(encoding="utf-8")
                    except UnicodeDecodeError as error:
                        raise SkillArtifactError("SKILL.md must be UTF-8") from error
            if instructions is None:
                raise SkillArtifactError("exactly one root SKILL.md is required")
            return instructions

    @staticmethod
    def _validate_member(member: zipfile.ZipInfo, artifact: bytes) -> PurePosixPath:
        name = member.filename
        if member.orig_filename != name:
            raise SkillArtifactError("unsafe zip path")
        is_directory = member.is_dir()
        parts = _raw_posix_parts(name, allow_directory=is_directory, local_path=True)
        path = PurePosixPath(*parts)
        if len(path.parts) - 1 > MAX_PATH_DEPTH:
            raise SkillArtifactError("zip path too deep")
        mode = member.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise SkillArtifactError("unsafe zip member")
        if is_directory:
            if (file_type not in {0, stat.S_IFDIR}) or member.file_size or member.compress_size:
                raise SkillArtifactError("unsafe zip member")
        elif file_type == stat.S_IFDIR:
            raise SkillArtifactError("unsafe zip member")
        if member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise SkillArtifactError("unsupported zip compression")
        if member.flag_bits & ~_ALLOWED_ZIP_FLAGS:
            raise SkillArtifactError("unsafe zip flags")
        if member.file_size < 0 or member.file_size > MAX_FILE_BYTES:
            raise SkillArtifactError("uncompressed content too large")
        if member.compress_size < 0 or member.compress_size > MAX_ARCHIVE_BYTES:
            raise SkillArtifactError("invalid skill archive")
        if member.file_size and not member.compress_size:
            raise SkillArtifactError("zip compression ratio too high")
        if member.compress_size and member.file_size > member.compress_size * MAX_COMPRESSION_RATIO:
            raise SkillArtifactError("zip compression ratio too high")
        if member.header_offset < 0:
            raise SkillArtifactError("invalid skill archive")
        SkillArtifactCache._validate_local_header(member, artifact)
        return path

    @staticmethod
    def _validate_local_header(member: zipfile.ZipInfo, artifact: bytes) -> None:
        offset = member.header_offset
        if offset + _LOCAL_HEADER.size > len(artifact):
            raise SkillArtifactError("invalid skill archive")
        try:
            (
                signature,
                _version,
                flags,
                compression,
                _modified_time,
                _modified_date,
                _crc,
                _compressed_size,
                _uncompressed_size,
                name_size,
                extra_size,
            ) = _LOCAL_HEADER.unpack_from(artifact, offset)
        except struct.error as error:
            raise SkillArtifactError("invalid skill archive") from error
        end = offset + _LOCAL_HEADER.size + name_size + extra_size
        if signature != _LOCAL_HEADER_SIGNATURE or end > len(artifact):
            raise SkillArtifactError("invalid skill archive")
        if flags != member.flag_bits or compression != member.compress_type:
            raise SkillArtifactError("unsafe zip flags")
        if flags & ~_ALLOWED_ZIP_FLAGS:
            raise SkillArtifactError("unsafe zip flags")
        encoding = "utf-8" if flags & 0x800 else "cp437"
        try:
            expected_name = member.orig_filename.encode(encoding)
        except UnicodeEncodeError as error:
            raise SkillArtifactError("unsafe zip path") from error
        raw_name = artifact[offset + _LOCAL_HEADER.size : offset + _LOCAL_HEADER.size + name_size]
        if raw_name != expected_name:
            raise SkillArtifactError("unsafe zip path")


def _run_limited(function, *args):
    with _WORKER_LIMIT:
        return function(*args)


async def _acquire_lock(lock: _CacheFileLock) -> None:
    """Poll lock I/O in a dedicated bounded executor with cancellation safety."""
    delay = 0.005
    while True:
        cancellation_state = {"cancelled": False, "release_scheduled": False}
        cancellation_lock = threading.Lock()
        attempt = _LOCK_EXECUTOR.submit(lock.try_acquire)

        def release_if_cancelled(done) -> None:
            if not done.done() or done.cancelled():
                return
            try:
                acquired = done.result()
            except Exception:
                return
            if not acquired:
                return
            with cancellation_lock:
                if not cancellation_state["cancelled"] or cancellation_state["release_scheduled"]:
                    return
                cancellation_state["release_scheduled"] = True
            _LOCK_EXECUTOR.submit(lock.release)

        attempt.add_done_callback(release_if_cancelled)
        try:
            acquired = await asyncio.shield(asyncio.wrap_future(attempt))
        except asyncio.CancelledError:
            with cancellation_lock:
                cancellation_state["cancelled"] = True
            if attempt.done():
                release_if_cancelled(attempt)
            raise
        if acquired:
            return
        await asyncio.sleep(min(
            delay * (0.75 + _BACKOFF_RANDOM() * 0.5), _LOCK_BACKOFF_CAP_SECONDS
        ))
        delay = min(delay * 2, _LOCK_BACKOFF_CAP_SECONDS)


def _schedule_release(lease: _LockLease) -> None:
    """Schedule non-stage cleanup without needing a surviving event loop task."""
    _LOCK_EXECUTOR.submit(lease.release_before_stage)


def _raw_posix_parts(value: str, *, allow_directory: bool, local_path: bool) -> tuple[str, ...]:
    """Validate raw POSIX segments before any path library can normalize them."""
    message = "unsafe zip path" if local_path else "unsafe object key"
    if not value or "\\" in value or value.startswith("/"):
        raise SkillArtifactError(message)
    raw_value = value[:-1] if allow_directory and value.endswith("/") else value
    if allow_directory != value.endswith("/"):
        raise SkillArtifactError(message)
    parts = raw_value.split("/")
    if not raw_value or any(part in {"", ".", ".."} for part in parts):
        raise SkillArtifactError(message)
    if any(any(ord(character) < 32 or ord(character) == 127 for character in part) for part in parts):
        raise SkillArtifactError(message)
    if local_path:
        for part in parts:
            if ":" in part or _is_windows_reserved_name(part):
                raise SkillArtifactError(message)
    return tuple(parts)


def _is_windows_reserved_name(part: str) -> bool:
    basename = part.rstrip(". ").split(".", 1)[0].rstrip(" ")
    basename = basename.translate(str.maketrans({"¹": "1", "²": "2", "³": "3"}))
    return basename.upper() in _WINDOWS_RESERVED_NAMES


_default_cache: SkillArtifactCache | None = None


def default_cache() -> SkillArtifactCache:
    """Return the process-wide cache rooted in the configured skill directory."""
    global _default_cache
    if _default_cache is None:
        root = Path(settings.skill_storage.skill_storage_dir) / "conversation-skills"
        _default_cache = SkillArtifactCache(root, downloader=_download)
    return _default_cache
