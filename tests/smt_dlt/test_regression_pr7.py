"""Regression tests ported from PR #7 (johndauphine/smt-py#7).

These pin behaviors that the dlt sql_ci_v1 convention got wrong and that we
explicitly correct in SmtCanonicalNamingConvention. They are intentionally
located here (not in the generator test suite) because the naming contract
is the source of truth — sqlacodegen now reflects already-normalized names.
"""
from smt_dlt.naming import (
    NamingConvention,
    normalize_table_name,
    normalize_column_name,
    detect_logical_collisions,
)


def test_pr7_orders_double_underscore_preserved():
    """Regression: dlt's sql_ci_v1.normalize_identifier('orders__items')
    returned 'orders_items'. The SMT convention preserves __."""
    assert normalize_table_name("orders__items") == "orders__items"


def test_pr7_normalize_tables_path_preserves_double_underscore():
    nc = NamingConvention()
    assert nc.normalize_tables_path("orders__items") == "orders__items"


def test_pr7_trailing_underscore_preserved():
    """Regression: dlt's sql_ci_v1 stripped trailing _. The SMT convention
    preserves them so foo and foo_ remain distinct."""
    assert normalize_column_name("foo_") == "foo_"


def test_pr7_foo_and_foo_underscore_do_not_collide():
    """Regression: under sql_ci_v1, 'foo' and 'foo_' both normalize to 'foo'
    and trigger SQLAlchemy DuplicateColumnError. Under SMT, they stay distinct."""
    assert detect_logical_collisions(["foo", "foo_"]) == {}


def test_pr7_genuine_collision_still_caught():
    """The PR's compensation for collisions remains valid for collisions
    that actually exist (e.g., 'Customer ID' / 'customer_id')."""
    assert detect_logical_collisions(["Customer ID", "customer_id"]) == {
        "customer_id": ["Customer ID", "customer_id"],
    }
