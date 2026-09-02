from finance_app.security.passwords import hash_password, verify_password


def test_password_roundtrip() -> None:
    password_hash = hash_password("mot-de-passe-tres-solide")
    assert verify_password(password_hash, "mot-de-passe-tres-solide")
    assert not verify_password(password_hash, "incorrect")
