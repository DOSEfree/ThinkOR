"""Atomic, non-secret updates for ThinkOR's local dotenv mode settings."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from dotenv import set_key

from ideaos_agent.domain.runtime import RuntimeModeSelection

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

MODE_ENVIRONMENT_KEYS = (
    "IDEAOS_USE_FAKE_LLM",
    "IDEAOS_USE_FAKE_ARCHIVE",
)


class DotenvStoreError(RuntimeError):
    """Raised when the local dotenv file cannot be safely updated."""


@dataclass(frozen=True)
class DotenvModeUpdate:
    """Safe result details after updating only the runtime mode flags."""

    created_from_template: bool
    updated_keys: tuple[str, ...] = MODE_ENVIRONMENT_KEYS


_PROCESS_LOCK = threading.RLock()


@contextmanager
def _exclusive_file_lock(lock_path: Path) -> Iterator[None]:
    """Use a small cross-process lock file while replacing dotenv content."""

    try:
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            lock_file.seek(0)
            if lock_file.read(1) == "":
                lock_file.write("0")
                lock_file.flush()

            if sys.platform == "win32":
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise DotenvStoreError("Unable to lock the local dotenv settings.") from exc


class DotenvModeStore:
    """Create or patch the project dotenv file without handling credentials."""

    def __init__(self, *, dotenv_path: Path, template_path: Path) -> None:
        self._dotenv_path = dotenv_path
        self._template_path = template_path

    def update_modes(self, selection: RuntimeModeSelection) -> DotenvModeUpdate:
        """Persist validated mode flags while preserving every other dotenv entry."""

        selection.validate()
        self._validate_paths()

        with _PROCESS_LOCK, _exclusive_file_lock(self._lock_path):
            created_from_template = not self._dotenv_path.exists()
            source = self._read_source(created_from_template)
            self._write_atomically(source, selection)

        return DotenvModeUpdate(created_from_template=created_from_template)

    @property
    def _lock_path(self) -> Path:
        return self._dotenv_path.with_name(f"{self._dotenv_path.name}.lock")

    def _validate_paths(self) -> None:
        if self._dotenv_path.name != ".env":
            raise DotenvStoreError("Only a project .env file may be updated.")
        if self._dotenv_path.exists():
            if self._dotenv_path.is_symlink() or not self._dotenv_path.is_file():
                raise DotenvStoreError("A regular .env file is required.")
            return
        if not self._template_path.is_file() or self._template_path.is_symlink():
            raise DotenvStoreError("A regular .env.example template is required.")

    def _read_source(self, created_from_template: bool) -> str:
        source_path = self._template_path if created_from_template else self._dotenv_path
        try:
            return source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DotenvStoreError("Unable to read the local dotenv source file.") from exc

    def _write_atomically(self, source: str, selection: RuntimeModeSelection) -> None:
        self._dotenv_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".thinkor-env-",
            suffix=".tmp",
            dir=self._dotenv_path.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        original_mode = self._existing_mode()

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as temporary_file:
                temporary_file.write(source)

            os.chmod(temporary_path, original_mode)
            set_key(
                str(temporary_path),
                "IDEAOS_USE_FAKE_LLM",
                self._as_dotenv_bool(selection.use_fake_llm),
                quote_mode="never",
            )
            set_key(
                str(temporary_path),
                "IDEAOS_USE_FAKE_ARCHIVE",
                self._as_dotenv_bool(selection.use_fake_archive),
                quote_mode="never",
            )
            self._fsync(temporary_path)
            os.replace(temporary_path, self._dotenv_path)
        except OSError as exc:
            raise DotenvStoreError("Unable to atomically update the local .env file.") from exc
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def _existing_mode(self) -> int:
        if not self._dotenv_path.exists():
            return stat.S_IRUSR | stat.S_IWUSR
        return stat.S_IMODE(self._dotenv_path.stat().st_mode)

    @staticmethod
    def _as_dotenv_bool(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _fsync(path: Path) -> None:
        # Windows requires a write-capable handle for FlushFileBuffers/fsync.
        with path.open("r+b") as temporary_file:
            os.fsync(temporary_file.fileno())
