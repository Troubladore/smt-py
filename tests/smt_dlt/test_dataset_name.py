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
