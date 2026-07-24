import logging
import os
from datetime import datetime
from typing import Sequence

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import RowMapping

from db.crud import (
    get_active_users_profiles,
    save_match,
    get_vac_ids_since_date, load_semantic_matches_for_vacancies_id_list,
    load_vacancies_by_id_list, update_profile_embeddings, update_vacancy_embeddings,
    load_no_embedding_for_vacancies_id_list, load_semantic_matches_and_no_embedded_vacancies_from_id_list,
)
from db.models import UserProfile
from db.session import get_db
from common_settings import setup_logging, current_model_name

setup_logging()
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

def filter_vacancies_by_keywords(vacancies: Sequence[RowMapping], include: list, exclude: list) -> list[RowMapping]:
    vacancies_list = [
        vacancy
        for vacancy
        in vacancies
        if keyword_filter(vacancy.title, include, exclude)
    ]
    return vacancies_list



def filter_vacancies(model: SentenceTransformer | None) -> None:
    if model is None:
        model = SentenceTransformer(current_model_name)
    with get_db() as db:
        updated_profiles = update_profile_embeddings(db=db, model=model, current_model_name=current_model_name)
        updated_vacancies = update_vacancy_embeddings(db=db, model=model, current_model_name=current_model_name)

        logger.info("Updated profiles.embeddings: {}, vacancies.embeddings: {}".format(updated_profiles, updated_vacancies))
        profiles: Sequence[UserProfile] = get_active_users_profiles(db)
        logger.info("Знайдено профайлів {}".format(len(profiles)))
        if not profiles:
            logger.info("No active profiles in user_profiles. Nothing to process.")
            return
        num_matches = 0

        for profile in profiles:
            vacancies_id: Sequence[int] = get_vac_ids_since_date(db, profile.last_matched_at)
            logger.info("Нових вакансій для матчингу {}".format(len(vacancies_id)))
            if not vacancies_id:
                continue

            if profile.embedding:
                # vacancy.embedding is not None
                # long version
                semantic_filtered_vacancies: Sequence[RowMapping] = load_semantic_matches_for_vacancies_id_list(db, profile, vacancies_id)
                num_semantic_filtered_vacancies = len(semantic_filtered_vacancies)
                logger.info(
                    "Знайдено %s підходящих вакансій за семантичною ознакою для профіля %s",
                    num_semantic_filtered_vacancies, profile.id
                )
                keyword_filtered_vacancies_with_embedding = filter_vacancies_by_keywords(semantic_filtered_vacancies, profile.include_keywords, profile.exclude_keywords)
                num_filtered_vacancies_1 = len(keyword_filtered_vacancies_with_embedding)
                num_rejected_1 = num_semantic_filtered_vacancies - num_filtered_vacancies_1

                logger.info(
                    "Відсіяно %s з %s попередньо семантично відфільтрованих за keyword_filter для профіля %s",
                    num_rejected_1, num_filtered_vacancies_1, profile.id
                )
                # vacancy.embedding is None
                no_embedding_vacancies: Sequence[RowMapping] = load_no_embedding_for_vacancies_id_list(db, vacancies_id)
                num_no_embedding_vacancies = len(no_embedding_vacancies)
                logger.info(
                    "Знайдено %s вакансій без embedding для профіля %s",
                    num_no_embedding_vacancies, profile.id
                )
                keyword_filtered_vacancies_no_embedding = filter_vacancies_by_keywords(
                    semantic_filtered_vacancies,
                    profile.include_keywords,
                    profile.exclude_keywords
                )

                num_filtered_vacancies_2 = len(keyword_filtered_vacancies_no_embedding)
                num_rejected_2 = num_no_embedding_vacancies - num_filtered_vacancies_2

                logger.info(
                    "Відсіяно %s з %s вакансій (без embedding) за keyword_filter для профіля %s",
                    num_rejected_2, num_no_embedding_vacancies, profile.id
                )
                full_filtered_vacancies = keyword_filtered_vacancies_with_embedding + keyword_filtered_vacancies_no_embedding
                num_filtered_vacancies = len(full_filtered_vacancies)
                # # short version
                # vacancies = load_semantic_matches_and_no_embedded_vacancies_from_id_list(db, profile, vacancies_id)
                # logger.info(
                #     "Знайдено %s вакансій для профіля %s",
                #     len(vacancies), profile.id
                # )
                # full_filtered_vacancies = filter_vacancies_by_keywords(vacancies, profile.include_keywords, profile.exclude_keywords)
                # num_filtered_vacancies = len(full_filtered_vacancies)

            else:
                vacancies: Sequence[RowMapping] = load_vacancies_by_id_list(db=db, vac_ids=vacancies_id)
                logger.info(
                    "Знайдено %s вакансій для профіля %s",
                    len(vacancies), profile.id
                )
                full_filtered_vacancies = filter_vacancies_by_keywords(vacancies, profile.include_keywords, profile.exclude_keywords)
                num_vacancies = len(vacancies)
                num_filtered_vacancies = len(full_filtered_vacancies)
                num_rejected = num_vacancies - num_filtered_vacancies
                logger.info(
                    "Відсіяно %s з %s за keyword_filter для профіля %s",
                    num_rejected, num_vacancies, profile.id
                )
            num_matches += num_filtered_vacancies
            for v in full_filtered_vacancies:
                save_match(
                    db=db,
                    profile=profile,
                    vacancy_id=v["id"],
                    semantic=v.get("semantic_score")
                )
            profile.last_matched_at = datetime.now()
        logger.info("Всього за сесію додано %s збігів", num_matches)



if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")


    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    filter_vacancies()
