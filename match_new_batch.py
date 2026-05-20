import json
import os
from dataclasses import dataclass
from datetime import datetime

import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
STATE_KEY = "last_match_run_at"


@dataclass
class Vacancy:
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
class UserProfile:
    id: int
    user_id: int
    name: str
    query_text: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    min_keyword_coverage: float
    min_semantic_score: float
    top_k: int


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def to_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def ensure_ai_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_user_id BIGINT UNIQUE,
            username TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT 'default',
            query_text TEXT NOT NULL,
            include_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
            exclude_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
            min_keyword_coverage DOUBLE PRECISION NOT NULL DEFAULT 0.2,
            min_semantic_score DOUBLE PRECISION NOT NULL DEFAULT 0.42,
            top_k INTEGER NOT NULL DEFAULT 20,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_user_profiles_user_name ON user_profiles(user_id, name)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_matches (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            profile_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
            vacancy_id INTEGER NOT NULL REFERENCES vacancies(id) ON DELETE CASCADE,
            keyword_coverage DOUBLE PRECISION NOT NULL,
            semantic_score DOUBLE PRECISION NOT NULL,
            combined_score DOUBLE PRECISION NOT NULL,
            reason_json JSONB,
            notified BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_id, vacancy_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS matcher_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_last_run(cur) -> datetime:
    cur.execute("SELECT value FROM matcher_state WHERE key = %s", (STATE_KEY,))
    row = cur.fetchone()
    if not row:
        return datetime(1970, 1, 1)
    return datetime.fromisoformat(row[0])


def set_last_run(cur, ts: datetime) -> None:
    cur.execute(
        """
        INSERT INTO matcher_state(key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
        (STATE_KEY, ts.isoformat()),
    )


def load_new_vacancies(cur, since_ts: datetime) -> list[Vacancy]:
    cur.execute(
        """
        SELECT id, COALESCE(source, ''), title, url,
               COALESCE(listing_context, ''), COALESCE(description_text, ''), added_at
        FROM vacancies
        WHERE added_at > %s
        ORDER BY added_at ASC
        """,
        (since_ts,),
    )
    rows = cur.fetchall()
    return [
        Vacancy(
            id=row[0],
            source=row[1],
            title=row[2] or "",
            url=row[3] or "",
            listing_context=row[4] or "",
            description_text=row[5] or "",
            added_at=row[6],
        )
        for row in rows
    ]


def load_profiles(cur) -> list[UserProfile]:
    cur.execute(
        """
        SELECT p.id, p.user_id, p.name, p.query_text,
               p.include_keywords, p.exclude_keywords,
               p.min_keyword_coverage, p.min_semantic_score, p.top_k
        FROM user_profiles p
        JOIN users u ON u.id = p.user_id
        WHERE p.is_active = TRUE AND u.is_active = TRUE
        ORDER BY p.id
        """
    )
    rows = cur.fetchall()
    return [
        UserProfile(
            id=row[0],
            user_id=row[1],
            name=row[2],
            query_text=row[3],
            include_keywords=to_str_list(row[4]),
            exclude_keywords=to_str_list(row[5]),
            min_keyword_coverage=float(row[6]),
            min_semantic_score=float(row[7]),
            top_k=int(row[8]),
        )
        for row in rows
    ]


def keyword_filter(text: str, include: list[str], exclude: list[str], min_coverage: float) -> tuple[bool, float]:
    norm_text = normalize_text(text)
    include_norm = [normalize_text(word) for word in include]
    exclude_norm = [normalize_text(word) for word in exclude]

    if exclude_norm and any(word in norm_text for word in exclude_norm):
        return False, 0.0
    if not include_norm:
        return True, 1.0

    hits = sum(1 for word in include_norm if word in norm_text)
    coverage = hits / len(include_norm)
    return coverage >= min_coverage, coverage


def save_match(cur, profile: UserProfile, vacancy_id: int, coverage: float, semantic: float, combined: float) -> None:
    reason = {
        "profile_name": profile.name,
        "keyword_coverage": round(coverage, 4),
        "semantic_score": round(semantic, 4),
        "combined_score": round(combined, 4),
    }
    cur.execute(
        """
        INSERT INTO user_matches (
            user_id, profile_id, vacancy_id,
            keyword_coverage, semantic_score, combined_score, reason_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (profile_id, vacancy_id)
        DO UPDATE SET
            keyword_coverage = EXCLUDED.keyword_coverage,
            semantic_score = EXCLUDED.semantic_score,
            combined_score = EXCLUDED.combined_score,
            reason_json = EXCLUDED.reason_json
        """,
        (
            profile.user_id,
            profile.id,
            vacancy_id,
            coverage,
            semantic,
            combined,
            json.dumps(reason, ensure_ascii=False),
        ),
    )


def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set")

    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        ensure_ai_tables(cur)
        conn.commit()

        last_run = get_last_run(cur)
        vacancies = load_new_vacancies(cur, last_run)
        profiles = load_profiles(cur)

        if not profiles:
            print("No active profiles in user_profiles. Nothing to process.")
            return
        if not vacancies:
            print("No new vacancies since last matcher run.")
            return

        model = SentenceTransformer(MODEL_NAME)
        vacancy_texts = [vac.full_text for vac in vacancies]
        vacancy_embeddings = model.encode(vacancy_texts, convert_to_tensor=True)

        total_saved = 0
        for profile in profiles:
            query_embedding = model.encode(profile.query_text, convert_to_tensor=True)
            similarities = util.cos_sim(query_embedding, vacancy_embeddings)[0]

            candidates: list[tuple[int, float, float, float]] = []
            for idx, vacancy in enumerate(vacancies):
                ok, coverage = keyword_filter(
                    vacancy.full_text,
                    profile.include_keywords,
                    profile.exclude_keywords,
                    profile.min_keyword_coverage,
                )
                if not ok:
                    continue

                semantic = float(similarities[idx])
                if semantic < profile.min_semantic_score:
                    continue
                combined = 0.7 * semantic + 0.3 * coverage
                candidates.append((vacancy.id, coverage, semantic, combined))

            candidates.sort(key=lambda row: row[3], reverse=True)
            for vacancy_id, coverage, semantic, combined in candidates[: profile.top_k]:
                save_match(cur, profile, vacancy_id, coverage, semantic, combined)
                total_saved += 1

        newest_added_at = max(v.added_at for v in vacancies)
        set_last_run(cur, newest_added_at)
        conn.commit()

        print(f"Processed new vacancies: {len(vacancies)}")
        print(f"Processed active profiles: {len(profiles)}")
        print(f"Saved/updated matches: {total_saved}")
        print(f"Updated state {STATE_KEY} -> {newest_added_at.isoformat()}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

