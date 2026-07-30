import pytest

from app.fingerprint_readiness import (
    FingerprintNotReadyError,
    ensure_query_fingerprint_ready,
)
from app.fingerprint_status import FingerprintStatus
from app.storage import StoredVideo, VideoStore


def test_ensure_query_fingerprint_ready_allows_ready_query():
    store = VideoStore()
    query = StoredVideo(
        video_id="11111111",
        filename="query.mp4",
        width=576,
        height=1024,
        aspect_ratio="9:16",
        ratio_bucket="9:16",
        content=b"query",
        fingerprint_status=FingerprintStatus.READY,
    )
    ensure_query_fingerprint_ready(query, store)


def test_ensure_query_fingerprint_ready_retries_failed_query(monkeypatch):
    store = VideoStore()
    query = StoredVideo(
        video_id="11111111",
        filename="query.mp4",
        width=576,
        height=1024,
        aspect_ratio="9:16",
        ratio_bucket="9:16",
        content=b"query",
        fingerprint_status=FingerprintStatus.FAILED,
        fingerprint_attempt=1,
        fingerprint_last_attempt_at=0.0,
        fingerprint_error="boom",
    )
    store.store(query)
    scheduled: list[str] = []
    monkeypatch.setattr(
        "app.fingerprint_retries.schedule_fingerprint_job",
        lambda vid, _store: scheduled.append(vid),
    )
    monkeypatch.setattr("app.fingerprint_retries.monotonic_now", lambda: 100.0)

    with pytest.raises(FingerprintNotReadyError) as exc_info:
        ensure_query_fingerprint_ready(query, store)

    assert exc_info.value.status is FingerprintStatus.PENDING
    assert scheduled == ["11111111"]


def test_ensure_query_fingerprint_ready_returns_failed_when_retries_exhausted(monkeypatch):
    store = VideoStore()
    query = StoredVideo(
        video_id="11111111",
        filename="query.mp4",
        width=576,
        height=1024,
        aspect_ratio="9:16",
        ratio_bucket="9:16",
        content=b"query",
        fingerprint_status=FingerprintStatus.FAILED,
        fingerprint_attempt=3,
        fingerprint_error="boom",
    )
    store.store(query)
    monkeypatch.setattr("app.config.FINGERPRINT_MAX_RETRIES", 3)
    monkeypatch.setattr("app.fingerprint_retries.FINGERPRINT_MAX_RETRIES", 3)

    with pytest.raises(FingerprintNotReadyError) as exc_info:
        ensure_query_fingerprint_ready(query, store)

    assert exc_info.value.status is FingerprintStatus.FAILED
