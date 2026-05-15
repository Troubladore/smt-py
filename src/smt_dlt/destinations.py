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
        applies destination-specific case folding and reserved-word
        suffixing.
        """
        # Reserved-word check uses case-folded comparison so the rule
        # applies regardless of which case `_to_physical` will fold to.
        if logical.lower() in self.reserved_words:
            logical = logical + "_"
        return self._to_physical(logical)


# Subset of SQL:1999 reserved words common to most engines. Expanded during proof work.
_POSTGRES_RESERVED = frozenset({
    "all", "analyse", "analyze", "and", "any", "array", "as", "asc", "asymmetric",
    "both", "case", "cast", "check", "collate", "column", "constraint", "create",
    "current_date", "current_time", "current_timestamp", "current_user", "default",
    "deferrable", "desc", "distinct", "do", "else", "end", "except", "false", "fetch",
    "for", "foreign", "from", "grant", "group", "having", "in", "initially", "intersect",
    "into", "lateral", "leading", "limit", "localtime", "localtimestamp", "not", "null",
    "offset", "on", "only", "or", "order", "placing", "primary", "references", "returning",
    "select", "session_user", "some", "symmetric", "table", "then", "to", "trailing",
    "true", "union", "unique", "user", "using", "variadic", "when", "where", "window", "with",
})

# Snowflake reserved-word set (subset; ref: docs.snowflake.com/en/sql-reference/reserved-keywords).
_SNOWFLAKE_RESERVED = frozenset({
    "account", "all", "alter", "and", "any", "as", "between", "by", "case", "cast",
    "check", "column", "connect", "constraint", "create", "cross", "current",
    "current_date", "current_time", "current_timestamp", "current_user", "delete",
    "distinct", "drop", "else", "exists", "false", "following", "for", "from", "full",
    "grant", "group", "having", "ilike", "in", "increment", "inner", "insert",
    "intersect", "into", "is", "issue", "join", "lateral", "left", "like", "localtime",
    "localtimestamp", "minus", "natural", "not", "null", "of", "on", "or", "order",
    "organization", "qualify", "regexp", "revoke", "right", "rlike", "row", "rows",
    "sample", "schema", "select", "set", "some", "start", "table", "tablesample",
    "then", "to", "trigger", "true", "try_cast", "union", "unique", "update", "using",
    "values", "view", "when", "whenever", "where", "with",
})


def postgres_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="postgres",
        max_length=63,
        reserved_words=_POSTGRES_RESERVED,
        # str.lower (the bound-method-on-the-class) is picklable and gives
        # value-equality semantics across calls. A lambda would defeat both.
        _to_physical=str.lower,
    )


def snowflake_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="snowflake",
        max_length=255,
        reserved_words=_SNOWFLAKE_RESERVED,
        # str.upper preserves picklability and value-equality across calls.
        _to_physical=str.upper,
    )
