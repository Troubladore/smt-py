import pytest
from smt_dlt.naming import make_dataset_name
from smt.config import _sanitize_identifier


@pytest.mark.parametrize(
    "host, database, schema, expected",
    [
        ("localhost", "MyDB", "dbo", "localhost__mydb__dbo"),
        ("10.0.0.5", "CRM", "Sales", "_10_0_0_5__crm__sales"),
        ("db.eruditis.com", "Prod", "public", "db_eruditis_com__prod__public"),
        ("HOST", "DB", "schema", "host__db__schema"),
    ],
)
def test_make_dataset_name_known_outputs(host, database, schema, expected):
    assert make_dataset_name(source_host=host, source_database=database, source_schema=schema) == expected


@pytest.mark.parametrize(
    "host, database, schema",
    [
        ("localhost", "MyDB", "dbo"),
        ("10.0.0.5", "CRM", "Sales"),
        ("db.eruditis.com", "Prod", "public"),
        ("HOST", "DB", "schema"),
        ("Server_01", "AdventureWorks", "Person"),
        ("db-01.example.com", "MyDB", "dbo"),
        ("db–prod.example.com", "MyDB", "dbo"),
    ],
)
def test_parity_with_legacy(host, database, schema):
    # Replicates the composition in src/smt/config.py:__post_init__.
    legacy = (
        f"{_sanitize_identifier(host)}"
        f"__{database.lower()}"
        f"__{schema.lower()}"
    )
    assert make_dataset_name(source_host=host, source_database=database, source_schema=schema) == legacy


def test_leading_digit_host_is_prefixed():
    assert make_dataset_name(source_host="9server", source_database="db", source_schema="schema") == "_9server__db__schema"


def test_deterministic():
    a = make_dataset_name(source_host="host", source_database="db", source_schema="schema")
    b = make_dataset_name(source_host="host", source_database="db", source_schema="schema")
    assert a == b


# ---- Intentional deviations from legacy `_sanitize_identifier` ----


def test_empty_host_raises():
    # Legacy silently produced "__db__schema"; new function requires a real host.
    with pytest.raises((TypeError, ValueError)):
        make_dataset_name(source_host="", source_database="db", source_schema="dbo")


def test_unicode_lowercase_to_ascii_is_preserved():
    # Kelvin sign U+212A is a non-ASCII character that lowercases to ASCII 'k'.
    # Legacy filters non-ASCII BEFORE lowercasing, so it would be replaced with '_'.
    # New lowercases first, so it becomes 'k' and survives the identifier filter.
    result = make_dataset_name(source_host="K-host", source_database="db", source_schema="dbo")
    assert "k_host" in result
