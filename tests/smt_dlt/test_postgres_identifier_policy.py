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


def test_reserved_suffix_collision_with_trailing_underscore_is_known_limitation():
    # Documents the limitation: per-name reserved-word suffixing collides with
    # a literal trailing-underscore form of the same root. detect_logical_collisions
    # treats these as distinct (which is correct at the logical layer), so the
    # duplicate slips through to physical names. Resolution: a future
    # detect_physical_collisions batch check (Plan 4 / follow-up).
    p = postgres_identifier_policy()
    assert p.physical_name("select") == "select_"
    assert p.physical_name("select_") == "select_"
    # Both produce the same physical name — collision is not raised at this layer.


def test_short_names_unchanged():
    p = postgres_identifier_policy()
    assert p.physical_name("short_name") == "short_name"


def test_too_long_name_is_shortened_to_max_length():
    p = postgres_identifier_policy()  # max 63
    name = "x" * 100
    out = p.physical_name(name)
    assert len(out) == 63


def test_shortening_is_deterministic():
    p = postgres_identifier_policy()
    name = "x" * 100
    assert p.physical_name(name) == p.physical_name(name)


def test_shortening_disambiguates_different_inputs_with_same_prefix():
    p = postgres_identifier_policy()
    a = "a" * 100
    b = "a" * 99 + "b"  # same 63-char prefix once truncated
    # Both are >63 chars; the hash suffix MUST differ.
    assert p.physical_name(a) != p.physical_name(b)
    assert len(p.physical_name(a)) == 63
    assert len(p.physical_name(b)) == 63


def test_shortening_preserves_prefix():
    # The first (max_length - 9) characters of the shortened output should
    # match the corresponding prefix of the folded input — locks the format.
    p = postgres_identifier_policy()
    name = "x" * 100
    out = p.physical_name(name)
    assert out.startswith("x" * (63 - 9))
    assert out[63 - 9] == "_"
