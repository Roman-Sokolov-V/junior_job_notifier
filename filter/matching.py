import logging
import os
from typing import Sequence

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import RowMapping

from db.crud import (
    get_active_users_profiles,
    get_vac_ids_since_date,
    load_semantic_matches_for_vacancies_id_list,
    load_vacancies_by_id_list,
    update_profile_embeddings,
    update_vacancy_embeddings,
    get_db_now,
    save_matches_bulk,
)
from db.models import UserProfile
from db.session import get_db
from common_settings import setup_logging, current_model_name, LLM_MODEL_NAME
from filter.gemini_filter import get_matches_list_for_all_profiles
from filter.schemas import LLMCandidate, MatchData, Profile

logger = logging.getLogger(__name__)


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def to_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def keyword_filter(title: str, include: list[str], exclude: list[str]) -> bool:
    """
    Повертає False якщо False якщо принаймні одне слово зі списку exclude
    присутнє в title, або жодне зі списку include відсутнє, інакше True
    """
    norm_title = normalize_text(title)
    title_words = set(norm_title.split())

    if exclude:
        exclude_set: set = {normalize_text(word) for word in exclude}
        if exclude_set and exclude_set.intersection(title_words):
            return False

    if include:
        include_set: set = {normalize_text(word) for word in include}
        if include_set and not include_set.intersection(title_words):
            return False
    return True


def filter_vacancies_by_keywords(
    vacancies: Sequence[RowMapping], include: list, exclude: list
) -> list[dict]:
    vacancies_list = [
        dict(vacancy)
        for vacancy in vacancies
        if keyword_filter(vacancy.title, include, exclude)
    ]
    return vacancies_list


async def filter_vacancies(model: SentenceTransformer | None = None) -> None:
    if model is None:
        model = SentenceTransformer(current_model_name)
    with get_db() as db:
        run_started_at = get_db_now(db)
        updated_profiles = update_profile_embeddings(
            db=db, model=model, current_model_name=current_model_name
        )
        updated_vacancies = update_vacancy_embeddings(
            db=db, model=model, current_model_name=current_model_name
        )

        logger.info(
            "Updated profiles.embeddings: %s, vacancies.embeddings: %s",
            updated_profiles,
            updated_vacancies,
        )
        profiles: Sequence[UserProfile] = get_active_users_profiles(db)
        logger.info("Знайдено профайлів {}".format(len(profiles)))
        if not profiles:
            logger.info("No active profiles in user_profiles. Nothing to process.")
            return

        matches = []
        candidates_llm_filtering = []
        for profile in profiles:
            vacancies_id: Sequence[int] = get_vac_ids_since_date(
                db, profile.last_matched_at
            )
            logger.info("Нових вакансій для матчингу %s", len(vacancies_id))
            if not vacancies_id:
                continue

            if profile.embedding:
                vacancies: Sequence[RowMapping] = (
                    load_semantic_matches_for_vacancies_id_list(
                        db, profile, vacancies_id
                    )
                )
                num_vacancies = len(vacancies)
                logger.info(
                    "Знайдено %s вакансій за семантичною дистанцією для профіля %s",
                    num_vacancies,
                    profile.id,
                )
                full_filtered_vacancies = filter_vacancies_by_keywords(
                    vacancies, profile.include_keywords, profile.exclude_keywords
                )
                num_filtered_vacancies = len(full_filtered_vacancies)
                logger.info(
                    "Відсіяно %s з %s вакансій за keyword_filter для профіля %s",
                    num_vacancies - num_filtered_vacancies,
                    num_vacancies,
                    profile.id,
                )
                logger.info(
                    "Всього %s вакансій відправляються на фільтрацію LLM для профіля %s",
                    num_filtered_vacancies,
                    profile.id,
                )
                profile_data = Profile(
                    id=profile.id,
                    user_id=profile.user_id,
                    query_text=profile.query_text,
                )
                candidates_llm_filtering.append(
                    LLMCandidate(
                        profile=profile_data, vacancies=full_filtered_vacancies
                    )
                )
            else:
                vacancies: Sequence[RowMapping] = load_vacancies_by_id_list(
                    db=db, vac_ids=vacancies_id
                )
                num_vacancies = len(vacancies)
                logger.info(
                    "Знайдено %s вакансій для профіля %s", num_vacancies, profile.id
                )
                full_filtered_vacancies = filter_vacancies_by_keywords(
                    vacancies, profile.include_keywords, profile.exclude_keywords
                )
                num_filtered_vacancies = len(full_filtered_vacancies)
                logger.info(
                    "Відсіяно %s з %s за keyword_filter для профіля %s",
                    num_vacancies - num_filtered_vacancies,
                    num_vacancies,
                    profile.id,
                )
                keyword_matches = [
                    MatchData(
                        user_id=profile.user_id,
                        profile_id=profile.id,
                        vacancy_id=v["id"],
                        semantic_score=None,
                        confidence=None,
                        reason="keyword_filter",
                    )
                    for v in full_filtered_vacancies
                ]
                matches.extend(keyword_matches)
                profile.last_matched_at = run_started_at
            llm_matches: list[MatchData] = await get_matches_list_for_all_profiles(
                candidates_llm_filtering, LLM_MODEL_NAME
            )
            logger.info("-----------LLM matches: %s--------------", len(llm_matches))
            matches.extend(llm_matches)
            save_matches_bulk(db, matches)
            logger.info("Всього за сесію додано %s збігів", len(matches))


if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    setup_logging()
    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    filter_vacancies()
