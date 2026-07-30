"""Frame extraction and normalization for video fingerprinting."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

from app.config import (
    CONTENT_CROP_THRESHOLD,
    DARK_FRAME_THRESHOLD,
    FFMPEG_FRAME_QUALITY,
    FFMPEG_TIMEOUT_SECONDS,
    FRAME_SAMPLE_FPS,
    FRAME_SCALE_WIDTH,
    LETTERBOX_SIZE,
    MAX_FRAMES,
)


@dataclass(frozen=True)
class SampledFrame:
    """One decoded video frame with a timestamp in seconds."""

    timestamp: float
    image: Image.Image


def crop_to_content(
    image: Image.Image,
    threshold: int = CONTENT_CROP_THRESHOLD,
) -> Image.Image:
    """Trim uniform black borders before letterboxing."""
    rgb = image.convert("RGB")
    grayscale = np.asarray(rgb.convert("L"))
    content_mask = grayscale > threshold
    if not content_mask.any():
        return rgb

    rows = np.where(content_mask.any(axis=1))[0]
    columns = np.where(content_mask.any(axis=0))[0]
    left = int(columns[0])
    right = int(columns[-1]) + 1
    top = int(rows[0])
    bottom = int(rows[-1]) + 1
    return rgb.crop((left, top, right, bottom))


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
    resized = rgb.resize((new_width, new_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (0, 0, 0))
    left = (size - new_width) // 2
    top = (size - new_height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def prepare_frame_for_hashing(image: Image.Image) -> Image.Image:
    """Crop letterboxed content and pad to a square canvas for hashing."""
    return letterbox_to_square(crop_to_content(image))


def is_dark_frame(
    image: Image.Image,
    threshold: float = DARK_FRAME_THRESHOLD,
) -> bool:
    """Return True when mean luminance is below the dark-frame threshold."""
    grayscale = np.asarray(image.convert("L"), dtype=np.float32)
    return float(grayscale.mean()) < threshold


MIN_SAMPLE_FRAMES = 4


def plan_frame_sampling(duration_seconds: float) -> tuple[float, int]:
    """Choose sample rate and cap based on clip length."""
    duration = max(0.1, duration_seconds)

    if duration <= 15:
        sample_fps = 1.0
        max_frames = 12
    elif duration <= 30:
        sample_fps = 1.0
        max_frames = 16
    elif duration <= 60:
        sample_fps = 0.5
        max_frames = 20
    else:
        sample_fps = 0.5
        max_frames = MAX_FRAMES

    available_frames = int(duration * sample_fps) + 1
    max_frames = max(MIN_SAMPLE_FRAMES, min(max_frames, available_frames))
    return sample_fps, max_frames


def _subsample_frames(frames: list[SampledFrame], max_frames: int) -> list[SampledFrame]:
    """Evenly subsample frames down to ``max_frames`` when ffmpeg over-extracts."""
    if len(frames) <= max_frames:
        return frames

    indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
    return [frames[index] for index in indices]


def _filter_dark_frames(frames: list[SampledFrame]) -> list[SampledFrame]:
    """Drop near-black frames when enough brighter frames remain."""
    bright_frames = [frame for frame in frames if not is_dark_frame(frame.image)]
    if len(bright_frames) >= MIN_SAMPLE_FRAMES:
        return bright_frames
    return frames


def sample_frames(
    content: bytes,
    fps: float | None = None,
    max_frames: int | None = None,
    duration_seconds: float | None = None,
) -> list[SampledFrame]:
    """Extract, normalize, and subsample frames from raw MP4 bytes via ffmpeg.

    Sampling rate and cap follow ``plan_frame_sampling`` when ``fps`` and
    ``max_frames`` are omitted. Raises ``ValueError`` on ffmpeg failure or
    timeout.
    """
    if fps is None or max_frames is None:
        if duration_seconds is None:
            try:
                from app.video import extract_video_duration

                duration_seconds = extract_video_duration(content)
            except ValueError:
                duration_seconds = None

        if duration_seconds is not None:
            planned_fps, planned_max = plan_frame_sampling(duration_seconds)
        else:
            planned_fps, planned_max = FRAME_SAMPLE_FPS, MAX_FRAMES

        fps = fps if fps is not None else planned_fps
        max_frames = max_frames if max_frames is not None else planned_max

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "input.mp4"
        frames_dir = Path(temp_dir) / "frames"
        frames_dir.mkdir()
        video_path.write_bytes(content)

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
            str(FFMPEG_FRAME_QUALITY),
            output_pattern,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=FFMPEG_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(
                f"ffmpeg timed out after {FFMPEG_TIMEOUT_SECONDS} seconds"
            ) from exc
        if result.returncode != 0:
            raise ValueError(result.stderr.strip() or "Failed to extract frames with ffmpeg")

        frame_paths = sorted(frames_dir.glob("frame_*.jpg"))
        if not frame_paths:
            raise ValueError("No frames could be extracted from video")

        sampled: list[SampledFrame] = []
        for index, frame_path in enumerate(frame_paths):
            with Image.open(frame_path) as image:
                normalized = prepare_frame_for_hashing(image)
                sampled.append(
                    SampledFrame(
                        timestamp=index / fps,
                        image=normalized.copy(),
                    )
                )

        sampled = _filter_dark_frames(sampled)
        return _subsample_frames(sampled, max_frames)
