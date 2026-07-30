from dataclasses import dataclass

from app.config import MATCH_CONFIDENCE_THRESHOLD
from app.matching.align import align_fingerprints
from app.storage import StoredVideo


@dataclass(frozen=True)
class MatchResult:
    video_id: str
    ratio_bucket: str
    confidence: float
    matched_frame_ratio: float
    alignment: str
    method: str = "dinov2"


def score_match(query: StoredVideo, candidate: StoredVideo) -> MatchResult | None:
    if query.fingerprints.is_empty or candidate.fingerprints.is_empty:
        return None

    alignment = align_fingerprints(
        query.fingerprints.frames,
        candidate.fingerprints.frames,
    )
    if alignment is None:
        return None

    if alignment.confidence < MATCH_CONFIDENCE_THRESHOLD:
        return None

    return MatchResult(
        video_id=candidate.video_id,
        ratio_bucket=candidate.ratio_bucket,
        confidence=round(alignment.confidence, 4),
        matched_frame_ratio=round(alignment.matched_frame_ratio, 4),
        alignment=alignment.alignment,
    )
