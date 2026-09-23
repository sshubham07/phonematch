"""SQLAlchemy models for the schema in docs/HLD.md §8."""

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    REAL,
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# bge-small-en-v1.5. Changing it needs a migration and a full re-embed (see CLAUDE.md gotchas).
EMBEDDING_DIM = 384

PRICE_BANDS = ("u15k", "15-25k", "25-40k", "40-70k", "70k+")
PHONE_OS = ("android", "ios")
CHANNEL_TIERS = ("core", "backup")
REVIEW_VIDEO_STATUSES = ("pending", "needs_review", "fetched", "failed", "rejected")
JOB_RUN_STATUSES = ("running", "success", "partial", "failed")
DIGEST_ASPECTS = ("camera", "battery", "performance", "display", "thermals", "software", "build")

TZ = TIMESTAMP(timezone=True)


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


class Phone(Base):
    __tablename__ = "phones"
    __table_args__ = (
        CheckConstraint("price_from > 0", name="price_from_positive"),
        CheckConstraint(_in("price_band", PRICE_BANDS), name="price_band"),
        CheckConstraint(_in("os", PHONE_OS), name="os"),
        Index("ix_phones_is_active_price_from", "is_active", "price_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    brand: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    launch_date: Mapped[date | None] = mapped_column(Date)
    price_from: Mapped[int | None] = mapped_column(Integer)
    price_band: Mapped[str | None] = mapped_column(Text)
    sales_rank: Mapped[int | None] = mapped_column(Integer)
    os: Mapped[str | None] = mapped_column(Text)
    chipset: Mapped[str | None] = mapped_column(Text)
    antutu: Mapped[int | None] = mapped_column(Integer)
    ram_gb_max: Mapped[int | None] = mapped_column(Integer)
    storage_gb_max: Mapped[int | None] = mapped_column(Integer)
    display_in: Mapped[float | None] = mapped_column(REAL)
    display_type: Mapped[str | None] = mapped_column(Text)
    refresh_hz: Mapped[int | None] = mapped_column(Integer)
    battery_mah: Mapped[int | None] = mapped_column(Integer)
    charging_w: Mapped[int | None] = mapped_column(Integer)
    main_cam_mp: Mapped[int | None] = mapped_column(Integer)
    has_ois: Mapped[bool | None]
    is_5g: Mapped[bool | None]
    weight_g: Mapped[int | None] = mapped_column(Integer)
    ip_rating: Mapped[str | None] = mapped_column(Text)
    update_years: Mapped[int | None] = mapped_column(Integer)
    flipkart_url: Mapped[str | None] = mapped_column(Text)
    gsmarena_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now(), onupdate=func.now())


class PhonePrice(Base):
    __tablename__ = "phone_prices"
    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("mrp > 0", name="mrp_positive"),
    )

    phone_id: Mapped[int] = mapped_column(
        ForeignKey("phones.id", ondelete="CASCADE"), primary_key=True
    )
    variant: Mapped[str] = mapped_column(Text, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(TZ, primary_key=True, server_default=func.now())
    price: Mapped[int] = mapped_column(Integer)
    mrp: Mapped[int | None] = mapped_column(Integer)
    in_stock: Mapped[bool | None]


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (CheckConstraint(_in("tier", CHANNEL_TIERS), name="tier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    handle: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    last_synced_at: Mapped[datetime | None] = mapped_column(TZ)


class ChannelVideo(Base):
    __tablename__ = "channel_videos"
    __table_args__ = (
        Index("ix_channel_videos_channel_id", "channel_id"),
        Index(
            "ix_channel_videos_title_tsv",
            text("to_tsvector('simple', title)"),
            postgresql_using="gin",
        ),
    )

    video_id: Mapped[str] = mapped_column(Text, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"))
    title: Mapped[str] = mapped_column(Text)
    duration_s: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[date | None] = mapped_column(Date)
    first_seen_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class ReviewVideo(Base):
    __tablename__ = "review_videos"
    __table_args__ = (
        UniqueConstraint("phone_id", "video_id"),
        CheckConstraint("match_score BETWEEN 0 AND 100", name="match_score_range"),
        CheckConstraint(_in("status", REVIEW_VIDEO_STATUSES), name="status"),
        Index("ix_review_videos_status", "status"),
        Index("ix_review_videos_video_id", "video_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_id: Mapped[int] = mapped_column(ForeignKey("phones.id", ondelete="CASCADE"))
    video_id: Mapped[str] = mapped_column(ForeignKey("channel_videos.video_id"))
    match_score: Mapped[float | None] = mapped_column(REAL)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now(), onupdate=func.now())


class Transcript(Base):
    __tablename__ = "transcripts"

    video_id: Mapped[str] = mapped_column(ForeignKey("channel_videos.video_id"), primary_key=True)
    language: Mapped[str] = mapped_column(Text)
    is_auto: Mapped[bool]
    raw_path: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    map_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    map_prompt_version: Mapped[str | None] = mapped_column(Text)
    embedded_at: Mapped[datetime | None] = mapped_column(TZ)
    fetched_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class PhoneDigest(Base):
    __tablename__ = "phone_digests"
    __table_args__ = tuple(
        CheckConstraint(f"{aspect} BETWEEN 0 AND 10", name=f"{aspect}_range")
        for aspect in DIGEST_ASPECTS
    )

    phone_id: Mapped[int] = mapped_column(
        ForeignKey("phones.id", ondelete="CASCADE"), primary_key=True
    )
    camera: Mapped[float | None] = mapped_column(REAL)
    battery: Mapped[float | None] = mapped_column(REAL)
    performance: Mapped[float | None] = mapped_column(REAL)
    display: Mapped[float | None] = mapped_column(REAL)
    thermals: Mapped[float | None] = mapped_column(REAL)
    software: Mapped[float | None] = mapped_column(REAL)
    build: Mapped[float | None] = mapped_column(REAL)
    pros: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    cons: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    gaming_notes: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    disagreements: Mapped[list[Any] | None] = mapped_column(JSONB)
    source_videos: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    coverage: Mapped[str | None] = mapped_column(Text)
    low_confidence: Mapped[bool] = mapped_column(server_default=text("false"))
    source_hash: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    built_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())


class ReviewChunk(Base):
    __tablename__ = "review_chunks"
    __table_args__ = (
        UniqueConstraint("phone_id", "video_id", "start_sec"),
        CheckConstraint("start_sec >= 0", name="start_sec_non_negative"),
        Index(
            "ix_review_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone_id: Mapped[int] = mapped_column(ForeignKey("phones.id", ondelete="CASCADE"))
    video_id: Mapped[str] = mapped_column(ForeignKey("transcripts.video_id", ondelete="CASCADE"))
    start_sec: Mapped[int] = mapped_column(Integer)
    aspect: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (
        CheckConstraint(_in("status", JOB_RUN_STATUSES), name="status"),
        Index("ix_job_runs_job_started_at", "job", text("started_at DESC")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(TZ)
    processed: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    failed: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'running'"))
    notes: Mapped[str | None] = mapped_column(Text)


class QueryLog(Base):
    __tablename__ = "query_logs"
    __table_args__ = (
        CheckConstraint("feedback IN (-1, 1)", name="feedback"),
        Index("ix_query_logs_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=func.now())
    session_id: Mapped[str | None] = mapped_column(Text)
    raw_input: Mapped[dict[str, Any]] = mapped_column(JSONB)
    intent: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    candidate_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    fallback_used: Mapped[bool] = mapped_column(server_default=text("false"))
    feedback: Mapped[int | None] = mapped_column(SmallInteger)
