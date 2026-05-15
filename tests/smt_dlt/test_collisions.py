import pytest
from smt_dlt.naming import detect_logical_collisions


def test_no_collisions_returns_empty():
    result = detect_logical_collisions(["alpha", "beta", "gamma"])
    assert result == {}


def test_single_collision_returned():
    # "Customer ID" and "customer_id" both normalize to "customer_id".
    result = detect_logical_collisions(["Customer ID", "customer_id"])
    assert result == {"customer_id": ["Customer ID", "customer_id"]}


def test_multiple_collisions():
    result = detect_logical_collisions(
        ["First Name", "first_name", "Last Name", "last_name", "Email"]
    )
    assert result == {
        "first_name": ["First Name", "first_name"],
        "last_name": ["Last Name", "last_name"],
    }


def test_trailing_underscore_stays_distinct():
    # SMT preserves trailing underscores, so foo and foo_ DO NOT collide.
    result = detect_logical_collisions(["foo", "foo_"])
    assert result == {}


def test_double_underscore_stays_distinct():
    # SMT preserves double underscores.
    result = detect_logical_collisions(["a_b", "a__b"])
    assert result == {}


def test_raises_helper_produces_clear_error():
    from smt_dlt.naming import raise_on_logical_collisions
    with pytest.raises(ValueError) as exc:
        raise_on_logical_collisions(["Customer ID", "customer_id"])
    msg = str(exc.value)
    assert "customer_id" in msg
    assert "Customer ID" in msg
