import gc

from app.config import FINGERPRINT_METHOD


def release_inference_resources() -> None:
    """Drop loaded neural models that matching does not need."""
    if FINGERPRINT_METHOD == "onnx":
        from app.fingerprints.onnx_embedder import release_onnx_session

        release_onnx_session()
    gc.collect()
