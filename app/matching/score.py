"""Match confidence scoring for one query/candidate pair."""

from dataclasses import dataclass

from app.config import MATCH_CONFIDENCE_THRESHOLD
from app.matching.align import align_fingerprints
from app.matching.align_vpdq import align_vpdq_fingerprints, align_vpdq_fingerprints_fallback
from app.storage import StoredVideo


@dataclass(frozen=True)
class MatchResult:
    """Public match payload fields returned by ``GET /match``."""

    video_id: str
    filename: str
    confidence: float


def score_match(query: StoredVideo, candidate: StoredVideo) -> MatchResult | None:
    """Align fingerprints and return a match when confidence meets the threshold.

    Uses the query video's fingerprint method. vPDQ tries temporal RANSAC first,
    then falls back to best per-frame similarity when reframing breaks alignment.
    """
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

    if alignment.confidence < MATCH_CONFIDENCE_THRESHOLD:
        return None

    return MatchResult(
        video_id=candidate.video_id,
        filename=candidate.filename,
        confidence=round(alignment.confidence, 4),
    )
