"""SMT canonical naming and destination identifier policy for dlt."""

from smt_dlt.naming import (
    NamingConvention,
    SmtCanonicalNamingConvention,
    normalize_source_component,
    normalize_table_name,
    normalize_column_name,
    make_dataset_name,
    detect_logical_collisions,
    raise_on_logical_collisions,
)
from smt_dlt.destinations import (
    IdentifierPolicy,
    postgres_identifier_policy,
    snowflake_identifier_policy,
    build_postgres_destination,
    build_snowflake_destination,
)

__all__ = [
    "NamingConvention",
    "SmtCanonicalNamingConvention",
    "normalize_source_component",
    "normalize_table_name",
    "normalize_column_name",
    "make_dataset_name",
    "detect_logical_collisions",
    "raise_on_logical_collisions",
    "IdentifierPolicy",
    "postgres_identifier_policy",
    "snowflake_identifier_policy",
    "build_postgres_destination",
    "build_snowflake_destination",
]
