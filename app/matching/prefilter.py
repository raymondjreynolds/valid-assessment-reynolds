from typing import Protocol

from app.storage import StoredVideo


class CandidatePrefilter(Protocol):
    def prefilter(
        self,
        query: StoredVideo,
        candidates: list[StoredVideo],
    ) -> list[StoredVideo]:
        """Return a reduced candidate set before expensive visual scoring."""


class NoOpPrefilter:
    """Default prefilter that passes all cross-bucket candidates through."""

    def prefilter(
        self,
        query: StoredVideo,
        candidates: list[StoredVideo],
    ) -> list[StoredVideo]:
        return candidates
