from PIL import Image

from app.frames import SampledFrame, _subsample_frames, letterbox_to_square


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
