import pytest
from smt_dlt.destinations import (
    build_postgres_destination,
    build_snowflake_destination,
)


def test_postgres_destination_returns_dlt_destination_object():
    dest = build_postgres_destination(
        connection_string="postgresql://u:p@h/db",
    )
    assert dest is not None


def test_snowflake_destination_returns_dlt_destination_object():
    dest = build_snowflake_destination(
        account_identifier="acct.region",
        user="u",
        password="p",
        database="db",
    )
    assert dest is not None


def test_snowflake_destination_requires_exactly_one_auth_zero():
    with pytest.raises(ValueError, match="exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            database="d",
        )


def test_snowflake_destination_requires_exactly_one_auth_two():
    with pytest.raises(ValueError, match="exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            password="p",
            private_key="k",
            database="d",
        )


def test_snowflake_destination_requires_exactly_one_auth_three():
    with pytest.raises(ValueError, match="exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            password="p",
            private_key="k",
            oauth_token="t",
            database="d",
        )


def test_snowflake_destination_accepts_password_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        password="p",
        database="d",
    )
    assert dest is not None


def test_snowflake_destination_accepts_private_key_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
        database="d",
    )
    assert dest is not None


def test_snowflake_destination_accepts_oauth_token_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        oauth_token="oauth-token-here",
        database="d",
    )
    assert dest is not None


def test_snowflake_oauth_token_maps_to_token_key():
    """The builder renames our kwarg `oauth_token` to dlt's expected key `token`.
    Confirms the value actually lands under the right key — this is the only
    non-obvious rename in the builder, so we assert it rather than just trusting it.
    """
    dest = build_snowflake_destination(
        account_identifier="acct.region",
        user="u",
        oauth_token="oauth-value-here",
        database="db",
    )
    # dlt destination factory objects (current dlt 1.x) expose credentials via
    # `config_params`. If the attribute name changes in a future dlt release,
    # this test fails loudly — at which point update the attribute lookup AND
    # confirm the underlying rename still works.
    config_params = getattr(dest, "config_params", None)
    assert config_params is not None, (
        "dlt destination no longer exposes `config_params`; update this test for the new attr"
    )
    creds = config_params.get("credentials", {})
    assert isinstance(creds, dict), f"Expected credentials dict; got {type(creds).__name__}"
    assert creds.get("token") == "oauth-value-here", (
        f"Expected 'token' key with oauth_token value; got credentials={creds!r}"
    )
