from app.matching.prefilter import CandidatePrefilter, NoOpPrefilter
from app.matching.score import MatchResult, score_match
from app.storage import StoredVideo, VideoStore


class VideoMatcher:
    def __init__(
        self,
        store: VideoStore,
        prefilter: CandidatePrefilter | None = None,
    ) -> None:
        self._store = store
        self._prefilter = prefilter or NoOpPrefilter()

    def get_cross_bucket_candidates(self, query: StoredVideo) -> list[StoredVideo]:
        return [
            video
            for video in self._store.list_all()
            if video.video_id != query.video_id
            and video.ratio_bucket != query.ratio_bucket
            and video.fingerprint_status.is_ready()
            and not video.fingerprints.is_empty
        ]

    def match(self, video_id: str) -> list[MatchResult]:
        query = self._store.get(video_id)
        if query is None:
            raise KeyError(f"Video {video_id} not found")

        from app.fingerprint_readiness import ensure_all_fingerprints_ready

        ensure_all_fingerprints_ready(self._store)

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
    return VideoMatcher(store=store, prefilter=NoOpPrefilter())
