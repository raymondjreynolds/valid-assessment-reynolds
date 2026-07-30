from fastapi.testclient import TestClient

from app.fingerprint_status import FingerprintStatus
from app.fingerprints.base import FingerprintSet, FrameFingerprint
from app.main import app
from app.matching.matcher import VideoMatcher
from app.matching.prefilter import NoOpPrefilter
from app.storage import StoredVideo, VideoStore

client = TestClient(app)


def test_delete_video_endpoint(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="87654321",
            filename="test.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"video-bytes",
        )
    )
    monkeypatch.setattr("app.main.store", store)

    response = client.delete("/videos/87654321")
    assert response.status_code == 200
    assert response.json() == {"deleted": "87654321"}
    assert store.get("87654321") is None


def test_delete_unknown_video_returns_404(monkeypatch):
    monkeypatch.setattr("app.main.store", VideoStore())

    response = client.delete("/videos/87654321")
    assert response.status_code == 404


def test_delete_invalid_video_id_returns_404():
    response = client.delete("/videos/not-an-id")
    assert response.status_code == 404


def test_list_videos_endpoint(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="a.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"a",
        )
    )
    store.store(
        StoredVideo(
            video_id="22222222",
            filename="b.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"b",
        )
    )
    monkeypatch.setattr("app.main.store", store)

    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == [
        {
            "video_id": "11111111",
            "width": 576,
            "height": 1024,
            "aspect_ratio": "9:16",
            "ratio_bucket": "9:16",
            "filename": "a.mp4",
        },
        {
            "video_id": "22222222",
            "width": 1280,
            "height": 720,
            "aspect_ratio": "16:9",
            "ratio_bucket": "16:9",
            "filename": "b.mp4",
        },
    ]


def test_list_videos_empty(monkeypatch):
    monkeypatch.setattr("app.main.store", VideoStore())

    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == []


def test_list_videos_filter_by_ratio(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="a.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"a",
        )
    )
    store.store(
        StoredVideo(
            video_id="22222222",
            filename="b.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"b",
        )
    )
    monkeypatch.setattr("app.main.store", store)

    response = client.get("/videos", params={"ratio": "9:16"})
    assert response.status_code == 200
    assert response.json() == [
        {
            "video_id": "11111111",
            "width": 576,
            "height": 1024,
            "aspect_ratio": "9:16",
            "ratio_bucket": "9:16",
            "filename": "a.mp4",
        }
    ]


def test_list_videos_invalid_ratio_filter_returns_404():
    response = client.get("/videos", params={"ratio": "7:3"})
    assert response.status_code == 404

    response = client.get("/videos", params={"ratio": "Other"})
    assert response.status_code == 404


def test_match_unknown_video_returns_404():
    response = client.get("/match", params={"video_id": "12345678"})
    assert response.status_code == 404


def test_match_invalid_video_id_returns_404():
    response = client.get("/match", params={"video_id": "not-valid"})
    assert response.status_code == 404


def test_match_endpoint_returns_cross_bucket_matches(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="query.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"query",
            fingerprint_method="dinov2",
            fingerprint_status=FingerprintStatus.READY,
            fingerprints=FingerprintSet(
                method="dinov2",
                frames=[
                    FrameFingerprint(timestamp=0.0, dinov2=[1.0, 0.0]),
                    FrameFingerprint(timestamp=1.0, dinov2=[1.0, 0.0]),
                    FrameFingerprint(timestamp=2.0, dinov2=[1.0, 0.0]),
                ]
            ),
        )
    )
    store.store(
        StoredVideo(
            video_id="22222222",
            filename="match.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"match",
            fingerprint_method="dinov2",
            fingerprint_status=FingerprintStatus.READY,
            fingerprints=FingerprintSet(
                method="dinov2",
                frames=[
                    FrameFingerprint(timestamp=0.5, dinov2=[1.0, 0.0]),
                    FrameFingerprint(timestamp=1.5, dinov2=[1.0, 0.0]),
                    FrameFingerprint(timestamp=2.5, dinov2=[1.0, 0.0]),
                ]
            ),
        )
    )
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr("app.main.matcher", VideoMatcher(store=store, prefilter=NoOpPrefilter()))

    response = client.get("/match", params={"video_id": "11111111"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["video_id"] == "22222222"
    assert payload[0]["filename"] == "match.mp4"
    assert "confidence" in payload[0]
    assert set(payload[0]) == {"video_id", "filename", "confidence"}


def test_match_returns_processing_when_fingerprints_pending(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="query.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"query",
            fingerprint_status=FingerprintStatus.PROCESSING,
            fingerprint_started_at=0.0,
        )
    )
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr("app.main.matcher", VideoMatcher(store=store, prefilter=NoOpPrefilter()))
    monkeypatch.setattr("app.fingerprint_readiness.monotonic_now", lambda: 10.0)

    response = client.get("/match", params={"video_id": "11111111"})
    assert response.status_code == 202
    assert response.json() == {
        "status": "processing",
        "message": "Fingerprints are still being computed",
    }


def test_match_returns_processing_when_any_video_fingerprint_pending(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="query.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"query",
            fingerprint_status=FingerprintStatus.READY,
            fingerprints=FingerprintSet(method="vpdq", frames=[]),
        )
    )
    store.store(
        StoredVideo(
            video_id="22222222",
            filename="candidate.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"candidate",
            fingerprint_status=FingerprintStatus.PROCESSING,
            fingerprint_started_at=0.0,
        )
    )
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr("app.main.matcher", VideoMatcher(store=store, prefilter=NoOpPrefilter()))
    monkeypatch.setattr("app.fingerprint_readiness.monotonic_now", lambda: 10.0)

    response = client.get("/match", params={"video_id": "11111111"})
    assert response.status_code == 202
    assert response.json() == {
        "status": "processing",
        "message": "Fingerprints are still being computed",
    }


def test_match_returns_timed_out_after_timeout(monkeypatch):
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="11111111",
            filename="query.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=b"query",
            fingerprint_status=FingerprintStatus.PROCESSING,
            fingerprint_started_at=0.0,
        )
    )
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr("app.main.matcher", VideoMatcher(store=store, prefilter=NoOpPrefilter()))
    monkeypatch.setattr("app.config.FINGERPRINT_TIMEOUT_SECONDS", 60)
    monkeypatch.setattr("app.fingerprint_readiness.FINGERPRINT_TIMEOUT_SECONDS", 60)
    monkeypatch.setattr("app.fingerprint_readiness.monotonic_now", lambda: 100.0)

    response = client.get("/match", params={"video_id": "11111111"})
    assert response.status_code == 503
    assert response.json()["status"] == "timed_out"
    assert "video_id" not in response.json()
