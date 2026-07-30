from __future__ import annotations

import gc
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image

from app.config import ONNX_BATCH_SIZE, ONNX_MODEL, ONNX_MODEL_CACHE
from app.fingerprints.base import FrameFingerprint
from app.frames import SampledFrame, is_dark_frame

IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
CLIP_MEAN = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
CLIP_STD = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

_session: ort.InferenceSession | None = None
_model_spec: ModelSpec | None = None
_model_loading = False
_model_ready = False
_load_lock = threading.Lock()


@dataclass(frozen=True)
class ModelSpec:
    name: str
    url: str
    filename: str
    input_size: int
    mean: np.ndarray
    std: np.ndarray


MODEL_SPECS: dict[str, ModelSpec] = {
    "mobilenet": ModelSpec(
        name="mobilenet",
        url=(
            "https://media.githubusercontent.com/media/onnx/models/main/"
            "validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
        ),
        filename="mobilenetv2-7.onnx",
        input_size=224,
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD,
    ),
    "clip": ModelSpec(
        name="clip",
        url=(
            "https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/"
            "onnx/vision_model.onnx"
        ),
        filename="clip-vit-base-patch32-vision.onnx",
        input_size=224,
        mean=CLIP_MEAN,
        std=CLIP_STD,
    ),
}


def _resolve_model_spec(model_name: str | None = None) -> ModelSpec:
    selected = (model_name or ONNX_MODEL).lower()
    if selected not in MODEL_SPECS:
        supported = ", ".join(sorted(MODEL_SPECS))
        raise ValueError(f"Unsupported ONNX model: {selected}. Supported: {supported}")
    return MODEL_SPECS[selected]


def _model_cache_path(spec: ModelSpec) -> Path:
    return Path(ONNX_MODEL_CACHE) / spec.filename


def _download_model(spec: ModelSpec, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return

    partial = destination.with_suffix(destination.suffix + ".partial")
    with urllib.request.urlopen(spec.url, timeout=120) as response:
        partial.write_bytes(response.read())
    partial.rename(destination)


def preload_onnx(model_name: str | None = None) -> None:
    """Load the configured ONNX model once to avoid cold-start latency."""
    global _model_loading
    with _load_lock:
        if _model_ready or _model_loading:
            return
        _model_loading = True
    try:
        _get_session(model_name)
    finally:
        with _load_lock:
            _model_loading = False


def is_model_ready() -> bool:
    return _model_ready


def release_onnx_session() -> None:
    """Unload the ONNX model to free memory during matching."""
    global _session, _model_spec, _model_ready
    with _load_lock:
        _session = None
        _model_spec = None
        _model_ready = False
    gc.collect()


def _create_session(model_path: Path) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.enable_cpu_mem_arena = False
    options.enable_mem_pattern = False
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(
        str(model_path),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )


def _get_session(model_name: str | None = None) -> tuple[ort.InferenceSession, ModelSpec]:
    global _session, _model_spec, _model_ready
    spec = _resolve_model_spec(model_name)
    if _session is None or _model_spec != spec:
        model_path = _model_cache_path(spec)
        _download_model(spec, model_path)
        _session = _create_session(model_path)
        _model_spec = spec
        _model_ready = True
    return _session, _model_spec


def _preprocess_image(image: Image.Image, spec: ModelSpec) -> np.ndarray:
    rgb = image.convert("RGB").resize(
        (spec.input_size, spec.input_size),
        Image.Resampling.LANCZOS,
    )
    array = np.asarray(rgb, dtype=np.float32) / 255.0
    array = (array - spec.mean) / spec.std
    array = np.transpose(array, (2, 0, 1))
    return np.expand_dims(array, axis=0)


def _extract_embedding(output_values: list[Any], output_names: list[str]) -> np.ndarray:
    for name, value in zip(output_names, output_values, strict=True):
        if name in {"image_embeds", "pooler_output"}:
            return np.asarray(value[0], dtype=np.float32)

    array = np.asarray(output_values[0], dtype=np.float32)
    if array.ndim == 3:
        return array[0, 0]
    if array.ndim == 2:
        return array[0]
    raise ValueError("Unsupported ONNX model output shape for embedding extraction")


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def _run_batch(
    session: ort.InferenceSession,
    spec: ModelSpec,
    frames: list[SampledFrame],
) -> list[FrameFingerprint]:
    input_info = session.get_inputs()[0]
    input_name = input_info.name
    output_names = [output.name for output in session.get_outputs()]
    results: list[FrameFingerprint] = []

    for start in range(0, len(frames), ONNX_BATCH_SIZE):
        batch_frames = frames[start : start + ONNX_BATCH_SIZE]
        batch_input = np.concatenate(
            [_preprocess_image(frame.image, spec) for frame in batch_frames],
            axis=0,
        )
        try:
            outputs = session.run(output_names, {input_name: batch_input})
            for index, frame in enumerate(batch_frames):
                vector = _extract_embedding(
                    [output[index : index + 1] for output in outputs],
                    output_names,
                )
                vector = _normalize_vector(vector)
                results.append(
                    FrameFingerprint(
                        timestamp=frame.timestamp,
                        embedding=vector.astype(np.float32).tobytes(),
                    )
                )
        finally:
            del batch_input

    return results


class ONNXFingerprinter:
    """Embed sampled frames with a lightweight ONNX vision model."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name

    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        if not frames:
            return []

        session, spec = _get_session(self._model_name)
        usable_frames = [frame for frame in frames if not is_dark_frame(frame.image)]
        if not usable_frames:
            usable_frames = frames

        return _run_batch(session, spec, usable_frames)
