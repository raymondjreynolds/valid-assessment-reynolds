"""Temporal alignment and confidence scoring for vPDQ frame hashes."""

from dataclasses import dataclass

import threatengine

from app.config import MIN_ALIGNED_FRAMES, VPDQ_HAMMING_THRESHOLD
from app.fingerprints.base import FrameFingerprint


@dataclass(frozen=True)
class AlignmentResult:
    """Alignment quality metrics for one query/candidate vPDQ comparison."""

    confidence: float
    matched_frame_ratio: float
    alignment: str
    inlier_count: int


def _frame_pairs(
    query_frames: list[FrameFingerprint],
    candidate_frames: list[FrameFingerprint],
    *,
    hamming_threshold: int,
) -> list[tuple[float, float, float]]:
    pairs: list[tuple[float, float, float]] = []
    for query_frame in query_frames:
        if not query_frame.vpdq:
            continue

        best_distance = 256
        best_similarity = 0.0
        best_candidate: FrameFingerprint | None = None

        for candidate_frame in candidate_frames:
            if not candidate_frame.vpdq:
                continue
            distance, similarity = threatengine.pdq_similarity(
                query_frame.vpdq,
                candidate_frame.vpdq,
            )
            if distance < best_distance:
                best_distance = distance
                best_similarity = similarity
                best_candidate = candidate_frame

        if best_candidate is not None and best_distance <= hamming_threshold:
            pairs.append(
                (
                    query_frame.timestamp,
                    best_candidate.timestamp,
                    best_similarity,
                )
            )

    return pairs


def _best_frame_matches(
    query_frames: list[FrameFingerprint],
    candidate_frames: list[FrameFingerprint],
) -> list[tuple[float, int]]:
    """Return (best_similarity, best_hamming_distance) per query frame."""
    matches: list[tuple[float, int]] = []
    for query_frame in query_frames:
        if not query_frame.vpdq:
            continue

        best_distance = 256
        best_similarity = 0.0

        for candidate_frame in candidate_frames:
            if not candidate_frame.vpdq:
                continue
            distance, similarity = threatengine.pdq_similarity(
                query_frame.vpdq,
                candidate_frame.vpdq,
            )
            if distance < best_distance:
                best_distance = distance
                best_similarity = similarity

        matches.append((best_similarity, best_distance))

    return matches


def align_vpdq_fingerprints_fallback(
    query_frames: list[FrameFingerprint],
    candidate_frames: list[FrameFingerprint],
    *,
    hamming_threshold: int = VPDQ_HAMMING_THRESHOLD,
) -> AlignmentResult | None:
    """Score cross-bucket matches from best per-frame PDQ similarity without RANSAC."""
    if not query_frames or not candidate_frames:
        return None

    best_matches = _best_frame_matches(query_frames, candidate_frames)
    if not best_matches:
        return None

    matched_count = sum(
        1 for _, distance in best_matches if distance <= hamming_threshold
    )
    passing_similarities = [
        similarity
        for similarity, distance in best_matches
        if distance <= hamming_threshold
    ]
    if passing_similarities:
        mean_similarity = sum(passing_similarities) / len(passing_similarities)
    else:
        mean_similarity = sum(similarity for similarity, _ in best_matches) / len(
            best_matches
        )
    matched_frame_ratio = matched_count / len(query_frames)
    confidence = mean_similarity * matched_frame_ratio

    return AlignmentResult(
        confidence=confidence,
        matched_frame_ratio=matched_frame_ratio,
        alignment="fallback",
        inlier_count=matched_count,
    )


def _fit_line(points: list[tuple[float, float, float]]) -> tuple[float, float]:
    import numpy as np

    pair_array = np.asarray(points, dtype=np.float32)
    slope, intercept = np.polyfit(pair_array[:, 0], pair_array[:, 1], deg=1)
    return float(slope), float(intercept)


def _count_inliers(
    pair_array,
    slope: float,
    intercept: float,
    max_residual: float,
):
    import numpy as np

    predicted = slope * pair_array[:, 0] + intercept
    residuals = np.abs(pair_array[:, 1] - predicted)
    return residuals <= max_residual


def align_vpdq_fingerprints(
    query_frames: list[FrameFingerprint],
    candidate_frames: list[FrameFingerprint],
    *,
    hamming_threshold: int = VPDQ_HAMMING_THRESHOLD,
    min_aligned_frames: int = MIN_ALIGNED_FRAMES,
) -> AlignmentResult | None:
    """Align vPDQ hashes with RANSAC on timestamp offsets.

    Pairs frames by best Hamming distance under ``hamming_threshold``, then
    estimates a linear time warp between query and candidate timelines.
    """
    import numpy as np

    if not query_frames or not candidate_frames:
        return None

    pairs = _frame_pairs(
        query_frames,
        candidate_frames,
        hamming_threshold=hamming_threshold,
    )
    if len(pairs) < min_aligned_frames:
        return None

    pair_array = np.asarray(pairs, dtype=np.float32)
    best_inliers = None
    best_count = 0

    rng = np.random.default_rng(0)
    iterations = min(64, max(16, len(pairs) * 4))
    max_time_delta = max(
        1.0,
        float(max(query_frames, key=lambda frame: frame.timestamp).timestamp),
    )
    max_residual = max(0.75, max_time_delta * 0.15)

    for _ in range(iterations):
        sample = pair_array[rng.choice(len(pair_array), size=2, replace=False)]
        slope, intercept = _fit_line([tuple(row) for row in sample])
        inliers = _count_inliers(pair_array, slope, intercept, max_residual)
        count = int(inliers.sum())
        if count > best_count:
            best_count = count
            best_inliers = inliers

    if best_inliers is None or best_count < min_aligned_frames:
        return None

    inlier_pairs = pair_array[best_inliers]
    matched_frame_ratio = best_count / len(query_frames)
    mean_similarity = float(inlier_pairs[:, 2].mean())
    confidence = matched_frame_ratio * mean_similarity
    alignment = "full" if matched_frame_ratio >= 0.9 else "partial"

    return AlignmentResult(
        confidence=confidence,
        matched_frame_ratio=matched_frame_ratio,
        alignment=alignment,
        inlier_count=best_count,
    )
