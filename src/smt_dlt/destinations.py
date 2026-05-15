"""Per-target identifier policies and dlt destination builders."""

from __future__ import annotations

import hashlib
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
        applies destination-specific case folding, reserved-word suffixing,
        and max-length shortening with a deterministic hash suffix when
        necessary. Suffixing happens BEFORE folding so that on Snowflake
        ``"select"`` becomes ``"SELECT_"`` (not ``"SELECT" + "_"`` then
        re-folded).

        Known limitation: per-name suffixing does NOT detect collisions
        between a reserved name and an already-distinct logical name that
        happens to match the suffixed form. For example, the source schema
        having both ``"select"`` (reserved → suffixed to ``"select_"``) and
        ``"select_"`` (literal, not reserved → stays ``"select_"``) maps both
        to the same physical name. ``detect_logical_collisions`` treats these
        as distinct logical inputs, so the duplicate slips past the logical
        check. Tracked as
        https://github.com/Troubladore/smt-py/issues/1 — resolution is a
        batch-level ``detect_physical_collisions``.
        """
        if logical.lower() in self.reserved_words:
            logical = logical + "_"
        folded = self._to_physical(logical)
        if len(folded) > self.max_length:
            folded = self._shorten(folded)
        return folded

    def _shorten(self, name: str) -> str:
        # Reserve 8 chars for a hash suffix to disambiguate truncations.
        suffix_len = 8
        keep = self.max_length - suffix_len - 1  # -1 for the separator '_'
        digest = hashlib.blake2b(name.encode("utf-8"), digest_size=4).hexdigest()
        return f"{name[:keep]}_{digest}"


# Subset of SQL:1999 reserved words common to most engines, plus common-in-real-
# source-schemas keywords that PG marks as reserved at the "can be column or
# type" level (key, value, type, name, id, comment, etc.). Expanded during proof
# work as concrete collisions surface.
_POSTGRES_RESERVED = frozenset({
    "all", "analyse", "analyze", "and", "any", "array", "as", "asc", "asymmetric",
    "both", "case", "cast", "check", "collate", "column", "comment", "constraint",
    "create", "current_date", "current_time", "current_timestamp", "current_user",
    "database", "default", "deferrable", "desc", "distinct", "do", "else", "end",
    "except", "false", "fetch", "for", "foreign", "from", "function", "grant",
    "group", "having", "id", "in", "index", "initially", "intersect", "into",
    "key", "lateral", "leading", "limit", "localtime", "localtimestamp", "name",
    "not", "null", "offset", "on", "only", "or", "order", "placing", "primary",
    "procedure", "references", "returning", "role", "schema", "select",
    "sequence", "session_user", "some", "symmetric", "table", "then", "to",
    "trailing", "trigger", "true", "type", "union", "unique", "user", "using",
    "value", "variadic", "view", "when", "where", "window", "with",
})

# Snowflake reserved-word set: subset of Snowflake's reserved keywords plus
# common-in-real-source-schemas names that Snowflake treats as reserved
# (database, key, value, type, name, etc.).
_SNOWFLAKE_RESERVED = frozenset({
    "account", "all", "alter", "and", "any", "as", "between", "by", "case", "cast",
    "check", "column", "comment", "connect", "constraint", "create", "cross",
    "current", "current_date", "current_time", "current_timestamp", "current_user",
    "database", "delete", "distinct", "drop", "else", "exists", "false", "following",
    "for", "from", "full", "function", "grant", "group", "having", "id", "ilike",
    "in", "increment", "index", "inner", "insert", "intersect", "into", "is",
    "issue", "join", "key", "lateral", "left", "like", "localtime", "localtimestamp",
    "minus", "name", "natural", "not", "null", "of", "on", "or", "order",
    "organization", "procedure", "qualify", "regexp", "revoke", "right", "rlike",
    "role", "row", "rows", "sample", "schema", "select", "sequence", "set", "some",
    "start", "table", "tablesample", "then", "to", "trigger", "true", "try_cast",
    "type", "union", "unique", "update", "using", "value", "values", "view", "when",
    "whenever", "where", "with",
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
