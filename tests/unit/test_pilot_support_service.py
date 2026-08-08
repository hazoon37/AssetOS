import json
import logging
import tempfile
from pathlib import Path

import pytest

from services.pilot_support_service import (
    get_error_logger,
    get_release_info,
    submit_feedback,
)


def test_release_info_contains_required_fields() -> None:
    release = get_release_info()
    assert release.version
    assert release.build
    assert release.git_tag


def test_feedback_is_validated_and_written_as_jsonl() -> None:
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "feedback.jsonl"
        entry = submit_feedback("google:123", "Bug", "Import failed", destination)
        stored = json.loads(destination.read_text(encoding="utf-8"))
        assert stored["user_id"] == entry.user_id
        assert stored["category"] == "Bug"
        assert stored["comment"] == "Import failed"
        with pytest.raises(ValueError):
            submit_feedback("google:123", "Unknown", "Message", destination)
        with pytest.raises(ValueError):
            submit_feedback("google:123", "Comment", "", destination)


def test_unexpected_exception_is_written_to_bounded_log() -> None:
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "assetos.log"
        logger = get_error_logger(destination)
        try:
            raise RuntimeError("pilot failure")
        except RuntimeError:
            logger.exception("Unexpected exception [test]")
        for handler in logger.handlers:
            handler.flush()
        assert "pilot failure" in destination.read_text(encoding="utf-8")
        for handler in tuple(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        logging.shutdown()
