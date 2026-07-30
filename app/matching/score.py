from dataclasses import dataclass

from app.matching.align import align_fingerprints
from app.matching.align_vpdq import align_vpdq_fingerprints, align_vpdq_fingerprints_fallback
from app.storage import StoredVideo


@dataclass(frozen=True)
class MatchResult:
    video_id: str
    filename: str
    confidence: float


def score_match(query: StoredVideo, candidate: StoredVideo) -> MatchResult | None:
    if query.fingerprints.is_empty or candidate.fingerprints.is_empty:
        return None

    method = query.fingerprint_method
    if method == "vpdq":
        alignment = align_vpdq_fingerprints(
            query.fingerprints.frames,
            candidate.fingerprints.frames,
        )
        if alignment is None:
            alignment = align_vpdq_fingerprints_fallback(
                query.fingerprints.frames,
                candidate.fingerprints.frames,
            )
    elif method in {"dinov2", "onnx"}:
        alignment = align_fingerprints(
            query.fingerprints.frames,
            candidate.fingerprints.frames,
        )
    else:
        raise ValueError(f"Unsupported fingerprint method: {method}")

    if alignment is None:
        return None

    return MatchResult(
        video_id=candidate.video_id,
        filename=candidate.filename,
        confidence=round(alignment.confidence, 4),
    )
