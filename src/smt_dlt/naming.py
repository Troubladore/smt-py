"""SMT canonical naming for dlt.

dlt loads custom naming conventions by importing the module and looking up
a class named exactly ``NamingConvention``. ``SmtCanonicalNamingConvention``
is a human-readable alias for use elsewhere in the codebase.
"""

from __future__ import annotations

import re

from dlt.common.normalizers.naming import NamingConvention as _DltNamingConvention

_NON_WORD = re.compile(r"[^a-z0-9_]")


class NamingConvention(_DltNamingConvention):
    """SMT canonical case-insensitive naming convention."""

    @property
    def is_case_sensitive(self) -> bool:
        return False

    def normalize_identifier(self, identifier: str) -> str:
        if not identifier:
            raise ValueError("identifier must be a non-empty string")
        lowered = identifier.lower()
        cleaned = _NON_WORD.sub("_", lowered)
        if cleaned[0].isdigit():
            cleaned = "_" + cleaned
        return cleaned


SmtCanonicalNamingConvention = NamingConvention
