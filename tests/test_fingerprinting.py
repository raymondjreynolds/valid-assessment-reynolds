from app.fingerprinting import get_fingerprinter


def test_default_fingerprinter_is_vpdq():
    fingerprinter = get_fingerprinter("vpdq")
    assert fingerprinter.__class__.__name__ == "VPDQFingerprinter"
