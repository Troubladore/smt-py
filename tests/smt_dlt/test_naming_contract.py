import pytest
from smt_dlt.naming import NamingConvention, SmtCanonicalNamingConvention


def test_class_is_named_exactly_NamingConvention():
    # dlt's custom-convention import contract requires this exact class name.
    assert NamingConvention.__name__ == "NamingConvention"


def test_smt_alias_points_at_same_class():
    assert SmtCanonicalNamingConvention is NamingConvention


def test_is_case_insensitive():
    nc = NamingConvention()
    assert nc.is_case_sensitive is False


def test_inherits_from_dlt_NamingConvention():
    from dlt.common.normalizers.naming import NamingConvention as DltNC
    assert issubclass(NamingConvention, DltNC)


@pytest.fixture
def nc():
    return NamingConvention()


def test_lowercases_ascii(nc):
    assert nc.normalize_identifier("CustomerID") == "customerid"


def test_lowercases_all_caps(nc):
    assert nc.normalize_identifier("ORDER") == "order"


def test_replaces_non_word_chars_with_underscore(nc):
    assert nc.normalize_identifier("first name") == "first_name"
    assert nc.normalize_identifier("price$") == "price_"
    assert nc.normalize_identifier("a-b") == "a_b"


def test_leading_digit_is_prefixed_with_underscore(nc):
    assert nc.normalize_identifier("123abc") == "_123abc"


def test_preserves_existing_underscores(nc):
    assert nc.normalize_identifier("foo_bar") == "foo_bar"


def test_preserves_double_underscore_literal(nc):
    # sql_ci_v1 collapses __ to _; we deliberately do not.
    assert nc.normalize_identifier("orders__items") == "orders__items"


def test_preserves_triple_underscore(nc):
    assert nc.normalize_identifier("a___b") == "a___b"


def test_preserves_trailing_underscore(nc):
    # sql_ci_v1 strips trailing _; we deliberately do not (foo/foo_ stay distinct).
    assert nc.normalize_identifier("foo_") == "foo_"


def test_preserves_multiple_trailing_underscores(nc):
    assert nc.normalize_identifier("bar___") == "bar___"


def test_empty_string_raises(nc):
    with pytest.raises(ValueError, match="non-empty"):
        nc.normalize_identifier("")


def test_none_raises_typeerror(nc):
    with pytest.raises(TypeError, match="must be a string"):
        nc.normalize_identifier(None)  # type: ignore[arg-type]


def test_normalize_tables_path_preserves_double_underscore(nc):
    # dlt internally calls normalize_tables_path; it must not split on __.
    assert nc.normalize_tables_path("orders__items") == "orders__items"


def test_normalize_tables_path_lowercases(nc):
    assert nc.normalize_tables_path("OrderItems") == "orderitems"


def test_break_path_returns_single_element(nc):
    assert list(nc.break_path("orders__items")) == ["orders__items"]


def test_normalize_path_also_preserves_double_underscore(nc):
    # normalize_path is a distinct dlt code path from normalize_tables_path;
    # the flat-path override must cover both.
    assert nc.normalize_path("a__b") == "a__b"
