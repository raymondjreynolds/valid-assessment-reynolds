from app.storage import StoredVideo, VideoStore


def test_delete_video_returns_deleted_id():
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="12345678",
            filename="test.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"video-bytes",
        )
    )

    assert store.delete("12345678") is True
    assert store.get("12345678") is None


def test_delete_unknown_video_returns_false():
    store = VideoStore()
    assert store.delete("12345678") is False


def test_release_video_content_clears_bytes():
    store = VideoStore()
    store.store(
        StoredVideo(
            video_id="12345678",
            filename="test.mp4",
            width=1280,
            height=720,
            aspect_ratio="16:9",
            ratio_bucket="16:9",
            content=b"video-bytes",
        )
    )

    store.release_video_content("12345678")

    video = store.get("12345678")
    assert video is not None
    assert video.content == b""
