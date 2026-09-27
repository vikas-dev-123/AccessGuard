from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Timezone-aware datetime that stays UTC-aware on SQLite, which drops tzinfo on read."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Role(str, Enum):
    AUDITOR = "auditor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    hashed_password: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16))


class Dataset(Base):
    """One upload: an HR master file plus one or more system user lists."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    uploaded_by: Mapped[str] = mapped_column(String(64))
    systems: Mapped[list] = mapped_column(JSON)
    file_names: Mapped[dict] = mapped_column(JSON)
    hr_employee_count: Mapped[int] = mapped_column(Integer)
    account_counts: Mapped[dict] = mapped_column(JSON)

    employees: Mapped[list[HREmployee]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    accounts: Mapped[list[SystemAccount]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class HREmployee(Base):
    __tablename__ = "hr_employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(128))
    designation: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    joining_date: Mapped[date | None] = mapped_column(Date)
    termination_date: Mapped[date | None] = mapped_column(Date)

    dataset: Mapped[Dataset] = relationship(back_populates="employees")


class SystemAccount(Base):
    __tablename__ = "system_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    system: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(String(64))
    employee_id: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(128))
    account_status: Mapped[str] = mapped_column(String(32))
    created_date: Mapped[date | None] = mapped_column(Date)
    last_login_date: Mapped[date | None] = mapped_column(Date)
    status_last_updated: Mapped[date | None] = mapped_column(Date)

    dataset: Mapped[Dataset] = relationship(back_populates="accounts")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    run_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    run_by: Mapped[str] = mapped_column(String(64))
    as_of_date: Mapped[date] = mapped_column(Date)
    systems: Mapped[list] = mapped_column(JSON)
    total_findings: Mapped[int] = mapped_column(Integer)

    findings: Mapped[list[FindingRecord]] = relationship(back_populates="review", cascade="all, delete-orphan")


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[str] = mapped_column(String(16))
    check_code: Mapped[str] = mapped_column(String(64), index=True)
    check_name: Mapped[str] = mapped_column(String(128))
    system: Mapped[str] = mapped_column(String(128), index=True)
    employee_id: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str] = mapped_column(String(512))
    details: Mapped[str] = mapped_column(Text)
    risk_rating: Mapped[str] = mapped_column(String(16), index=True)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime())

    review: Mapped[Review] = relationship(back_populates="findings")
