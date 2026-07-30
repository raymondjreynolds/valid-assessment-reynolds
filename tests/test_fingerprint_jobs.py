from app.fingerprint_jobs import run_fingerprint_job
from app.fingerprint_status import FingerprintStatus
from app.fingerprints.base import FingerprintSet, FrameFingerprint
from app.storage import StoredVideo, VideoStore


def test_update_fingerprints_skips_timed_out_status():
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="clip.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"video",
            fingerprint_status=FingerprintStatus.TIMED_OUT,
            fingerprint_attempt=1,
        )
    )

    updated = store.update_fingerprints(
        "11111111",
        FingerprintSet(method="vpdq", frames=[FrameFingerprint(timestamp=0.0, vpdq="abc")]),
        expected_attempt=1,
    )

    assert updated is False
    video = store.get("11111111")
    assert video is not None
    assert video.fingerprint_status is FingerprintStatus.TIMED_OUT


def test_update_fingerprints_skips_stale_attempt():
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="clip.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"video",
            fingerprint_status=FingerprintStatus.PROCESSING,
            fingerprint_attempt=2,
        )
    )

    updated = store.update_fingerprints(
        "11111111",
        FingerprintSet(method="vpdq", frames=[FrameFingerprint(timestamp=0.0, vpdq="abc")]),
        expected_attempt=1,
    )

    assert updated is False


def test_run_fingerprint_job_does_not_overwrite_timed_out(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="clip.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"video",
            fingerprint_status=FingerprintStatus.TIMED_OUT,
            fingerprint_attempt=1,
        )
    )

    monkeypatch.setattr(
        "app.fingerprint_jobs.build_fingerprints",
        lambda *_args, **_kwargs: FingerprintSet(
            method="vpdq",
            frames=[FrameFingerprint(timestamp=0.0, vpdq="abc")],
        ),
    )

    run_fingerprint_job("11111111", store)

    video = store.get("11111111")
    assert video is not None
    assert video.fingerprint_status is FingerprintStatus.TIMED_OUT
