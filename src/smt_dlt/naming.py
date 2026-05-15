"""SMT canonical naming for dlt.

dlt loads custom naming conventions by importing the module and looking up
a class named exactly ``NamingConvention``. ``SmtCanonicalNamingConvention``
is a human-readable alias for use elsewhere in the codebase.
"""

from __future__ import annotations

from dlt.common.normalizers.naming import NamingConvention as _DltNamingConvention


class NamingConvention(_DltNamingConvention):
    """SMT canonical case-insensitive naming convention."""

    @property
    def is_case_sensitive(self) -> bool:
        return False

    def normalize_identifier(self, identifier: str) -> str:
        # Implemented in Task 3.
        raise NotImplementedError


SmtCanonicalNamingConvention = NamingConvention
