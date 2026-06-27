import logging
import os
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

from scrap_vac.db.crud import get_active_users_profiles, get_vacancies_since_date, get_last_run, save_match
from scrap_vac.db.models import MatcherState
from scrap_vac.db.schemas import VacancyRow, ProfileRow
from scrap_vac.db.session import get_db

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
STATE_KEY = "last_match_run_at"



def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def to_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def set_last_run(db: Session, ts: datetime) -> None:
    upsert = insert(MatcherState).values(key=STATE_KEY, value=ts.isoformat())
    upsert = upsert.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": upsert.excluded.value, "updated_at": func.now()},
    )
    db.execute(upsert)


def load_new_vacancies(since_ts: datetime) -> list[VacancyRow]:
    with get_db() as db:
        rows = get_vacancies_since_date(db, since_ts)
    return [
        VacancyRow(
            id=v.id,
            source=v.source or "",
            title=v.title or "",
            url=v.url or "",
            listing_context=v.listing_context or "",
            description_text=v.description_text or "",
            added_at=v.added_at,
        )
        for v in rows
    ]


def load_profiles() -> list[ProfileRow]:
    with get_db() as db:
        profiles = get_active_users_profiles(db)
    return [
        ProfileRow(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            query_text=p.query_text,
            include_keywords=to_str_list(p.include_keywords),
            exclude_keywords=to_str_list(p.exclude_keywords),
            min_keyword_coverage=float(p.min_keyword_coverage),
            min_semantic_score=float(p.min_semantic_score),
            top_k=int(p.top_k),
        )
        for p in profiles
    ]


def keyword_filter(title: str, text: str, include: list[str], exclude: list[str], min_coverage: float) -> tuple[bool, float]:
    # normalization
    norm_title = normalize_text(title)
    norm_text = normalize_text(text)

    include_norm = [normalize_text(word) for word in include]
    exclude_norm = [normalize_text(word) for word in exclude]

    # if any word from exclude list in title remove immediately
    if exclude_norm and any(word in norm_title for word in exclude_norm):
        return False, 0.0

    if not include_norm:
        return True, 1.0

    hits = sum(1 for word in include_norm if word in norm_text)
    coverage = hits / len(include_norm)
    return coverage >= min_coverage, coverage

#
# def save_match(profile: ProfileRow, vacancy_id: int, coverage: float, semantic: float, combined: float) -> None:
#     reason = {
#         "profile_name": profile.name,
#         "keyword_coverage": round(coverage, 4),
#         "semantic_score": round(semantic, 4),
#         "combined_score": round(combined, 4),
#     }
#     upsert = insert(UserMatch).values(
#         user_id=profile.user_id,
#         profile_id=profile.id,
#         vacancy_id=vacancy_id,
#         keyword_coverage=coverage,
#         semantic_score=semantic,
#         combined_score=combined,
#         reason_json=reason,
#     )
#     upsert = upsert.on_conflict_do_update(
#         constraint="uq_user_matches_profile_vacancy",
#         set_={
#             "keyword_coverage": upsert.excluded.keyword_coverage,
#             "semantic_score": upsert.excluded.semantic_score,
#             "combined_score": upsert.excluded.combined_score,
#             "reason_json": upsert.excluded.reason_json,
#         },
#     )
#     with get_db() as db:
#         db.execute(upsert)


def filter_vacancies() -> None:
    with get_db() as db:
        last_run = get_last_run(db=db, key=STATE_KEY)

    vacancies = load_new_vacancies(last_run)
    profiles = load_profiles()
    if not profiles:
        print("No active profiles in user_profiles. Nothing to process.")
        return
    if not vacancies:
        print("No new vacancies since last matcher run.")
        return

    model = SentenceTransformer(MODEL_NAME)
    vacancy_texts = [vac.full_text for vac in vacancies] # список текстів вакансій
    vacancy_embeddings = model.encode(vacancy_texts, convert_to_tensor=True)
    total_saved = 0

    for profile in profiles:
        query_embedding = model.encode(profile.query_text, convert_to_tensor=True)
        similarities = util.cos_sim(query_embedding, vacancy_embeddings)[0]  # Returns: Tensor: Matrix with res[i][j] = cos_sim(a[i], b[j])
        print(profile.include_keywords)
        print(profile.exclude_keywords)
        print(similarities)

        candidates: list[tuple[int, float, float, float]] = []
        for idx, vacancy in enumerate(vacancies):
            ok, coverage = keyword_filter(
                vacancy.title,
                vacancy.full_text,
                profile.include_keywords,
                profile.exclude_keywords,
                profile.min_keyword_coverage,
            )
            if not ok:
                print("not ok")
                continue

            semantic = float(similarities[idx])
            if semantic < profile.min_semantic_score:
                continue
            combined = 0.7 * semantic + 0.3 * coverage
            candidates.append((vacancy.id, coverage, semantic, combined))

        candidates.sort(key=lambda row: row[3], reverse=True)
        for vacancy_id, coverage, semantic, combined in candidates[: profile.top_k]:
            with get_db() as db:
                save_match(db, profile, vacancy_id, coverage, semantic, combined)
            total_saved += 1

    newest_added_at = max(v.added_at for v in vacancies)
    set_last_run(db, newest_added_at)

    print(f"Processed new vacancies: {len(vacancies)}")
    print(f"Processed active profiles: {len(profiles)}")
    print(f"Saved/updated matches: {total_saved}")
    print(f"Updated state {STATE_KEY} -> {newest_added_at.isoformat()}")




if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    filter_vacancies()
