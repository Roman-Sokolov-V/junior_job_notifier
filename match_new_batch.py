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


def keyword_filter(title: str, text: str, include: list[str], exclude: list[str], min_coverage: float) -> tuple[
    bool, float]:
    """Функція відфільтровує вакансії в яких в title відсутнє жодне слово зі списку include
    а також, ті в які в title присутнє принаймні одне слово зі списку exclude
    Якщо ці перевірки пройдені, повертає True, 0.0 якщо відсутні слова в include
    Інакше True, num: float  де  0 < num < 1   оцінка частоти зустрічи слів з include в text
    """
    # 1. Нормалізація
    norm_title = normalize_text(title)

    # Створюємо сети для миттєвого і точного пошуку по словах в title
    title_words = set(norm_title.split())

    include_norm = [normalize_text(word) for word in include]
    exclude_set = set(normalize_text(word) for word in exclude)

    # 2. Перевірка EXCLUDE (якщо є хоч одне слово в title -> видаляємо)
    if exclude_set and exclude_set.intersection(title_words):
        return False, 0.0

    # 3. Перевірка порожнього INCLUDE
    if not include_norm:
        return True, 0.0

    # 4. Перевірка INCLUDE в title (має бути хоча б ОДНЕ слово з include)
    # Використовуємо any(word in norm_title), бо в include можуть бути фрази типу "data science"
    if not any(word in norm_title for word in include_norm):
        return False, 0.0

    # 5. Рахуємо покриття (coverage) в ТЕКСТІ вакансії
    norm_text = normalize_text(text)
    # розбиваємо текст на слова для захисту від багу з "js" -> "json"
    text_words = set(norm_text.split())

    hits = sum(1 for word in include_norm if word in text_words)
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
        if profile.query_text:
            query_embedding = model.encode(profile.query_text, convert_to_tensor=True)
            similarities = util.cos_sim(query_embedding, vacancy_embeddings)[0]  # Returns: Tensor: Matrix with res[i][j] = cos_sim(a[i], b[j])


        candidates: list[tuple[int, float, float, float]] = []
        for idx, vacancy in enumerate(vacancies):
            ok, key_word_coverage = keyword_filter(
                vacancy.title,
                vacancy.full_text,
                profile.include_keywords,
                profile.exclude_keywords,
                profile.min_keyword_coverage,
            )
            if not ok:
                print("not passed keyword filter")
                continue
            if not profile.query_text:
                candidates.append((vacancy.id, key_word_coverage, 0.0, 0.0))
            else:
                semantic = float(similarities[idx])  #  обираємо потрібний semantic з матриці similarities за індексом вакансії
                combined = semantic + key_word_coverage
                if combined < profile.min_semantic_score:
                    continue
                candidates.append((vacancy.id, key_word_coverage, semantic, combined))

        # candidates.sort(key=lambda row: row[3], reverse=True)
        # for vacancy_id, kew_word_coverage, semantic, combined in candidates[: profile.top_k]:
        for vacancy_id, key_word_coverage, semantic, combined in candidates:
            if key_word_coverage >= profile.min_keyword_coverage or semantic >= profile.min_semantic_score:
                with get_db() as db:
                    save_match(db, profile, vacancy_id, key_word_coverage, semantic, combined)
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
