import os
from datetime import datetime
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util


from scrap_vac.db.crud import get_active_users_profiles, get_vacancies_since_date, get_last_run, set_last_run, save_match
from scrap_vac.db.schemas import VacancyRow, ProfileRow, MatchCandidate
from scrap_vac.db.session import get_db

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
STATE_KEY = "last_match_run_at"



def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def to_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []



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




def _score_candidates(profile, vacancies, similarities) -> list[MatchCandidate]:
    """Applies keyword filtering and, if the profile has a query_text,
    semantic filtering. Each candidate is checked exactly once."""
    candidates: list[MatchCandidate] = []

    for idx, vacancy in enumerate(vacancies):
        passed, coverage = keyword_filter(
            vacancy.title,
            vacancy.full_text,
            profile.include_keywords,
            profile.exclude_keywords,
            profile.min_keyword_coverage,
        )
        if not passed:
            continue

        if profile.query_text:
            semantic = float(similarities[idx])
            combined = semantic + coverage
            if combined < profile.min_semantic_score:
                continue
        else:
            semantic = 0.0
            combined = coverage

        candidates.append(MatchCandidate(vacancy.id, coverage, semantic, combined))

    return candidates


def filter_vacancies() -> None:
    profiles = load_profiles()
    if not profiles:
        print("No active profiles in user_profiles. Nothing to process.")
        return

    model = SentenceTransformer(MODEL_NAME)  # завантажуємо один раз
    total_saved = 0
    total_profiles_processed = 0

    for profile in profiles:
        state_key = f"profile:{profile.id}"

        with get_db() as db:
            last_run = get_last_run(db, key=state_key)

        vacancies = load_new_vacancies(last_run)
        if not vacancies:
            continue

        vacancy_texts = [vac.full_text for vac in vacancies]
        vacancy_embeddings = model.encode(vacancy_texts, convert_to_tensor=True)

        similarities = None
        if profile.query_text:
            query_embedding = model.encode(profile.query_text, convert_to_tensor=True)
            similarities = util.cos_sim(query_embedding, vacancy_embeddings)[0]

        candidates = _score_candidates(profile, vacancies, similarities)

        newest_added_at = max(v.added_at for v in vacancies)
        with get_db() as db:
            for c in candidates:
                save_match(db, profile, c.vacancy_id, c.keyword_coverage, c.semantic_score, c.combined_score)
                total_saved += 1
            set_last_run(db, key=state_key, ts=newest_added_at)

        total_profiles_processed += 1

    print(f"Profiles with new vacancies processed: {total_profiles_processed}")
    print(f"Total profiles: {len(profiles)}")
    print(f"Saved/updated matches: {total_saved}")




if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set")
    filter_vacancies()
