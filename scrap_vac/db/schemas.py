from dataclasses import dataclass
from datetime import datetime


@dataclass
class VacancyRow:
    id: int
    source: str
    title: str
    url: str
    listing_context: str
    description_text: str
    added_at: datetime

    @property
    def full_text(self) -> str:
        parts = [self.title, self.listing_context, self.description_text]
        return "\n".join(part for part in parts if part)


@dataclass
class ProfileRow:
    id: int
    user_id: int
    name: str
    query_text: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    min_keyword_coverage: float
    min_semantic_score: float
    top_k: int
