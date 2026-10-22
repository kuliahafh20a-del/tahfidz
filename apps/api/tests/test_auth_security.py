from app.modules.auth.security import OpaqueTokenManager, PasswordManager


def test_password_manager_hashes_with_argon2_and_rejects_wrong_password() -> None:
    manager = PasswordManager()
    password_hash = manager.hash("a sufficiently strong password")

    assert password_hash.startswith("$argon2id$")
    assert "sufficiently strong" not in password_hash
    assert manager.verify(password_hash, "a sufficiently strong password")
    assert not manager.verify(password_hash, "wrong password")
    assert not manager.verify("not-a-valid-hash", "wrong password")


def test_opaque_token_manager_uses_random_values_and_keyed_digests() -> None:
    manager = OpaqueTokenManager("a-test-secret-that-is-longer-than-thirty-two-characters")
    first = manager.generate()
    second = manager.generate()

    assert first != second
    assert first not in manager.digest(first)
    assert manager.matches(manager.digest(first), first)
    assert not manager.matches(manager.digest(first), second)
