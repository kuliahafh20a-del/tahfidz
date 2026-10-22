"""Recovery token delivery boundary for a future institutional mail adapter."""

from typing import Annotated, Protocol

from fastapi import Depends

from app.modules.auth.service import RecoveryChallenge


class RecoveryTokenDelivery(Protocol):
    async def deliver(self, challenge: RecoveryChallenge) -> None: ...


class DeferredRecoveryTokenDelivery:
    """Keep tokens out of responses/logs until an approved delivery adapter is configured."""

    async def deliver(self, challenge: RecoveryChallenge) -> None:
        del challenge


def get_recovery_token_delivery() -> RecoveryTokenDelivery:
    return DeferredRecoveryTokenDelivery()


RecoveryTokenDeliveryDependency = Annotated[
    RecoveryTokenDelivery,
    Depends(get_recovery_token_delivery),
]
