from datetime import date, datetime
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, Row
from sqlalchemy.dialects.postgresql import insert

from scrap_vac.db.schemas import ProfileRow
from scrap_vac.db.models import Vacancy, UserProfile, User, MatcherState, UserMatch



def get_vacancies_since_date(db: Session, since_ts: date) -> Sequence[Vacancy]:
    stmt = (
        select(Vacancy)
        .where(Vacancy.added_at > since_ts)
        .order_by(Vacancy.added_at.asc())
    )
    result = db.execute(stmt)
    return result.scalars().all()

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

def get_not_notified(db: Session) -> list[Row]:
    stmt = (
        select(
            UserMatch.id,
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