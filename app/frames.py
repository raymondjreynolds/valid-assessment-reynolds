import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from app.config import CENTER_CROP_FRACTION, FRAME_SAMPLE_FPS


@dataclass(frozen=True)
class SampledFrame:
    timestamp: float
    image: Image.Image


def center_crop(image: Image.Image, fraction: float = CENTER_CROP_FRACTION) -> Image.Image:
    width, height = image.size
    crop_width = max(1, int(width * fraction))
    crop_height = max(1, int(height * fraction))
    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    return image.crop((left, top, left + crop_width, top + crop_height))


def sample_frames(content: bytes, fps: float = FRAME_SAMPLE_FPS) -> list[SampledFrame]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "input.mp4"
        frames_dir = Path(temp_dir) / "frames"
        frames_dir.mkdir()
        video_path.write_bytes(content)

        output_pattern = str(frames_dir / "frame_%04d.jpg")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            "-qscale:v",
            "2",
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
                cropped = center_crop(image.convert("RGB"))
                sampled.append(
                    SampledFrame(
                        timestamp=index / fps,
                        image=cropped.copy(),
                    )
                )

        return sampled


def is_dark_frame(image: Image.Image, threshold: float = 12.0) -> bool:
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)
    return float(grayscale.mean()) < threshold
