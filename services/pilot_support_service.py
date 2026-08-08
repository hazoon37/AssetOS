from __future__ import annotations

import logging
import os
import sqlite3
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from services.user_context import get_current_user_id
from services.user_storage_service import feedback_database_path, log_database_path

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION = "0.3.0"
FEEDBACK_CATEGORIES = ("Bug", "Suggestion", "Comment")
_feedback_lock = threading.Lock()
_exception_hook_installed = False


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    build: str
    git_tag: str


@dataclass(frozen=True)
class FeedbackEntry:
    user_id: str
    category: str
    comment: str
    created_at: str


def _git_value(*arguments: str) -> str:
    try:
        return subprocess.check_output(
            ("git", *arguments),
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=1,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def get_release_info() -> ReleaseInfo:
    """Return deployment metadata, using Git only as a local fallback."""
    build = os.getenv("ASSETOS_BUILD", "").strip() or _git_value(
        "rev-parse", "--short", "HEAD"
    )
    git_tag = os.getenv("ASSETOS_GIT_TAG", "").strip() or _git_value(
        "describe", "--tags", "--exact-match"
    )
    return ReleaseInfo(VERSION, build or "local", git_tag or "unreleased")


def submit_feedback(
    user_id: str,
    category: str,
    comment: str,
    destination: Path | None = None,
) -> FeedbackEntry:
    """Store one validated feedback entry in the user's isolated database."""
    owner = str(user_id or "").strip()
    kind = str(category or "").strip()
    message = str(comment or "").strip()
    if not owner:
        raise ValueError("사용자 정보가 필요합니다.")
    if kind not in FEEDBACK_CATEGORIES:
        raise ValueError("지원하지 않는 피드백 유형입니다.")
    if not message:
        raise ValueError("내용을 입력해 주세요.")
    if len(message) > 2000:
        raise ValueError("피드백은 2,000자 이하로 입력해 주세요.")
    entry = FeedbackEntry(owner, kind, message, datetime.now(UTC).isoformat())
    database_path = destination or feedback_database_path(owner)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _feedback_lock, sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO feedback (user_id, category, comment, created_at) VALUES (?, ?, ?, ?)",
            (entry.user_id, entry.category, entry.comment, entry.created_at),
        )
    return entry


class SQLiteLogHandler(logging.Handler):
    def __init__(self, database_path: Path) -> None:
        super().__init__(logging.ERROR)
        self.database_path = database_path

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS error_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO error_logs (level, message, created_at) VALUES (?, ?, ?)",
                    (
                        record.levelname,
                        self.format(record),
                        datetime.now(UTC).isoformat(),
                    ),
                )
        except (OSError, sqlite3.Error):
            self.handleError(record)


def get_error_logger(
    log_path: Path | None = None,
    user_id: str | None = None,
) -> logging.Logger:
    """Return the error logger for one isolated user database."""
    owner = str(user_id or get_current_user_id())
    database_path = log_path or log_database_path(owner)
    logger = logging.getLogger(f"assetos.{database_path}")
    if logger.handlers:
        return logger
    handler = SQLiteLogHandler(database_path)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    return logger


def log_unexpected_exception(context: str) -> None:
    """Log the active exception without exposing details in the UI."""
    get_error_logger().exception("Unexpected exception [%s]", context)


def install_exception_logging() -> None:
    """Record otherwise uncaught main-thread exceptions before normal handling."""
    global _exception_hook_installed
    if _exception_hook_installed:
        return
    previous_hook = sys.excepthook

    def exception_hook(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        get_error_logger().error(
            "Uncaught application exception",
            exc_info=(exception_type, exception, traceback),
        )
        previous_hook(exception_type, exception, traceback)

    sys.excepthook = exception_hook
    _exception_hook_installed = True
