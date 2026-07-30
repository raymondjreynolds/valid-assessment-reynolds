from dataclasses import dataclass

from app.matching.align import align_fingerprints
from app.matching.align_vpdq import align_vpdq_fingerprints, align_vpdq_fingerprints_fallback
from app.storage import StoredVideo


@dataclass(frozen=True)
class MatchResult:
    video_id: str
    ratio_bucket: str
    confidence: float
    matched_frame_ratio: float
    alignment: str
    method: str = "vpdq"


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
    elif method == "dinov2":
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
        ratio_bucket=candidate.ratio_bucket,
        confidence=round(alignment.confidence, 4),
        matched_frame_ratio=round(alignment.matched_frame_ratio, 4),
        alignment=alignment.alignment,
        method=method,
    )
