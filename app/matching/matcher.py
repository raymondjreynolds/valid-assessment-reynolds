"""Cross-bucket video matching orchestration."""

from app.fingerprint_readiness import ensure_query_fingerprint_ready
from app.fingerprint_retries import maybe_retry_failed_candidates
from app.matching.prefilter import CandidatePrefilter, NoOpPrefilter
from app.matching.score import MatchResult, score_match
from app.storage import StoredVideo, VideoStore
from app.video import is_matchable_ratio_bucket


class VideoMatcher:
    """Find visually similar videos in different aspect-ratio buckets."""

    def __init__(
        self,
        store: VideoStore,
        prefilter: CandidatePrefilter | None = None,
    ) -> None:
        self._store = store
        self._prefilter = prefilter or NoOpPrefilter()

    def get_cross_bucket_candidates(self, query: StoredVideo) -> list[StoredVideo]:
        """Return ready, fingerprinted videos in a different ratio bucket than the query."""
        if not is_matchable_ratio_bucket(query.ratio_bucket):
            return []

        return [
            video
            for video in self._store.list_all()
            if video.video_id != query.video_id
            and video.ratio_bucket != query.ratio_bucket
            and is_matchable_ratio_bucket(video.ratio_bucket)
            and video.fingerprint_status.is_ready()
            and not video.fingerprints.is_empty
        ]

    def match(self, video_id: str) -> list[MatchResult]:
        """Score cross-bucket candidates and return matches above the confidence threshold.

        Results are sorted by confidence descending. Pending or failed unrelated
        uploads are ignored; only the query video can block with 202/503.
        """
        query = self._store.get(video_id)
        if query is None:
            raise KeyError(f"Video {video_id} not found")

        ensure_query_fingerprint_ready(query, self._store)
        maybe_retry_failed_candidates(query, self._store)

        candidates = self.get_cross_bucket_candidates(query)
        candidates = self._prefilter.prefilter(query, candidates)

        matches: list[MatchResult] = []
        for candidate in candidates:
            result = score_match(query, candidate)
            if result is not None:
                matches.append(result)

        matches.sort(key=lambda match: match.confidence, reverse=True)
        return matches


def default_matcher(store: VideoStore) -> VideoMatcher:
    """Construct the production matcher with no candidate prefilter."""
    return VideoMatcher(store=store, prefilter=NoOpPrefilter())
