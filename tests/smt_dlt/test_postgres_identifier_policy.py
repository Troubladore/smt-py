from smt_dlt.destinations import postgres_identifier_policy, IdentifierPolicy


def test_returns_IdentifierPolicy():
    p = postgres_identifier_policy()
    assert isinstance(p, IdentifierPolicy)


def test_max_length_is_63():
    assert postgres_identifier_policy().max_length == 63


def test_target_name_is_postgres():
    assert postgres_identifier_policy().target == "postgres"


def test_sqlalchemy_metadata_name_is_lowercase():
    p = postgres_identifier_policy()
    assert p.sqlalchemy_metadata_name("customer_id") == "customer_id"
    assert p.sqlalchemy_metadata_name("Customer_ID") == "customer_id"


def test_physical_name_is_lowercase():
    p = postgres_identifier_policy()
    assert p.physical_name("customer_id") == "customer_id"


def test_metadata_and_physical_agree_for_postgres():
    p = postgres_identifier_policy()
    for logical in ["alpha", "orders__items", "foo_", "123abc"]:
        normalized = p.sqlalchemy_metadata_name(logical)
        assert p.physical_name(logical) == normalized
