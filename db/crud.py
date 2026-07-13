from datetime import date, datetime
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, Row, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

from db.schemas import ProfileRow
from db.models import Vacancy, UserProfile, User, MatcherState, UserMatch



def get_vacancies_since_date(db: Session, since_ts: date) -> Sequence[Vacancy]:
    stmt = (
        select(Vacancy)
        .where(Vacancy.added_at > since_ts)
        .order_by(Vacancy.added_at.asc())
    )
    result = db.execute(stmt)
    return result.scalars().all()

def create_vacancy(db: Session, data: dict) -> bool:
    stmt = (
        insert(Vacancy)
        .values(**data)
        .on_conflict_do_nothing(constraint="uq_vacancies_url_title")
    )
    result = db.execute(stmt)
    row_count = result.rowcount
    return row_count == 1


def get_active_users_profiles(db: Session):
    stmt = (
        select(UserProfile)
        .join(User, User.id == UserProfile.user_id)
        .where(UserProfile.is_active.is_(True), User.is_active.is_(True))
        .order_by(UserProfile.id)
    )
    result = db.execute(stmt)
    return result.scalars().all()

def get_last_run(db: Session, key) -> datetime:
    row = db.scalar(select(MatcherState).where(MatcherState.key == key))
    if not row:
        return datetime(1970, 1, 1)
    return datetime.fromisoformat(row.value)

def set_last_run(db: Session, key: str, ts: datetime) -> None:
    upsert = insert(MatcherState).values(key=key, value=ts.isoformat())
    upsert = upsert.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": upsert.excluded.value, "updated_at": func.now()},
    )
    db.execute(upsert)

def get_not_notified(db: Session) -> list[Row]:
    stmt = (
        select(
            UserMatch.id.label("match_id"),
            User.telegram_user_id,
            Vacancy.id,
            Vacancy.title,
            Vacancy.source,
            Vacancy.url,
        )
        .select_from(UserMatch)
        .join(User, User.id == UserMatch.user_id)
        .join(Vacancy, Vacancy.id == UserMatch.vacancy_id)
        .where(UserMatch.notified.is_not(True))
        .order_by(UserMatch.id)
    )
    result = db.execute(stmt)
    return result.all()

def save_match(db: Session, profile: ProfileRow, vacancy_id: int, coverage: float, semantic: float, combined: float) -> None:
    reason = {
        "profile_name": profile.name,
        "keyword_coverage": round(coverage, 4),
        "semantic_score": round(semantic, 4),
        "combined_score": round(combined, 4),
    }
    upsert = insert(UserMatch).values(
        user_id=profile.user_id,
        profile_id=profile.id,
        vacancy_id=vacancy_id,
        keyword_coverage=coverage,
        semantic_score=semantic,
        combined_score=combined,
        reason_json=reason,
    )
    upsert = upsert.on_conflict_do_update(
        constraint="uq_user_matches_profile_vacancy",
        set_={
            "keyword_coverage": upsert.excluded.keyword_coverage,
            "semantic_score": upsert.excluded.semantic_score,
            "combined_score": upsert.excluded.combined_score,
            "reason_json": upsert.excluded.reason_json,
        },
    )
    db.execute(upsert)


def mark_notified(db: Session, match_id: int) -> None:
    db.execute(
        update(UserMatch)
        .where(UserMatch.id == match_id)
        .values(notified=True)
    )
    db.commit()


def get_vacancies_urls(db: Session) -> Sequence[str]:
    stmt = (
        select(Vacancy.url)
    )
    result = db.execute(stmt)
    return result.scalars().all()

