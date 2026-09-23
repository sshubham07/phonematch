"""initial schema: all 10 tables of docs/HLD.md §8 (tightened in M0) + pgvector

Revision ID: 0001
Revises:
Create Date: 2026-09-23 18:37:20.113736

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("handle", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_synced_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("tier IN ('core', 'backup')", name=op.f("ck_channels_tier")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
        sa.UniqueConstraint("handle", name=op.f("uq_channels_handle")),
    )
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("processed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'partial', 'failed')", name=op.f("ck_job_runs_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_runs")),
    )
    op.create_index(
        "ix_job_runs_job_started_at",
        "job_runs",
        ["job", sa.literal_column("started_at DESC")],
        unique=False,
    )
    op.create_table(
        "phones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("launch_date", sa.Date(), nullable=True),
        sa.Column("price_from", sa.Integer(), nullable=True),
        sa.Column("price_band", sa.Text(), nullable=True),
        sa.Column("sales_rank", sa.Integer(), nullable=True),
        sa.Column("os", sa.Text(), nullable=True),
        sa.Column("chipset", sa.Text(), nullable=True),
        sa.Column("antutu", sa.Integer(), nullable=True),
        sa.Column("ram_gb_max", sa.Integer(), nullable=True),
        sa.Column("storage_gb_max", sa.Integer(), nullable=True),
        sa.Column("display_in", sa.REAL(), nullable=True),
        sa.Column("display_type", sa.Text(), nullable=True),
        sa.Column("refresh_hz", sa.Integer(), nullable=True),
        sa.Column("battery_mah", sa.Integer(), nullable=True),
        sa.Column("charging_w", sa.Integer(), nullable=True),
        sa.Column("main_cam_mp", sa.Integer(), nullable=True),
        sa.Column("has_ois", sa.Boolean(), nullable=True),
        sa.Column("is_5g", sa.Boolean(), nullable=True),
        sa.Column("weight_g", sa.Integer(), nullable=True),
        sa.Column("ip_rating", sa.Text(), nullable=True),
        sa.Column("update_years", sa.Integer(), nullable=True),
        sa.Column("flipkart_url", sa.Text(), nullable=True),
        sa.Column("gsmarena_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("os IN ('android', 'ios')", name=op.f("ck_phones_os")),
        sa.CheckConstraint(
            "price_band IN ('u15k', '15-25k', '25-40k', '40-70k', '70k+')",
            name=op.f("ck_phones_price_band"),
        ),
        sa.CheckConstraint("price_from > 0", name=op.f("ck_phones_price_from_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phones")),
        sa.UniqueConstraint("slug", name=op.f("uq_phones_slug")),
    )
    op.create_index(
        "ix_phones_is_active_price_from", "phones", ["is_active", "price_from"], unique=False
    )
    op.create_table(
        "query_logs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("raw_input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("intent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("candidate_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("feedback", sa.SmallInteger(), nullable=True),
        sa.CheckConstraint("feedback IN (-1, 1)", name=op.f("ck_query_logs_feedback")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_query_logs")),
    )
    op.create_index("ix_query_logs_session_id", "query_logs", ["session_id"], unique=False)
    op.create_table(
        "channel_videos",
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column(
            "first_seen_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["channels.id"], name=op.f("fk_channel_videos_channel_id_channels")
        ),
        sa.PrimaryKeyConstraint("video_id", name=op.f("pk_channel_videos")),
    )
    op.create_index("ix_channel_videos_channel_id", "channel_videos", ["channel_id"], unique=False)
    op.create_index(
        "ix_channel_videos_title_tsv",
        "channel_videos",
        [sa.literal_column("to_tsvector('simple', title)")],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "phone_digests",
        sa.Column("phone_id", sa.Integer(), nullable=False),
        sa.Column("camera", sa.REAL(), nullable=True),
        sa.Column("battery", sa.REAL(), nullable=True),
        sa.Column("performance", sa.REAL(), nullable=True),
        sa.Column("display", sa.REAL(), nullable=True),
        sa.Column("thermals", sa.REAL(), nullable=True),
        sa.Column("software", sa.REAL(), nullable=True),
        sa.Column("build", sa.REAL(), nullable=True),
        sa.Column(
            "pros", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column(
            "cons", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("gaming_notes", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("disagreements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "source_videos",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("coverage", sa.Text(), nullable=True),
        sa.Column("low_confidence", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_hash", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "built_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("battery BETWEEN 0 AND 10", name=op.f("ck_phone_digests_battery_range")),
        sa.CheckConstraint("build BETWEEN 0 AND 10", name=op.f("ck_phone_digests_build_range")),
        sa.CheckConstraint("camera BETWEEN 0 AND 10", name=op.f("ck_phone_digests_camera_range")),
        sa.CheckConstraint("display BETWEEN 0 AND 10", name=op.f("ck_phone_digests_display_range")),
        sa.CheckConstraint(
            "performance BETWEEN 0 AND 10", name=op.f("ck_phone_digests_performance_range")
        ),
        sa.CheckConstraint(
            "software BETWEEN 0 AND 10", name=op.f("ck_phone_digests_software_range")
        ),
        sa.CheckConstraint(
            "thermals BETWEEN 0 AND 10", name=op.f("ck_phone_digests_thermals_range")
        ),
        sa.ForeignKeyConstraint(
            ["phone_id"],
            ["phones.id"],
            name=op.f("fk_phone_digests_phone_id_phones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("phone_id", name=op.f("pk_phone_digests")),
    )
    op.create_table(
        "phone_prices",
        sa.Column("phone_id", sa.Integer(), nullable=False),
        sa.Column("variant", sa.Text(), nullable=False),
        sa.Column(
            "captured_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("mrp", sa.Integer(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.CheckConstraint("mrp > 0", name=op.f("ck_phone_prices_mrp_positive")),
        sa.CheckConstraint("price > 0", name=op.f("ck_phone_prices_price_positive")),
        sa.ForeignKeyConstraint(
            ["phone_id"],
            ["phones.id"],
            name=op.f("fk_phone_prices_phone_id_phones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("phone_id", "variant", "captured_at", name=op.f("pk_phone_prices")),
    )
    op.create_table(
        "review_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("match_score", sa.REAL(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'needs_review', 'fetched', 'failed', 'rejected')",
            name=op.f("ck_review_videos_status"),
        ),
        sa.CheckConstraint(
            "match_score BETWEEN 0 AND 100", name=op.f("ck_review_videos_match_score_range")
        ),
        sa.ForeignKeyConstraint(
            ["phone_id"],
            ["phones.id"],
            name=op.f("fk_review_videos_phone_id_phones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["channel_videos.video_id"],
            name=op.f("fk_review_videos_video_id_channel_videos"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_videos")),
        sa.UniqueConstraint(
            "phone_id", "video_id", name=op.f("uq_review_videos_phone_id_video_id")
        ),
    )
    op.create_index("ix_review_videos_status", "review_videos", ["status"], unique=False)
    op.create_index("ix_review_videos_video_id", "review_videos", ["video_id"], unique=False)
    op.create_table(
        "transcripts",
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("is_auto", sa.Boolean(), nullable=False),
        sa.Column("raw_path", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("map_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("map_prompt_version", sa.Text(), nullable=True),
        sa.Column("embedded_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["channel_videos.video_id"],
            name=op.f("fk_transcripts_video_id_channel_videos"),
        ),
        sa.PrimaryKeyConstraint("video_id", name=op.f("pk_transcripts")),
    )
    op.create_table(
        "review_chunks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("phone_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Text(), nullable=False),
        sa.Column("start_sec", sa.Integer(), nullable=False),
        sa.Column("aspect", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=384), nullable=False),
        sa.CheckConstraint("start_sec >= 0", name=op.f("ck_review_chunks_start_sec_non_negative")),
        sa.ForeignKeyConstraint(
            ["phone_id"],
            ["phones.id"],
            name=op.f("fk_review_chunks_phone_id_phones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["transcripts.video_id"],
            name=op.f("fk_review_chunks_video_id_transcripts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_chunks")),
        sa.UniqueConstraint(
            "phone_id",
            "video_id",
            "start_sec",
            name=op.f("uq_review_chunks_phone_id_video_id_start_sec"),
        ),
    )
    op.create_index(
        "ix_review_chunks_embedding",
        "review_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Downgrade schema. The vector extension is left installed (shared, harmless)."""
    op.drop_index(
        "ix_review_chunks_embedding",
        table_name="review_chunks",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_table("review_chunks")
    op.drop_table("transcripts")
    op.drop_index("ix_review_videos_video_id", table_name="review_videos")
    op.drop_index("ix_review_videos_status", table_name="review_videos")
    op.drop_table("review_videos")
    op.drop_table("phone_prices")
    op.drop_table("phone_digests")
    op.drop_index(
        "ix_channel_videos_title_tsv", table_name="channel_videos", postgresql_using="gin"
    )
    op.drop_index("ix_channel_videos_channel_id", table_name="channel_videos")
    op.drop_table("channel_videos")
    op.drop_index("ix_query_logs_session_id", table_name="query_logs")
    op.drop_table("query_logs")
    op.drop_index("ix_phones_is_active_price_from", table_name="phones")
    op.drop_table("phones")
    op.drop_index("ix_job_runs_job_started_at", table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_table("channels")
