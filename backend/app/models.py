import uuid
from datetime import date, datetime

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Indeks GiST zakładany jawnie niżej (spatial_index=False), żeby Alembic go nie dublował.
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    has_plates: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="web")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    photos: Mapped[list["ReportPhoto"]] = relationship(
        back_populates="report", order_by="ReportPhoto.position", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_reports_location", "location", postgresql_using="gist"),
        Index("ix_reports_created_at_id", "created_at", "id"),
        CheckConstraint("source IN ('web', 'seed')", name="ck_reports_source"),
    )


class ReportPhoto(Base):
    __tablename__ = "report_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_path: Mapped[str] = mapped_column(Text, nullable=False)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped[Report] = relationship(back_populates="photos")


class WeeklySummary(Base):
    __tablename__ = "weekly_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB)
    snapshot: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (Index("ix_weekly_summaries_generated_at_id", "generated_at", "id"),)
