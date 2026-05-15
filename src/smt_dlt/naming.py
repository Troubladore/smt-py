"""SMT canonical naming for dlt.

dlt loads custom naming conventions by importing the module and looking up
a class named exactly ``NamingConvention``. ``SmtCanonicalNamingConvention``
is a human-readable alias for use elsewhere in the codebase.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from dlt.common.normalizers.naming import NamingConvention as _DltNamingConvention

# Applied after `.lower()`, so uppercase letters are already folded out.
_NON_WORD = re.compile(r"[^a-z0-9_]")


class NamingConvention(_DltNamingConvention):
    """SMT canonical case-insensitive naming convention."""

    @property
    def is_case_sensitive(self) -> bool:
        return False

    def normalize_identifier(self, identifier: str) -> str:
        if not isinstance(identifier, str):
            raise TypeError("identifier must be a string")
        if not identifier:
            raise ValueError("identifier must be a non-empty string")
        lowered = identifier.lower()
        cleaned = _NON_WORD.sub("_", lowered)
        if cleaned[0].isdigit():
            cleaned = "_" + cleaned
        return cleaned

    def break_path(self, path: str) -> list[str]:
        # SMT source identifiers are flat. We never use `__` as a path separator.
        # Note: without this override, dlt's default split-then-rejoin happens to be
        # lossless for already-normalized names — but pinning `[path]` makes the
        # intent explicit and guards against future dlt changes to PATH_SEPARATOR
        # handling.
        return [path]


SmtCanonicalNamingConvention = NamingConvention

_DEFAULT = NamingConvention()


def normalize_source_component(name: str) -> str:
    """Normalize a single SMT source identifier (host segment, schema, etc.)."""
    return _DEFAULT.normalize_identifier(name)


def normalize_table_name(name: str) -> str:
    """Normalize a source table name."""
    return _DEFAULT.normalize_identifier(name)


def normalize_column_name(name: str) -> str:
    """Normalize a source column name."""
    return _DEFAULT.normalize_identifier(name)


def make_dataset_name(*, source_host: str, source_database: str, source_schema: str) -> str:
    """Deterministically derive a dataset name from source instance + DB + schema.

    Replaces ``src/smt/config.py::_sanitize_identifier``-based composition.
    Output: ``{sanitized_host}__{lowercased_db}__{lowercased_schema}``.

    Intentional deviations from the legacy composition:

    * ``source_host`` must be a non-empty string. The legacy function silently
      accepted ``""`` and produced ``"__{db}__{schema}"`` — almost certainly
      not what the caller wanted.
    * Unicode characters in ``source_host`` that lowercase to valid ASCII
      identifier characters (e.g. Kelvin sign ``K`` U+212A → ``k``) are
      *preserved* rather than replaced with ``_``. The legacy regex filtered
      before lowercasing, losing the information.

    ``source_database`` and ``source_schema`` are currently only lowercased,
    matching the legacy composition. Plan 4 may tighten this to full
    identifier sanitization once the legacy function is retired.
    """
    host_part = normalize_source_component(source_host)
    db_part = source_database.lower()
    schema_part = source_schema.lower()
    return f"{host_part}__{db_part}__{schema_part}"


def detect_logical_collisions(source_names: Iterable[str]) -> dict[str, list[str]]:
    """Return a mapping of logical-name → originals whenever two or more source
    names normalize to the same logical name. Empty dict means no collisions.
    """
    buckets: dict[str, list[str]] = defaultdict(list)
    for name in source_names:
        buckets[normalize_source_component(name)].append(name)
    return {logical: originals for logical, originals in buckets.items() if len(originals) > 1}


def raise_on_logical_collisions(source_names: Iterable[str]) -> None:
    """Raise ValueError naming every collision; no-op when there are none."""
    collisions = detect_logical_collisions(source_names)
    if not collisions:
        return
    lines = [
        f"  - {logical!r} ← {', '.join(repr(o) for o in originals)}"
        for logical, originals in collisions.items()
    ]
    raise ValueError(
        "Source identifiers collide under SMT canonical normalization:\n"
        + "\n".join(lines)
    )
