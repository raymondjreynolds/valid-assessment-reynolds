from app.video import (
    compute_aspect_ratio,
    compute_ratio_bucket,
    generate_video_id,
)


def test_aspect_ratio_standard_buckets():
    assert compute_aspect_ratio(576, 1024) == "9:16"
    assert compute_aspect_ratio(576, 576) == "1:1"
    assert compute_aspect_ratio(1080, 1350) == "4:5"
    assert compute_aspect_ratio(1280, 720) == "16:9"
    assert compute_aspect_ratio(1470, 630) == "7:3"


def test_ratio_bucket():
    assert compute_ratio_bucket("9:16") == "9:16"
    assert compute_ratio_bucket("1:1") == "1:1"
    assert compute_ratio_bucket("4:5") == "4:5"
    assert compute_ratio_bucket("16:9") == "16:9"
    assert compute_ratio_bucket("7:3") == "Other"


def test_video_id_is_eight_digits():
    video_id = generate_video_id(b"sample video content")
    assert len(video_id) == 8
    assert video_id.isdigit()
