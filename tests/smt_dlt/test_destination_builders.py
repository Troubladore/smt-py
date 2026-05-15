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
        schema="bronze",
    )
    assert dest is not None


def test_snowflake_destination_requires_exactly_one_auth_zero():
    with pytest.raises(ValueError, match="Exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            database="d",
            schema="s",
        )


def test_snowflake_destination_requires_exactly_one_auth_two():
    with pytest.raises(ValueError, match="Exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            password="p",
            private_key="k",
            database="d",
            schema="s",
        )


def test_snowflake_destination_requires_exactly_one_auth_three():
    with pytest.raises(ValueError, match="Exactly one"):
        build_snowflake_destination(
            account_identifier="a",
            user="u",
            password="p",
            private_key="k",
            oauth_token="t",
            database="d",
            schema="s",
        )


def test_snowflake_destination_accepts_password_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        password="p",
        database="d",
        schema="s",
    )
    assert dest is not None


def test_snowflake_destination_accepts_private_key_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
        database="d",
        schema="s",
    )
    assert dest is not None


def test_snowflake_destination_accepts_oauth_token_only():
    dest = build_snowflake_destination(
        account_identifier="a",
        user="u",
        oauth_token="oauth-token-here",
        database="d",
        schema="s",
    )
    assert dest is not None
