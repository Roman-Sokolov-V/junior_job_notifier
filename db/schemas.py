from dataclasses import dataclass
from datetime import datetime

from pgvector import Vector


@dataclass
class VacancyRow:
    id: int
    source: str
    title: str
    url: str
    listing_context: str
    description_text: str
    added_at: datetime
    embedding: Vector | None
    embedding_model: str | None

    @property
    def full_text(self) -> str:
        parts = [self.title, self.listing_context, self.description_text]
        return "\n".join(part for part in parts if part)


@dataclass
class VacancyIdRow:
    id: int


@dataclass
class ProfileRow:
    def __init__(self):
        self.last_matched_at = None

    id: int
    user_id: int
    name: str
    query_text: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    min_semantic_score: float
    embedding: Vector | None
    embedding_model: str | None
    last_matched_at: datetime



@dataclass
class MatchCandidate:
    vacancy_id: int
    keyword_coverage: float
    semantic_score: float
    combined_score: float