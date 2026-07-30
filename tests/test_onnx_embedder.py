from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from app.frames import SampledFrame
from app.fingerprints.onnx_embedder import (
    MODEL_SPECS,
    ONNXFingerprinter,
    _extract_embedding,
    _normalize_vector,
    _preprocess_image,
    _resolve_model_spec,
)


def test_resolve_model_spec_supports_mobilenet_and_clip():
    assert _resolve_model_spec("mobilenet").name == "mobilenet"
    assert _resolve_model_spec("clip").name == "clip"


def test_resolve_model_spec_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unsupported ONNX model"):
        _resolve_model_spec("unknown")


def test_preprocess_image_produces_nchw_batch():
    spec = MODEL_SPECS["mobilenet"]
    image = Image.new("RGB", (384, 384), color=(128, 64, 32))

    tensor = _preprocess_image(image, spec)

    assert tensor.shape == (1, 3, 224, 224)


def test_extract_embedding_uses_cls_token_for_sequence_output():
    output = np.ones((1, 50, 768), dtype=np.float32)
    output[0, 0, 0] = 9.0

    vector = _extract_embedding([output], ["last_hidden_state"])

    assert vector.shape == (768,)
    assert vector[0] == 9.0


def test_normalize_vector_unit_length():
    vector = _normalize_vector(np.asarray([3.0, 4.0], dtype=np.float32))

    assert pytest.approx(float(np.linalg.norm(vector)), rel=1e-6) == 1.0


def test_onnx_fingerprinter_emits_normalized_embeddings(monkeypatch):
    session = MagicMock()
    input_info = MagicMock()
    input_info.name = "input"
    session.get_inputs.return_value = [input_info]
    session.get_outputs.return_value = [MagicMock(name="output")]
    session.run.return_value = [np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)]

    spec = MODEL_SPECS["mobilenet"]
    monkeypatch.setattr(
        "app.fingerprints.onnx_embedder._get_session",
        lambda model_name=None: (session, spec),
    )

    frames = [
        SampledFrame(timestamp=0.0, image=Image.new("RGB", (64, 64), (255, 0, 0))),
        SampledFrame(timestamp=1.0, image=Image.new("RGB", (64, 64), (0, 255, 0))),
    ]
    results = ONNXFingerprinter().fingerprint(frames)

    assert len(results) == 2
    assert results[0].dinov2 is not None
    assert pytest.approx(np.linalg.norm(results[0].dinov2), rel=1e-6) == 1.0


def test_get_fingerprinter_supports_onnx():
    from app.fingerprinting import get_fingerprinter

    fingerprinter = get_fingerprinter("onnx")
    assert fingerprinter.__class__.__name__ == "ONNXFingerprinter"
