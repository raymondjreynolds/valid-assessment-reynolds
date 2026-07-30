from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from app.config import FRAME_SIMILARITY_THRESHOLD
from app.fingerprints.base import FrameFingerprint, VideoFingerprinter
from app.frames import SampledFrame, is_dark_frame

if TYPE_CHECKING:
    from torchvision.models import VisionTransformer


_model: VisionTransformer | None = None
_transform: transforms.Compose | None = None


def _get_model() -> tuple[VisionTransformer, transforms.Compose]:
    global _model, _transform
    if _model is None or _transform is None:
        model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14")
        model.eval()
        transform = transforms.Compose(
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
        _model = model
        _transform = transform
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


def frame_similarity_threshold() -> float:
    return FRAME_SIMILARITY_THRESHOLD
