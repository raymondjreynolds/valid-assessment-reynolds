from app.frames import SampledFrame, _subsample_frames


def test_subsample_frames_caps_count():
    frames = [
        SampledFrame(timestamp=float(index), image=None)  # type: ignore[arg-type]
        for index in range(30)
    ]

    sampled = _subsample_frames(frames, max_frames=12)

    assert len(sampled) == 12
    assert sampled[0].timestamp == 0.0
    assert sampled[-1].timestamp == 29.0
