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
        """SQLAlchemy-facing name for a SMT canonical (already-normalized) name.

        ``logical`` MUST already be a canonical SMT identifier — i.e. the
        output of ``smt_dlt.naming.normalize_identifier`` /
        ``normalize_source_component``. This method does not re-normalize;
        raw source names containing dots, hyphens, spaces, or other
        non-identifier characters will pass through unchanged and produce
        invalid SQL.

        Always returns lowercase: ``snowflake-sqlalchemy`` treats lowercase
        identifiers as case-insensitive and emits them unquoted, matching
        Postgres's natural unquoted folding direction.
        """
        return logical.lower()

    def physical_name(self, logical: str) -> str:
        """The warehouse-stored form (as observed in ``INFORMATION_SCHEMA``).

        ``logical`` MUST already be a canonical SMT identifier (see
        ``sqlalchemy_metadata_name`` for the input contract). This method
        applies destination-specific case folding and (in later tasks)
        reserved-word suffixing and max-length shortening.
        """
        return self._to_physical(logical)


# Concrete policies are added in subsequent tasks.

def postgres_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="postgres",
        max_length=63,
        reserved_words=frozenset(),  # populated in Task 11
        # str.lower (the bound-method-on-the-class) is picklable and gives
        # value-equality semantics across calls. A lambda would defeat both.
        _to_physical=str.lower,
    )
