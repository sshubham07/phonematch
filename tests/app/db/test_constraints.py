"""The schema rejects bad rows (spec R3b). Each test runs in a rolled-back transaction."""

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Channel,
    ChannelVideo,
    Phone,
    PhoneDigest,
    PhonePrice,
    QueryLog,
    ReviewChunk,
    ReviewVideo,
    Transcript,
)

VECTOR = [0.0] * 384


async def _phone(session: AsyncSession, slug: str = "redmi-note-14-pro") -> Phone:
    phone = Phone(slug=slug, brand="Redmi", model="Note 14 Pro")
    session.add(phone)
    await session.flush()
    return phone


async def _video(session: AsyncSession, video_id: str = "abc123") -> ChannelVideo:
    channel = Channel(handle=f"@ch-{video_id}", name="Channel", tier="core")
    session.add(channel)
    await session.flush()
    video = ChannelVideo(video_id=video_id, channel_id=channel.id, title="Redmi Note 14 Pro review")
    session.add(video)
    await session.flush()
    return video


async def _transcript(session: AsyncSession, video_id: str = "abc123") -> Transcript:
    await _video(session, video_id)
    transcript = Transcript(
        video_id=video_id, language="en", is_auto=True, raw_path=f"data/raw/{video_id}.json"
    )
    session.add(transcript)
    await session.flush()
    return transcript


async def _assert_rejected(session: AsyncSession, row: Any) -> None:
    async with session.begin_nested():
        session.add(row)
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_unknown_review_video_status_rejected(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    await _video(db_session)
    bad = ReviewVideo(phone_id=phone.id, video_id="abc123", status="done")
    await _assert_rejected(db_session, bad)


async def test_review_video_defaults_to_pending(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    await _video(db_session)
    row = ReviewVideo(phone_id=phone.id, video_id="abc123", match_score=95)
    db_session.add(row)
    await db_session.flush()
    await db_session.refresh(row)
    assert row.status == "pending"


async def test_review_video_requires_phone(db_session: AsyncSession) -> None:
    await _video(db_session)
    await _assert_rejected(db_session, ReviewVideo(video_id="abc123"))


async def test_unknown_channel_tier_rejected(db_session: AsyncSession) -> None:
    await _assert_rejected(db_session, Channel(handle="@x", name="X", tier="gold"))


async def test_unknown_price_band_rejected(db_session: AsyncSession) -> None:
    await _assert_rejected(db_session, Phone(slug="x", brand="X", model="X", price_band="cheap"))


async def test_unknown_os_rejected(db_session: AsyncSession) -> None:
    await _assert_rejected(db_session, Phone(slug="x", brand="X", model="X", os="symbian"))


async def test_duplicate_phone_slug_rejected(db_session: AsyncSession) -> None:
    await _phone(db_session)
    await _assert_rejected(db_session, Phone(slug="redmi-note-14-pro", brand="R", model="N"))


async def test_digest_score_above_ten_rejected(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    bad = PhoneDigest(phone_id=phone.id, camera=11, source_hash="h", prompt_version="v1", model="m")
    await _assert_rejected(db_session, bad)


async def test_digest_null_score_allowed(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    digest = PhoneDigest(
        phone_id=phone.id, camera=None, battery=7.5, source_hash="h", prompt_version="v1", model="m"
    )
    db_session.add(digest)
    await db_session.flush()
    await db_session.refresh(digest)
    assert digest.pros == []
    assert digest.low_confidence is False


async def test_feedback_zero_rejected(db_session: AsyncSession) -> None:
    await _assert_rejected(db_session, QueryLog(raw_input={"text": "hi"}, feedback=0))


async def test_duplicate_chunk_natural_key_rejected(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    await _transcript(db_session)
    db_session.add(
        ReviewChunk(phone_id=phone.id, video_id="abc123", start_sec=60, text="a", embedding=VECTOR)
    )
    await db_session.flush()
    dup = ReviewChunk(
        phone_id=phone.id, video_id="abc123", start_sec=60, text="b", embedding=VECTOR
    )
    await _assert_rejected(db_session, dup)


async def test_deleting_phone_cascades_to_derived_rows(db_session: AsyncSession) -> None:
    phone = await _phone(db_session)
    await _transcript(db_session)
    db_session.add_all(
        [
            PhonePrice(phone_id=phone.id, variant="8/256", price=24999),
            PhoneDigest(phone_id=phone.id, source_hash="h", prompt_version="v1", model="m"),
            ReviewVideo(phone_id=phone.id, video_id="abc123"),
            ReviewChunk(
                phone_id=phone.id, video_id="abc123", start_sec=0, text="t", embedding=VECTOR
            ),
        ]
    )
    await db_session.flush()

    await db_session.delete(phone)
    await db_session.flush()
    db_session.expunge_all()

    for model in (PhonePrice, PhoneDigest, ReviewVideo, ReviewChunk):
        count = await db_session.scalar(select(func.count()).select_from(model))
        assert count == 0, model.__tablename__
    # The transcript is not phone-owned data and survives.
    assert await db_session.scalar(select(func.count()).select_from(Transcript)) == 1
