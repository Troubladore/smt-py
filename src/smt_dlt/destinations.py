"""Per-target identifier policies and dlt destination builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from smt_dlt.naming import normalize_source_component  # noqa: F401  # used in subsequent tasks


@dataclass(frozen=True)
class IdentifierPolicy:
    """Per-target rules for translating a logical name into the names SQLAlchemy
    sees (metadata) and the warehouse stores (physical).
    """
    target: str  # "postgres" | "snowflake"
    max_length: int
    reserved_words: frozenset[str]
    _to_physical: Callable[[str], str] = field(repr=False)

    def sqlalchemy_metadata_name(self, logical: str) -> str:
        """SQLAlchemy-facing name. Always lowercase: snowflake-sqlalchemy treats
        lowercase identifiers as case-insensitive and emits them unquoted.
        """
        return logical.lower()

    def physical_name(self, logical: str) -> str:
        """The warehouse-stored form (as observed in INFORMATION_SCHEMA)."""
        return self._to_physical(logical)


# Concrete policies are added in subsequent tasks.

def postgres_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="postgres",
        max_length=63,
        reserved_words=frozenset(),  # populated in Task 11
        _to_physical=lambda name: name.lower(),
    )
