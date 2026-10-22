"""Durable claims and canonical hashing for idempotent commands."""

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.session import get_session
from app.modules.operations.models import IdempotencyRecord, IdempotencyStatus


class IdempotencyKeyReusedError(ValueError):
    """A key was bound to another operation or payload."""


class IdempotencyRequestInProgressError(RuntimeError):
    """The first request has not published a safe replay result yet."""


def request_fingerprint(payload: object) -> str:
    """Hash a canonical JSON payload without storing its potentially sensitive content."""
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    record: IdempotencyRecord
    replay_body: dict[str, object] | None = None


class IdempotencyStore:
    """Claim command keys and retain only safe response data for replay."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim(
        self,
        *,
        actor_id: UUID,
        idempotency_key: UUID,
        method: str,
        normalized_path: str,
        payload: object,
        request_id: UUID,
    ) -> IdempotencyClaim:
        fingerprint = request_fingerprint(payload)
        record = await self.session.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == actor_id,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        now = utc_now()
        if record is None:
            record = IdempotencyRecord(
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                method=method,
                normalized_path=normalized_path,
                request_hash=fingerprint,
                request_id=request_id,
                expires_at=now + timedelta(hours=24),
            )
            self.session.add(record)
            await self.session.flush()
            return IdempotencyClaim(record=record)

        if (
            record.method != method
            or record.normalized_path != normalized_path
            or record.request_hash != fingerprint
        ):
            raise IdempotencyKeyReusedError
        if record.status == IdempotencyStatus.COMPLETED and record.response_body is not None:
            return IdempotencyClaim(record=record, replay_body=record.response_body)
        raise IdempotencyRequestInProgressError

    async def complete(
        self,
        claim: IdempotencyClaim,
        *,
        response_body: dict[str, object],
        response_status: int,
    ) -> None:
        claim.record.status = IdempotencyStatus.COMPLETED
        claim.record.response_body = response_body
        claim.record.response_status = response_status
        await self.session.commit()


def get_idempotency_store(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IdempotencyStore:
    return IdempotencyStore(session)


IdempotencyStoreDependency = Annotated[IdempotencyStore, Depends(get_idempotency_store)]
