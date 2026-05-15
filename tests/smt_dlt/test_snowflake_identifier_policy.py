from smt_dlt.destinations import snowflake_identifier_policy, IdentifierPolicy


def test_returns_IdentifierPolicy():
    assert isinstance(snowflake_identifier_policy(), IdentifierPolicy)


def test_target_is_snowflake():
    assert snowflake_identifier_policy().target == "snowflake"


def test_max_length_is_255():
    assert snowflake_identifier_policy().max_length == 255


def test_sqlalchemy_metadata_name_is_lowercase_even_for_snowflake():
    # The whole point of the policy split: SQLAlchemy-facing names stay
    # lowercase so snowflake-sqlalchemy emits unquoted identifiers.
    p = snowflake_identifier_policy()
    assert p.sqlalchemy_metadata_name("customer_id") == "customer_id"
    assert p.sqlalchemy_metadata_name("CUSTOMER_ID") == "customer_id"


def test_physical_name_is_uppercase():
    # The warehouse catalog stores uppercase, matching Snowflake's
    # unquoted-identifier folding.
    p = snowflake_identifier_policy()
    assert p.physical_name("customer_id") == "CUSTOMER_ID"
    assert p.physical_name("orders__items") == "ORDERS__ITEMS"


def test_metadata_and_physical_differ_in_case():
    p = snowflake_identifier_policy()
    assert p.sqlalchemy_metadata_name("x") != p.physical_name("x")
    assert p.sqlalchemy_metadata_name("x") == "x"
    assert p.physical_name("x") == "X"
