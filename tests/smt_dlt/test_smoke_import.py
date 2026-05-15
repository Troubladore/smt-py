def test_smt_dlt_imports():
    import smt_dlt  # noqa: F401
    import smt_dlt.naming  # noqa: F401


def test_dlt_naming_base_class_importable():
    from dlt.common.normalizers.naming import NamingConvention as DltNamingConvention
    assert DltNamingConvention is not None
