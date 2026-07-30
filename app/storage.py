from dataclasses import dataclass


@dataclass
class StoredVideo:
    video_id: str
    filename: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str
    content: bytes


class VideoStore:
    """In-memory store for uploaded video files and metadata."""

    def __init__(self) -> None:
        self._videos: dict[str, StoredVideo] = {}

    def store(self, video: StoredVideo) -> None:
        self._videos[video.video_id] = video

    def get(self, video_id: str) -> StoredVideo | None:
        return self._videos.get(video_id)
