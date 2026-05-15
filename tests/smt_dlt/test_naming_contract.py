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
