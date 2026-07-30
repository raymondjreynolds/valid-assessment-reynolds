from PIL import Image

from app.frames import (
    SampledFrame,
    _filter_dark_frames,
    _subsample_frames,
    crop_to_content,
    is_dark_frame,
    letterbox_to_square,
    plan_frame_sampling,
    prepare_frame_for_hashing,
)


def test_plan_frame_sampling_scales_with_duration():
    assert plan_frame_sampling(10) == (1.0, 11)
    assert plan_frame_sampling(15) == (1.0, 12)
    assert plan_frame_sampling(20) == (1.0, 16)
    assert plan_frame_sampling(45) == (0.5, 20)
    assert plan_frame_sampling(90) == (0.5, 24)


def test_plan_frame_sampling_enforces_minimum_for_short_clips():
    assert plan_frame_sampling(2) == (1.0, 4)


def test_crop_to_content_trims_black_borders():
    framed = Image.new("RGB", (200, 100), color=(0, 0, 0))
    framed.paste(Image.new("RGB", (80, 60), color=(255, 255, 255)), (60, 20))

    cropped = crop_to_content(framed)

    assert cropped.size == (80, 60)


def test_prepare_frame_for_hashing_uses_content_crop_and_letterbox():
    framed = Image.new("RGB", (200, 100), color=(0, 0, 0))
    framed.paste(Image.new("RGB", (80, 60), color=(255, 0, 0)), (60, 20))

    prepared = prepare_frame_for_hashing(framed)

    assert prepared.size == (384, 384)
    assert not is_dark_frame(prepared)


def test_filter_dark_frames_keeps_bright_frames_when_available():
    bright = SampledFrame(timestamp=0.0, image=Image.new("RGB", (8, 8), color=(200, 200, 200)))
    dark = SampledFrame(timestamp=1.0, image=Image.new("RGB", (8, 8), color=(0, 0, 0)))
    frames = [dark, bright, bright, bright, bright]

    filtered = _filter_dark_frames(frames)

    assert dark not in filtered
    assert len(filtered) == 4


def test_letterbox_to_square_produces_fixed_canvas():
    portrait = Image.new("RGB", (144, 256), color=(255, 0, 0))
    landscape = Image.new("RGB", (256, 144), color=(0, 255, 0))

    portrait_box = letterbox_to_square(portrait, size=256)
    landscape_box = letterbox_to_square(landscape, size=256)

    assert portrait_box.size == (256, 256)
    assert landscape_box.size == (256, 256)


def test_subsample_frames_caps_count():
    frames = [
        SampledFrame(timestamp=float(index), image=None)  # type: ignore[arg-type]
        for index in range(30)
    ]

    sampled = _subsample_frames(frames, max_frames=12)

    assert len(sampled) == 12
    assert sampled[0].timestamp == 0.0
    assert sampled[-1].timestamp == 29.0


def test_sample_frames_raises_when_ffmpeg_times_out(monkeypatch):
    import subprocess

    import app.frames as frames_module

    def _timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)

    monkeypatch.setattr(frames_module.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(frames_module.subprocess, "run", _timeout)
    monkeypatch.setattr(frames_module, "FFMPEG_TIMEOUT_SECONDS", 1)

    try:
        frames_module.sample_frames(b"video-bytes", fps=1, max_frames=4)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "timed out" in str(exc).lower()
