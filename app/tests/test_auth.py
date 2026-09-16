"""Tests for sign-in.

The acquired system's auth is the part of the monolith it would have been easiest to
port verbatim, because it looked finished: there was a login form, a password check and
a five-attempt lockout. Each of those tests exists here because the original was
decorative rather than functional.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.models import ANONYMOUS, AuthOutcome, Principal
from app.auth.providers import (
    AnonymousProvider,
    LocalPasswordProvider,
    LockoutPolicy,
    SupabasePasswordProvider,
    build_provider,
    hash_password,
    verify_password,
)
from app.storage.sqlite_store import SqlitePortfolioStore


@pytest.fixture
def store(tmp_path):
    store = SqlitePortfolioStore(tmp_path / "auth.db")
    yield store
    store.close()


@pytest.fixture
def users():
    return {"alice@example.com": hash_password("correct horse battery staple")}


# --------------------------------------------------------------------------- #
# Password handling
# --------------------------------------------------------------------------- #


def test_a_correct_password_verifies():
    assert verify_password("hunter2", hash_password("hunter2"))


def test_a_wrong_password_does_not():
    assert not verify_password("hunter3", hash_password("hunter2"))


def test_the_same_password_hashes_differently_every_time():
    """Per-user salt. Identical hashes would reveal shared passwords across accounts."""
    assert hash_password("same") != hash_password("same")


def test_the_hash_does_not_contain_the_password():
    assert "hunter2" not in hash_password("hunter2")


def test_the_encoding_names_its_algorithm_and_cost():
    algorithm, iterations, salt, digest = hash_password("x").split("$")
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) >= 200_000
    assert salt and digest


@pytest.mark.parametrize(
    "junk", ["", "not-a-hash", "pbkdf2_sha256$abc$def$ghi", "md5$1$a$b", None]
)
def test_malformed_stored_hashes_fail_closed(junk):
    """A corrupted record must deny access, never grant it."""
    assert not verify_password("anything", junk)


# --------------------------------------------------------------------------- #
# Local provider
# --------------------------------------------------------------------------- #


def test_correct_credentials_produce_a_principal(users):
    outcome = LocalPasswordProvider(users).sign_in(
        "alice@example.com", "correct horse battery staple"
    )
    assert outcome.succeeded
    assert outcome.principal.email == "alice@example.com"


def test_the_user_id_is_not_the_email(users):
    """A store keyed on a mutable identifier orphans data when it changes."""
    outcome = LocalPasswordProvider(users).sign_in(
        "alice@example.com", "correct horse battery staple"
    )
    assert outcome.principal.user_id != outcome.principal.email
    assert outcome.principal.user_id.startswith("local:")


def test_email_is_case_insensitive_and_trimmed(users):
    outcome = LocalPasswordProvider(users).sign_in(
        "  ALICE@Example.com  ", "correct horse battery staple"
    )
    assert outcome.succeeded


def test_a_wrong_password_fails(users):
    outcome = LocalPasswordProvider(users).sign_in("alice@example.com", "wrong")
    assert not outcome.succeeded
    assert outcome.error


def test_an_unknown_account_and_a_wrong_password_are_indistinguishable(users):
    """Naming which was wrong confirms whether an account exists."""
    provider = LocalPasswordProvider(users)
    unknown = provider.sign_in("nobody@example.com", "whatever")
    wrong = provider.sign_in("alice@example.com", "whatever")

    assert not unknown.succeeded and not wrong.succeeded
    assert unknown.error == wrong.error


def test_blank_credentials_are_rejected_without_a_lookup(users):
    outcome = LocalPasswordProvider(users).sign_in("", "")
    assert not outcome.succeeded
    assert "Enter an email" in outcome.error


def test_a_plaintext_configured_password_is_refused_not_accepted():
    """A development convenience that accepts plaintext ends up in production."""
    provider = LocalPasswordProvider({"bob@example.com": "letmein"})
    outcome = provider.sign_in("bob@example.com", "letmein")

    assert not outcome.succeeded
    assert "plaintext" in outcome.error


def test_an_unconfigured_local_provider_reports_itself_unconfigured():
    assert not LocalPasswordProvider({}).is_configured


def test_users_are_read_from_the_environment(monkeypatch):
    import json

    monkeypatch.setenv(
        "SCRCAE_USERS", json.dumps({"env@example.com": hash_password("secret")})
    )
    provider = LocalPasswordProvider()
    assert provider.is_configured
    assert provider.sign_in("env@example.com", "secret").succeeded


def test_malformed_user_json_does_not_crash_the_app(monkeypatch):
    monkeypatch.setenv("SCRCAE_USERS", "{not json")
    assert not LocalPasswordProvider().is_configured


# --------------------------------------------------------------------------- #
# Lockout: the one that was decorative
# --------------------------------------------------------------------------- #


def test_lockout_engages_after_the_configured_failures(store, users):
    policy = LockoutPolicy(store, max_failures=3, window=timedelta(minutes=15))
    provider = LocalPasswordProvider(users, lockout=policy)

    for _ in range(3):
        assert not provider.sign_in("alice@example.com", "wrong").succeeded

    held = provider.sign_in("alice@example.com", "correct horse battery staple")
    assert not held.succeeded
    assert held.locked_out


def test_lockout_survives_a_new_process(tmp_path, users):
    """The whole point.

    The acquired system counted attempts in `st.session_state`, so refreshing the page
    reset the counter and the control provided no protection at all. Constructing a
    brand-new store object here is a stronger test than a refresh: even restarting the
    server must not clear the count.
    """
    path = tmp_path / "lockout.db"

    first = SqlitePortfolioStore(path)
    provider = LocalPasswordProvider(users, lockout=LockoutPolicy(first, max_failures=3))
    for _ in range(3):
        provider.sign_in("alice@example.com", "wrong")
    first.close()

    second = SqlitePortfolioStore(path)
    reborn = LocalPasswordProvider(users, lockout=LockoutPolicy(second, max_failures=3))
    outcome = reborn.sign_in("alice@example.com", "correct horse battery staple")
    second.close()

    assert outcome.locked_out


def test_lockout_is_per_email(store, users):
    """One user's failures must not lock out another."""
    policy = LockoutPolicy(store, max_failures=2)
    provider = LocalPasswordProvider(
        {**users, "bob@example.com": hash_password("bobs password")}, lockout=policy
    )

    provider.sign_in("alice@example.com", "wrong")
    provider.sign_in("alice@example.com", "wrong")

    assert provider.sign_in("bob@example.com", "bobs password").succeeded


def test_a_successful_sign_in_clears_the_count(store, users):
    """Otherwise a user who fails four times then succeeds stays one mistake from lockout."""
    policy = LockoutPolicy(store, max_failures=3)
    provider = LocalPasswordProvider(users, lockout=policy)

    provider.sign_in("alice@example.com", "wrong")
    provider.sign_in("alice@example.com", "wrong")
    assert provider.sign_in("alice@example.com", "correct horse battery staple").succeeded

    provider.sign_in("alice@example.com", "wrong")
    assert not provider.sign_in("alice@example.com", "wrong").locked_out


def test_the_window_expires(store, users):
    """A permanent lock hands anyone a denial-of-service against a known address."""
    policy = LockoutPolicy(store, max_failures=2, window=timedelta(minutes=15))
    long_ago = datetime.now(UTC) - timedelta(hours=2)
    for _ in range(5):
        store.record_attempt("alice@example.com", succeeded=False, at=long_ago)

    assert policy.check("alice@example.com") is None


def test_lockout_states_when_to_retry(store, users):
    policy = LockoutPolicy(store, max_failures=1, window=timedelta(minutes=15))
    provider = LocalPasswordProvider(users, lockout=policy)
    provider.sign_in("alice@example.com", "wrong")

    outcome = provider.sign_in("alice@example.com", "wrong")
    assert outcome.retry_after_seconds == 900
    assert "15 minutes" in outcome.error


def test_a_provider_without_a_store_still_works(users):
    """No lockout is better than a crash; the store is optional."""
    provider = LocalPasswordProvider(users, lockout=LockoutPolicy(None))
    assert provider.sign_in("alice@example.com", "correct horse battery staple").succeeded


# --------------------------------------------------------------------------- #
# Supabase
# --------------------------------------------------------------------------- #


def test_supabase_without_credentials_says_so_rather_than_failing_the_password():
    outcome = SupabasePasswordProvider(url="", key="").sign_in("a@b.com", "pw")
    assert not outcome.succeeded
    assert "not configured" in outcome.error


def test_supabase_reports_a_missing_package_as_a_missing_package(monkeypatch):
    """The acquired system imported supabase at module scope, so its absence made the
    entire application unstartable."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "supabase":
            raise ImportError("no supabase here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    outcome = SupabasePasswordProvider(url="https://x", key="k").sign_in("a@b.com", "pw")

    assert not outcome.succeeded
    assert "not installed" in outcome.error


def test_an_unreachable_auth_service_is_not_reported_as_a_bad_password(monkeypatch):
    """Otherwise the user resets a password that was never the problem."""
    import sys
    import types

    module = types.ModuleType("supabase")

    def create_client(url, key):
        raise ConnectionError("DNS failure")

    module.create_client = create_client
    monkeypatch.setitem(sys.modules, "supabase", module)

    outcome = SupabasePasswordProvider(url="https://x", key="k").sign_in("a@b.com", "pw")

    assert not outcome.succeeded
    assert "Could not reach" in outcome.error
    assert "do not match" not in outcome.error


def test_supabase_success_yields_a_namespaced_principal(monkeypatch):
    import sys
    import types

    module = types.ModuleType("supabase")

    class FakeUser:
        id = "abc-123"
        email = "user@example.com"

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return types.SimpleNamespace(user=FakeUser())

    module.create_client = lambda url, key: types.SimpleNamespace(auth=FakeAuth())
    monkeypatch.setitem(sys.modules, "supabase", module)

    outcome = SupabasePasswordProvider(url="https://x", key="k").sign_in(
        "user@example.com", "pw"
    )

    assert outcome.succeeded
    # Namespaced so a local account and a Supabase account can never collide on id.
    assert outcome.principal.user_id == "supabase:abc-123"


def test_supabase_rejects_a_response_with_no_user(monkeypatch):
    import sys
    import types

    module = types.ModuleType("supabase")

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return types.SimpleNamespace(user=None)

    module.create_client = lambda url, key: types.SimpleNamespace(auth=FakeAuth())
    monkeypatch.setitem(sys.modules, "supabase", module)

    outcome = SupabasePasswordProvider(url="https://x", key="k").sign_in("a@b.com", "pw")
    assert not outcome.succeeded


# --------------------------------------------------------------------------- #
# Anonymous and selection
# --------------------------------------------------------------------------- #


def test_anonymous_always_succeeds_with_a_stable_id():
    """A random id per session would make persistence appear to work and then lose everything."""
    first = AnonymousProvider().sign_in()
    second = AnonymousProvider().sign_in()

    assert first.succeeded
    assert first.principal.user_id == second.principal.user_id == ANONYMOUS.user_id
    assert first.principal.is_anonymous


def test_provider_selection_prefers_supabase(monkeypatch, store):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    assert build_provider(store).name == "supabase"


def test_provider_selection_falls_back_to_local(monkeypatch, store):
    import json

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("SCRCAE_USERS", json.dumps({"a@b.com": hash_password("x")}))
    assert build_provider(store).name == "local"


def test_provider_selection_falls_back_to_anonymous(monkeypatch, store):
    """Falls back to an open door, not a locked one — but the UI must say which."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SCRCAE_USERS", raising=False)
    assert build_provider(store).name == "anonymous"


def test_a_principal_needs_an_id():
    with pytest.raises(ValueError, match="needs a user_id"):
        Principal(user_id="")


def test_outcome_without_a_principal_has_not_succeeded():
    assert not AuthOutcome(error="nope").succeeded


def test_an_unknown_account_costs_the_same_as_a_wrong_password():
    """No account-enumeration oracle in sign-in's timing.

    `sign_in` deliberately verifies a password even when the address is unknown,
    so the two failures cost the same. The first implementation of that idea made
    it worse than doing nothing: it built a throwaway hash *per attempt* and then
    verified against it, so an unknown account ran PBKDF2 twice against a known
    account's once. Measured at this iteration count, 158.0 ms against 316.9 ms —
    a 2.01x ratio, remotely observable through jitter in a few samples. The fix is
    a module-level reference hash, computed once, so both paths run PBKDF2 exactly
    once; the same measurement then gives 1.004x.

    This asserts the *work done*, not the wall-clock. A timing assertion on a
    shared CI runner would be flaky in both directions, and flaky security tests
    get deleted. Counting PBKDF2 invocations is what the fix actually changed, and
    it is deterministic.
    """
    from unittest.mock import patch

    from app.auth import providers

    users = {"real@example.com": providers.hash_password("a-real-password")}
    provider = providers.LocalPasswordProvider(users)

    def _count(email: str) -> int:
        calls = 0
        real = providers.hashlib.pbkdf2_hmac

        def counting(*args, **kwargs):
            nonlocal calls
            calls += 1
            return real(*args, **kwargs)

        with patch.object(providers.hashlib, "pbkdf2_hmac", counting):
            outcome = provider.sign_in(email, "the-wrong-password")
        assert outcome.principal is None, "both of these must fail to sign in"
        return calls

    known = _count("real@example.com")
    unknown = _count("nobody@example.com")
    assert known == 1, f"a known account should hash once, hashed {known}x"
    assert unknown == known, (
        f"unknown account hashed {unknown}x against {known}x for a known one: "
        "that difference is an account-enumeration oracle"
    )


def test_the_absent_account_reference_is_a_real_unguessable_hash():
    """The shared reference must not be verifiable against, or it is a backdoor.

    Reusing one hash for every unknown address is only safe because the password
    behind it is random and discarded. If it ever became a constant, a fixed
    string, or an empty password, every non-existent address would accept a known
    credential — and `sign_in`'s `and encoded is not None` would be the only thing
    standing between that and a login.
    """
    from app.auth import providers

    reference = providers._ABSENT_ACCOUNT_REFERENCE
    assert reference.startswith("pbkdf2_sha256$")
    for guess in ("", " ", "password", "secret", reference, "0" * 64):
        assert not providers.verify_password(guess, reference)
