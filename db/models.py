from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from db.base import Base



class Vacancy(Base):
    """Vacancies scraped from job sites (classic fields always set; AI fields optional)."""

    __tablename__ = "vacancies"
    __table_args__ = (UniqueConstraint("url", "title", name="uq_vacancies_url_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    nice_to_have: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seniority: Mapped[str | None] = mapped_column(Text, nullable=True)
    listing_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    matches: Mapped[list["UserMatch"]] = relationship(
        "UserMatch",
        back_populates="vacancy"
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True) # 384 - розмірність конкретної моделі що використовується
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    profiles: Mapped[list["UserProfile"]] = relationship("UserProfile", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id", "name", name="ux_user_profiles_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'default'"))
    query_text: Mapped[str] = mapped_column(Text, nullable=True, server_default=None)
    include_keywords: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    exclude_keywords: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    min_semantic_score: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0.42"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="profiles")
    matches: Mapped[list["UserMatch"]] = relationship(
        "UserMatch",
        back_populates="profile"
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384), nullable=True
    )  # 384 - розмірність конкретної моделі що використовується
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=text("'1970-01-01 00:00:00'"),
    )


class UserMatch(Base):
    __tablename__ = "user_matches"
    __table_args__ = (
        UniqueConstraint("profile_id", "vacancy_id", name="uq_user_matches_profile_vacancy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=True)
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="matches")
    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="matches")


class MatcherState(Base):
    __tablename__ = "matcher_state"
    __table_args__ = (
        CheckConstraint('id = 1', name='only_one_row_constraint'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )