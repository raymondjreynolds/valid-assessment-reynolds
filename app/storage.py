import json
from dataclasses import dataclass
from datetime import timedelta

from google.cloud import storage
from google.oauth2 import service_account

from app.config import (
    GCS_BUCKET_NAME,
    GCS_CREDENTIALS_JSON,
    SIGNED_URL_EXPIRATION_SECONDS,
)


@dataclass
class StoredVideo:
    video_id: str
    gcs_blob_name: str
    filename: str
    width: int
    height: int
    aspect_ratio: str
    ratio_bucket: str


class VideoStore:
    """In-memory index of uploaded videos backed by GCS object storage."""

    def __init__(self) -> None:
        self._videos: dict[str, StoredVideo] = {}
        self._client: storage.Client | None = None
        self._bucket: storage.Bucket | None = None

    def _ensure_client(self) -> tuple[storage.Client, storage.Bucket]:
        if not GCS_BUCKET_NAME:
            raise RuntimeError("GCS_BUCKET_NAME environment variable is not set")
        if not GCS_CREDENTIALS_JSON:
            raise RuntimeError(
                "GCS_CREDENTIALS_JSON environment variable is not set"
            )

        if self._client is None:
            credentials_info = json.loads(GCS_CREDENTIALS_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            self._client = storage.Client(
                credentials=credentials,
                project=credentials_info.get("project_id"),
            )
            self._bucket = self._client.bucket(GCS_BUCKET_NAME)

        assert self._client is not None
        assert self._bucket is not None
        return self._client, self._bucket

    def upload(self, video: StoredVideo, content: bytes) -> None:
        _, bucket = self._ensure_client()
        blob = bucket.blob(video.gcs_blob_name)
        blob.upload_from_string(content, content_type="video/mp4")
        self._videos[video.video_id] = video

    def get(self, video_id: str) -> StoredVideo | None:
        return self._videos.get(video_id)

    def generate_signed_url(self, video_id: str) -> str:
        video = self._videos.get(video_id)
        if video is None:
            raise KeyError(f"Video {video_id} not found")

        _, bucket = self._ensure_client()
        blob = bucket.blob(video.gcs_blob_name)

        credentials_info = json.loads(GCS_CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info
        )

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=SIGNED_URL_EXPIRATION_SECONDS),
            method="GET",
            credentials=credentials,
        )
