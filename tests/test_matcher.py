import numpy as np

from app.fingerprint_status import FingerprintStatus
from app.fingerprints.base import FingerprintSet, FrameFingerprint
from app.matching.matcher import VideoMatcher
from app.matching.prefilter import NoOpPrefilter
from app.storage import StoredVideo, VideoStore


def _video(
    video_id: str,
    ratio_bucket: str,
    vector_index: int,
    timestamps: list[float],
) -> StoredVideo:
    frames = [
        FrameFingerprint(
            timestamp=timestamp,
            dinov2=np.eye(8, dtype=np.float32)[vector_index].tolist(),
        )
        for timestamp in timestamps
    ]
    return StoredVideo(
        video_id=video_id,
        filename=f"{video_id}.mp4",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        ratio_bucket=ratio_bucket,
        content=b"video",
        fingerprints=FingerprintSet(frames=frames),
        fingerprint_status=FingerprintStatus.READY,
    )


def test_matcher_returns_cross_bucket_matches_only():
    store = VideoStore()
    query = _video("11111111", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    same_bucket = _video("22222222", "9:16", vector_index=0, timestamps=[0.0, 1.0, 2.0, 3.0])
    cross_bucket = _video("33333333", "16:9", vector_index=0, timestamps=[0.5, 1.5, 2.5, 3.5])
    unrelated = _video("44444444", "1:1", vector_index=1, timestamps=[0.0, 1.0, 2.0, 3.0])

    store.store(query)
    store.store(same_bucket)
    store.store(cross_bucket)
    store.store(unrelated)

    matcher = VideoMatcher(store=store, prefilter=NoOpPrefilter())
    matches = matcher.match("11111111")

    assert len(matches) == 1
    assert matches[0].video_id == "33333333"
    assert matches[0].ratio_bucket == "16:9"
    assert matches[0].method == "dinov2"


def test_matcher_unknown_video_raises_key_error():
    matcher = VideoMatcher(store=VideoStore(), prefilter=NoOpPrefilter())
    try:
        matcher.match("12345678")
        assert False, "Expected KeyError"
    except KeyError:
        pass
