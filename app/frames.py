import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from app.config import (
    FRAME_SAMPLE_FPS,
    FRAME_SCALE_WIDTH,
    LETTERBOX_SIZE,
    MAX_FRAMES,
)


@dataclass(frozen=True)
class SampledFrame:
    timestamp: float
    image: Image.Image


def letterbox_to_square(
    image: Image.Image,
    size: int = LETTERBOX_SIZE,
) -> Image.Image:
    """Scale content to fit inside a square canvas with centered padding."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    scale = min(size / width, size / height)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = rgb.resize((new_width, new_height), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (size, size), (0, 0, 0))
    left = (size - new_width) // 2
    top = (size - new_height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def _subsample_frames(frames: list[SampledFrame], max_frames: int) -> list[SampledFrame]:
    if len(frames) <= max_frames:
        return frames

    indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
    return [frames[index] for index in indices]


def sample_frames(
    content: bytes,
    fps: float = FRAME_SAMPLE_FPS,
    max_frames: int = MAX_FRAMES,
) -> list[SampledFrame]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "input.mp4"
        frames_dir = Path(temp_dir) / "frames"
        frames_dir.mkdir()
        video_path.write_bytes(content)

        # Downscale during decode to reduce ffmpeg + PIL + inference cost.
        filter_chain = f"fps={fps},scale={FRAME_SCALE_WIDTH}:-2"
        output_pattern = str(frames_dir / "frame_%04d.jpg")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            filter_chain,
            "-qscale:v",
            "4",
            output_pattern,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ValueError(result.stderr.strip() or "Failed to extract frames with ffmpeg")

        frame_paths = sorted(frames_dir.glob("frame_*.jpg"))
        if not frame_paths:
            raise ValueError("No frames could be extracted from video")

        sampled: list[SampledFrame] = []
        for index, frame_path in enumerate(frame_paths):
            with Image.open(frame_path) as image:
                normalized = letterbox_to_square(image)
                sampled.append(
                    SampledFrame(
                        timestamp=index / fps,
                        image=normalized.copy(),
                    )
                )

        return _subsample_frames(sampled, max_frames)


def is_dark_frame(image: Image.Image, threshold: float = 12.0) -> bool:
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)
    return float(grayscale.mean()) < threshold
