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
