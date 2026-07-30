from fastapi.testclient import TestClient

from app.fingerprint_status import FingerprintStatus
from app.main import app
from app.storage import StoredVideo, VideoStore
from app.video import generate_video_id
from tests.fixtures import build_minimal_mp4

client = TestClient(app)


def test_upload_rejects_empty_file_list():
    response = client.post("/upload", files=[])
    assert response.status_code == 422


def test_upload_rejects_non_mp4(monkeypatch):
    monkeypatch.setattr("app.main.store", VideoStore())
    response = client.post(
        "/upload",
        files={"files": ("clip.mov", b"not-mp4", "video/quicktime")},
    )
    assert response.status_code == 400
    assert "Only MP4" in response.json()["detail"]


def test_upload_rejects_empty_bytes(monkeypatch):
    monkeypatch.setattr("app.main.store", VideoStore())
    response = client.post(
        "/upload",
        files={"files": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


def test_upload_rejects_invalid_mp4(monkeypatch):
    monkeypatch.setattr("app.main.store", VideoStore())
    response = client.post(
        "/upload",
        files={"files": ("bad.mp4", b"not-a-valid-mp4", "video/mp4")},
    )
    assert response.status_code == 400
    assert "Invalid video file" in response.json()["detail"]


def test_upload_accepts_valid_mp4(monkeypatch):
    store = VideoStore()
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr("app.main.schedule_fingerprint_job", lambda *_args: None)

    content = build_minimal_mp4(576, 1024)
    response = client.post(
        "/upload",
        files={"files": ("clip.mp4", content, "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ratio_bucket"] == "9:16"
    assert payload[0]["video_id"] == generate_video_id(content)

    stored = store.get(payload[0]["video_id"])
    assert stored is not None
    assert stored.fingerprint_status is FingerprintStatus.PENDING
    assert stored.fingerprint_attempt == 1


def test_upload_duplicate_returns_existing_ready_video(monkeypatch):
    store = VideoStore()
    content = build_minimal_mp4(576, 1024)
    video_id = generate_video_id(content)
    store.store(
        StoredVideo(
            video_id=video_id,
            filename="original.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=content,
            fingerprint_status=FingerprintStatus.READY,
            fingerprint_attempt=1,
        )
    )
    scheduled: list[str] = []
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr(
        "app.main.schedule_fingerprint_job",
        lambda vid, _store: scheduled.append(vid),
    )

    response = client.post(
        "/upload",
        files={"files": ("duplicate.mp4", content, "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()[0]["filename"] == "original.mp4"
    assert scheduled == []


def test_upload_duplicate_retries_failed_video(monkeypatch):
    store = VideoStore()
    content = build_minimal_mp4(576, 1024)
    video_id = generate_video_id(content)
    store.store(
        StoredVideo(
            video_id=video_id,
            filename="failed.mp4",
            width=576,
            height=1024,
            aspect_ratio="9:16",
            ratio_bucket="9:16",
            content=content,
            fingerprint_status=FingerprintStatus.FAILED,
            fingerprint_attempt=1,
            fingerprint_error="ffmpeg failed",
        )
    )
    scheduled: list[str] = []
    monkeypatch.setattr("app.main.store", store)
    monkeypatch.setattr(
        "app.fingerprint_retries.schedule_fingerprint_job",
        lambda vid, _store: scheduled.append(vid),
    )

    response = client.post(
        "/upload",
        files={"files": ("failed.mp4", content, "video/mp4")},
    )

    assert response.status_code == 200
    refreshed = store.get(video_id)
    assert refreshed is not None
    assert refreshed.fingerprint_status is FingerprintStatus.PENDING
    assert refreshed.fingerprint_attempt == 2
    assert scheduled == [video_id]
