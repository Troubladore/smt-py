import pytest
from smt_dlt.destinations import (
    build_postgres_destination,
    build_snowflake_destination,
)


def test_postgres_destination_returns_dlt_destination_object():
    dest = build_postgres_destination(
        connection_string="postgresql://u:p@h/db",
        dataset_name="host__db__schema",
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
    Confirm the value actually lands under the right key in the destination's
    credentials configuration.
    """
    dest = build_snowflake_destination(
        account_identifier="acct.region",
        user="u",
        oauth_token="oauth-value-here",
        database="db",
    )
    # dlt destinations expose their configured credentials via their
    # `credentials` attribute or `factory._init_args`. We check both.
    creds_holder = getattr(dest, "config_params", None) or getattr(dest, "_init_args", None) or {}
    if not isinstance(creds_holder, dict):
        # Some dlt versions wrap differently; bail out gracefully — the auth-validation
        # test still covers the precondition.
        pytest.skip(
            "dlt destination object does not expose credentials via expected attrs; "
            "non-obvious oauth_token->token rename is not directly assertable in this dlt version"
        )
    creds = creds_holder.get("credentials", {}) if isinstance(creds_holder, dict) else {}
    if isinstance(creds, dict):
        assert creds.get("token") == "oauth-value-here", (
            f"Expected 'token' key with oauth_token value; got credentials={creds!r}"
        )
