from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

BASE_DIR = Path(__file__).resolve().parent.parent
FEEDBACK_PATH = BASE_DIR / "data" / "feedback.jsonl"
ERROR_LOG_PATH = BASE_DIR / "logs" / "assetos.log"
VERSION = "0.2.7"
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
    destination: Path = FEEDBACK_PATH,
) -> FeedbackEntry:
    """Append one validated feedback entry to lightweight local storage."""
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
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _feedback_lock, destination.open("a", encoding="utf-8") as output:
        output.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return entry


def get_error_logger(log_path: Path = ERROR_LOG_PATH) -> logging.Logger:
    """Return one size-bounded application error logger."""
    logger = logging.getLogger("assetos")
    if logger.handlers:
        return logger
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
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
