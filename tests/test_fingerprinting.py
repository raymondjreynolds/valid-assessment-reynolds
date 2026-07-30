from app.fingerprinting import get_fingerprinter


def test_default_fingerprinter_is_onnx():
    fingerprinter = get_fingerprinter()
    assert fingerprinter.__class__.__name__ == "ONNXFingerprinter"


def test_vpdq_fingerprinter_still_available():
    fingerprinter = get_fingerprinter("vpdq")
    assert fingerprinter.__class__.__name__ == "VPDQFingerprinter"
