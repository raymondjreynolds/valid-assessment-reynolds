from dataclasses import dataclass

import numpy as np

from app.config import FRAME_SIMILARITY_THRESHOLD, MIN_ALIGNED_FRAMES
from app.fingerprints.base import FrameFingerprint, frame_embedding_vector, has_frame_embedding


@dataclass(frozen=True)
class AlignmentResult:
    confidence: float
    matched_frame_ratio: float
    alignment: str
    inlier_count: int


def _normalize_embeddings(fingerprints: list[FrameFingerprint]) -> np.ndarray:
    vectors = [
        frame_embedding_vector(frame)
        for frame in fingerprints
        if has_frame_embedding(frame)
    ]
    if not vectors:
        return np.empty((0, 0), dtype=np.float32)

    matrix = np.stack(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _fit_line(points: np.ndarray) -> tuple[float, float]:
    query_times = points[:, 0]
    candidate_times = points[:, 1]
    slope, intercept = np.polyfit(query_times, candidate_times, deg=1)
    return float(slope), float(intercept)


def _count_inliers(
    pairs: np.ndarray,
    slope: float,
    intercept: float,
    max_residual: float,
) -> np.ndarray:
    predicted = slope * pairs[:, 0] + intercept
    residuals = np.abs(pairs[:, 1] - predicted)
    return residuals <= max_residual


def align_fingerprints(
    query_frames: list[FrameFingerprint],
    candidate_frames: list[FrameFingerprint],
    *,
    similarity_threshold: float = FRAME_SIMILARITY_THRESHOLD,
    min_aligned_frames: int = MIN_ALIGNED_FRAMES,
) -> AlignmentResult | None:
    if not query_frames or not candidate_frames:
        return None

    query_frames = [frame for frame in query_frames if has_frame_embedding(frame)]
    candidate_frames = [frame for frame in candidate_frames if has_frame_embedding(frame)]
    if not query_frames or not candidate_frames:
        return None

    query_embeddings = _normalize_embeddings(query_frames)
    candidate_embeddings = _normalize_embeddings(candidate_frames)
    similarity_matrix = query_embeddings @ candidate_embeddings.T

    pairs: list[tuple[float, float, float]] = []
    for index, query_frame in enumerate(query_frames):
        candidate_index = int(np.argmax(similarity_matrix[index]))
        similarity = float(similarity_matrix[index, candidate_index])
        if similarity < similarity_threshold:
            continue
        candidate_frame = candidate_frames[candidate_index]
        pairs.append(
            (
                query_frame.timestamp,
                candidate_frame.timestamp,
                similarity,
            )
        )

    if len(pairs) < min_aligned_frames:
        return None

    pair_array = np.asarray(pairs, dtype=np.float32)
    best_inliers: np.ndarray | None = None
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
        slope, intercept = _fit_line(sample)
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
