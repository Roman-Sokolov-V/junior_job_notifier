from datetime import date, datetime
from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select, Row, update, RowMapping, or_, delete, literal
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

from db.models import Vacancy, UserProfile, User, UserMatch, MatcherState


def get_vacancies_since_date(db: Session, since_ts: date) -> Sequence[Vacancy]:
    stmt = (
        select(Vacancy)
        .where(Vacancy.added_at > since_ts)
        .order_by(Vacancy.added_at.asc())
    )
    result = db.execute(stmt)
    return result.scalars().all()

def get_vac_ids_since_date(db: Session, since_ts: date) -> Sequence[int]:
    stmt = (
        select(Vacancy.id)
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


def get_active_users_profiles(db: Session) -> Sequence[UserProfile]:
    stmt = (
        select(
            UserProfile
        )
        .join(User, User.id == UserProfile.user_id)
        .where(UserProfile.is_active.is_(True), User.is_active.is_(True))
    )
    result = db.execute(stmt)
    return result.scalars().all()


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

def save_match(db: Session, profile: UserProfile, vacancy_id: int, semantic: float | None) -> None:
    upsert = insert(UserMatch).values(
        user_id=profile.user_id,
        profile_id=profile.id,
        vacancy_id=vacancy_id,
        semantic_score=semantic,
    )
    upsert = upsert.on_conflict_do_update(
        constraint="uq_user_matches_profile_vacancy",
        set_={
            "semantic_score": upsert.excluded.semantic_score,
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



def update_profile_embeddings(db: Session, model, current_model_name: str) -> int:
    stmt = select(UserProfile).where(
        UserProfile.is_active.is_(True),
        UserProfile.query_text.is_not(None),
        or_(
            UserProfile.embedding_model.is_(None),
            UserProfile.embedding_model != current_model_name,
        ),
    )
    profiles = db.scalars(stmt).all()

    updated = 0
    for profile in profiles:
        embedding = model.encode(profile.query_text).tolist()
        profile.embedding = embedding
        profile.embedding_model = current_model_name
        updated += 1
    return updated

def update_vacancy_embeddings(db: Session, model, current_model_name: str) -> int:
    stmt = select(Vacancy).where(
        Vacancy.embedding_text.is_not(None),
        or_(
            Vacancy.embedding_model.is_(None),
            Vacancy.embedding_model != current_model_name,
        ),
    )
    vacancies = db.scalars(stmt).all()

    updated = 0
    for vac in vacancies:
        embedding = model.encode(vac.embedding_text).tolist()
        vac.embedding = embedding
        vac.embedding_model = current_model_name
        updated += 1
    return updated


def load_semantic_matches_for_vacancies_id_list(
        db: Session, profile: UserProfile, vac_ids: Sequence[int], limit: int = 200
) -> Sequence[RowMapping]:
    """Returns vacancies and similarities whose cosine similarity to the profile's embedding
    meets profile.min_semantic_score, ordered by best match first."""
    if not vac_ids:
        return []

    max_distance = 1 - profile.min_semantic_score
    distance_expr = Vacancy.embedding.cosine_distance(profile.embedding)
    similarity_expr = (1 - distance_expr).label("semantic_score")

    stmt = (
        select(Vacancy.id, Vacancy.title, Vacancy.url, similarity_expr)
        .where(
            Vacancy.id.in_(vac_ids),
            Vacancy.embedding.is_not(None),
            distance_expr <= max_distance,
        )
        .order_by(distance_expr)
        .limit(limit)
    )
    return db.execute(stmt).mappings().all()

def load_semantic_matches_and_no_embedded_vacancies_from_id_list(
        db: Session, profile: UserProfile, vac_ids: Sequence[int], limit: int = 200
) -> Sequence[RowMapping]:
    """Returns vacancies and similarities whose cosine similarity to the profile's embedding
    meets profile.min_semantic_score, ordered by best match first."""
    if not vac_ids:
        return []

    max_distance = 1 - profile.min_semantic_score
    distance_expr = Vacancy.embedding.cosine_distance(profile.embedding)
    similarity_expr = (1 - distance_expr).label("semantic_score")

    stmt_with_embedding = (
        select(Vacancy.id, Vacancy.title, Vacancy.url, similarity_expr)
        .where(
            Vacancy.id.in_(vac_ids),
            Vacancy.embedding.is_not(None),
            distance_expr <= max_distance,
        )
        #.order_by(distance_expr)
        .limit(limit)
    )
    stmt_without_embedding = (
        select(
            Vacancy.id,
            Vacancy.title,
            Vacancy.url,
            literal(None).label("similarity_expr"),
        )
        .where(
            Vacancy.id.in_(vac_ids),
            Vacancy.embedding.is_(None),
        )
    )
    stmt = stmt_with_embedding.union(stmt_without_embedding).order_by(similarity_expr)
    return db.execute(stmt).mappings().all()

def load_no_embedding_for_vacancies_id_list(db: Session, vac_ids: Sequence[int]) -> Sequence[RowMapping]:
    stmt = (
        select(Vacancy.id, Vacancy.title, Vacancy.url, literal(None).label("similarity_expr"))
        .where(
            Vacancy.id.in_(vac_ids),
            Vacancy.embedding.is_(None)
        )
    )
    return db.execute(stmt).mappings().all()

def load_vacancies_by_id_list(db: Session, vac_ids: Sequence[int]) -> Sequence[RowMapping]:
    if not vac_ids:
        return []
    stmt = (
        select(Vacancy.id, Vacancy.title, Vacancy.url)
        .where(
            Vacancy.id.in_(vac_ids),
        )
    )
    return db.execute(stmt).mappings().all()

def mark_urls_as_seen(db: Session, seen_existing_urls: Sequence[str]):
    if not seen_existing_urls:
        return
    stmt = (
        update(Vacancy)
        .where(Vacancy.url.in_(seen_existing_urls))
        .values(last_seen_at=func.now())
    )
    db.execute(stmt)


def delete_vacancies_not_seen_since(db: Session, stale_cutoff: datetime):
    stmt = (
        delete(Vacancy)
        .where(Vacancy.last_seen_at < stale_cutoff)
    )
    db.execute(stmt)


def get_last_run(db: Session) -> MatcherState | None:
    return db.execute(select(MatcherState)).scalar_one_or_none()

def create_state(db: Session):
    db.add(MatcherState())