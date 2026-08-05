from pydantic import BaseModel, Field


# Схема для однієї вакансії в результаті
class VacancyMatch(BaseModel):
    vacancy_id: int
    match: bool = Field(description="Does the job match the user's request")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the answer from 0.0 to 1.0"
    )
    reason: str = Field(
        description="Explanation in Ukrainian why the vacancy matches or not"
    )


# Обгортка для списку результатів (Batch-схема)
class BatchFilterResponse(BaseModel):
    evaluations: list[VacancyMatch] = Field(
        description="List of ratings for each given job"
    )


class Profile(BaseModel):
    id: int
    user_id: int
    query_text: str
    cv_file: str | None
    mime_type: str | None


class LLMCandidate(BaseModel):
    profile_data: Profile
    vacancies: list[dict]


class MatchData(BaseModel):
    user_id: int
    profile_id: int
    vacancy_id: int
    semantic_score: float | None
    confidence: float | None
    reason: str
