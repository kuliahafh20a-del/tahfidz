"""Password and opaque-token primitives kept behind a small testable boundary."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class PasswordManager:
    """Hash and verify passwords with Argon2id's maintained reference bindings."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        self.dummy_hash = self._hasher.hash("YAQin invalid credential sentinel")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except InvalidHashError, VerificationError, VerifyMismatchError:
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True


class OpaqueTokenManager:
    """Generate high-entropy bearer values and persist only keyed digests."""

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode("utf-8")

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(32)

    def digest(self, token: str) -> str:
        return hmac.new(self._secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    def matches(self, digest: str, candidate: str) -> bool:
        return hmac.compare_digest(digest, self.digest(candidate))
