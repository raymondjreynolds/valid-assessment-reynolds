from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch
from torchvision import transforms

from app.config import TORCH_NUM_THREADS
from app.fingerprints.base import FrameFingerprint
from app.frames import SampledFrame, is_dark_frame

if TYPE_CHECKING:
    from torchvision.models import VisionTransformer

torch.set_num_threads(TORCH_NUM_THREADS)

_model: VisionTransformer | None = None
_transform: transforms.Compose | None = None
_model_loading = False
_model_ready = False


def _build_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225),
            ),
        ]
    )


def preload_dinov2() -> None:
    """Load DINOv2 weights once so fingerprint jobs do not pay cold-start cost."""
    global _model_loading
    if _model_ready or _model_loading:
        return
    _model_loading = True
    try:
        _get_model()
    finally:
        _model_loading = False


def is_model_ready() -> bool:
    return _model_ready


def _get_model() -> tuple[VisionTransformer, transforms.Compose]:
    global _model, _transform, _model_ready
    if _model is None or _transform is None:
        model = torch.hub.load(
            "facebookresearch/dinov2",
            "dinov2_vits14",
            verbose=False,
        )
        model.eval()
        _model = model
        _transform = _build_transform()
        _model_ready = True
    return _model, _transform


class DINOv2Fingerprinter:
    def fingerprint(self, frames: list[SampledFrame]) -> list[FrameFingerprint]:
        if not frames:
            return []

        model, transform = _get_model()
        usable_frames = [frame for frame in frames if not is_dark_frame(frame.image)]
        if not usable_frames:
            usable_frames = frames

        batch = torch.stack([transform(frame.image) for frame in usable_frames])
        with torch.inference_mode():
            embeddings = model(batch)
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        vectors = embeddings.cpu().numpy()
        return [
            FrameFingerprint(
                timestamp=frame.timestamp,
                dinov2=vector.astype(np.float32).tolist(),
            )
            for frame, vector in zip(usable_frames, vectors, strict=True)
        ]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    vec_a = np.asarray(a, dtype=np.float32)
    vec_b = np.asarray(b, dtype=np.float32)
    return float(np.dot(vec_a, vec_b))
