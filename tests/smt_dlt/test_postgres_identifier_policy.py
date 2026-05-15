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


def test_two_postgres_policies_compare_equal():
    # Frozen dataclass + value-typed fields → equality should be by value.
    assert postgres_identifier_policy() == postgres_identifier_policy()


def test_policy_is_picklable():
    import pickle
    p = postgres_identifier_policy()
    restored = pickle.loads(pickle.dumps(p))
    assert restored == p
    assert restored.physical_name("alpha") == "alpha"


def test_reserved_word_gets_underscore_suffix_postgres():
    p = postgres_identifier_policy()
    # SQL reserved word.
    assert p.physical_name("select") == "select_"
    assert p.physical_name("table") == "table_"


def test_non_reserved_word_unchanged_postgres():
    p = postgres_identifier_policy()
    assert p.physical_name("customer") == "customer"


def test_metadata_name_unaffected_by_reserved_word():
    # Reserved-word handling is physical-layer only.
    p = postgres_identifier_policy()
    assert p.sqlalchemy_metadata_name("select") == "select"
