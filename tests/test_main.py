from fastapi.testclient import TestClient

from app.main import app
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
