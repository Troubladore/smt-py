import importlib
import pytest


MODULE_PATH = "smt_dlt.naming"


def test_module_has_class_named_NamingConvention():
    module = importlib.import_module(MODULE_PATH)
    assert hasattr(module, "NamingConvention"), (
        "dlt loads custom conventions via getattr(module, 'NamingConvention'). "
        "Renaming or removing this attribute breaks dlt's import contract."
    )
    cls = module.NamingConvention
    assert cls.__name__ == "NamingConvention"


def test_class_is_instantiable_with_dlt_init_signature():
    module = importlib.import_module(MODULE_PATH)
    # dlt instantiates NamingConvention(max_length=None) by default.
    instance = module.NamingConvention(max_length=None)
    assert instance is not None


def test_class_can_be_loaded_through_dlt_factory_signature():
    # Simulate dlt's lookup path: import-by-string + getattr.
    module = importlib.import_module(MODULE_PATH)
    cls = getattr(module, "NamingConvention")
    instance = cls(max_length=None)
    assert instance.normalize_identifier("Foo") == "foo"


def test_alias_is_same_class():
    module = importlib.import_module(MODULE_PATH)
    assert module.SmtCanonicalNamingConvention is module.NamingConvention
