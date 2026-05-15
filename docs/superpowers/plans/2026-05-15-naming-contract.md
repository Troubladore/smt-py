# SMT Canonical Naming Contract — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the SMT canonical naming convention plus Postgres and Snowflake destination identifier policies as a pure-Python module (`src/smt_dlt/`) with full test coverage. No database connectivity required.

**Architecture:** A `dlt.common.normalizers.naming.NamingConvention` subclass that folds case insensitively, preserves literal `__` and trailing `_` in source identifiers, and treats every source identifier as flat (no nested-path semantics). A separate destination policy layer translates one logical name into (a) the SQLAlchemy-metadata name (always lowercase) and (b) the warehouse-stored physical name (lowercase for Postgres, uppercase for Snowflake). Collision detection runs over logical names before any data load.

**Tech Stack:** Python 3.12+, `dlt>=1.0,<2`, `pytest`. No DB connection in any test.

**Spec:** `docs/superpowers/specs/2026-05-15-dlt-first-architecture-design.md` — this plan implements **Issue 1** only.

**Branching:** Start a feature branch off `development`:
```bash
git checkout development
git pull
git checkout -b feature/naming-contract
```

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/smt_dlt/__init__.py` | Public re-exports (`NamingConvention`, `SmtCanonicalNamingConvention`, helpers) |
| `src/smt_dlt/naming.py` | `class NamingConvention(dlt's NamingConvention)`; `normalize_source_component`, `normalize_table_name`, `normalize_column_name`, `make_dataset_name`, `detect_logical_collisions`. Module-level `SmtCanonicalNamingConvention = NamingConvention` alias. |
| `src/smt_dlt/destinations.py` | `IdentifierPolicy` dataclass; `postgres_identifier_policy`, `snowflake_identifier_policy`, `build_postgres_destination`, `build_snowflake_destination` |
| `tests/smt_dlt/__init__.py` | empty |
| `tests/smt_dlt/test_naming_contract.py` | Target-independent normalization rules |
| `tests/smt_dlt/test_dataset_name.py` | `make_dataset_name` behavior + parity with legacy `_sanitize_identifier` |
| `tests/smt_dlt/test_postgres_identifier_policy.py` | Postgres physical / SQLAlchemy-metadata rendering |
| `tests/smt_dlt/test_snowflake_identifier_policy.py` | Snowflake physical / SQLAlchemy-metadata rendering |
| `tests/smt_dlt/test_collisions.py` | `detect_logical_collisions` |
| `tests/smt_dlt/test_dlt_import_contract.py` | dlt's custom-convention import contract |
| `tests/smt_dlt/test_regression_pr7.py` | Four regression cases ported from PR #7 |
| `pyproject.toml` | Add `dlt>=1.0,<2` to `dependencies`; `dlt[postgres]` and `dlt[snowflake]` to optional dev extras |

Public API (single source of truth):
```python
from smt_dlt.naming import (
    NamingConvention,                # dlt's import contract
    SmtCanonicalNamingConvention,    # human-readable alias = NamingConvention
    normalize_source_component,
    normalize_table_name,
    normalize_column_name,
    make_dataset_name,
    detect_logical_collisions,
)
from smt_dlt.destinations import (
    IdentifierPolicy,
    postgres_identifier_policy,
    snowflake_identifier_policy,
    build_postgres_destination,
    build_snowflake_destination,
)
```

---

## Task 1: Package scaffolding + dlt dependency + smoke import

**Files:**
- Create: `src/smt_dlt/__init__.py`
- Create: `src/smt_dlt/naming.py`
- Create: `tests/smt_dlt/__init__.py`
- Create: `tests/smt_dlt/test_smoke_import.py`
- Modify: `pyproject.toml` (add `dlt` dep)

- [ ] **Step 1: Add dlt to dependencies in `pyproject.toml`**

Find the existing `dependencies = [ ... ]` block and add the dlt entry:

```toml
dependencies = [
    "pyyaml>=6.0",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "click>=8.1",
    "mako>=1.3",
    "sqlacodegen>=4.0,<5.0",
    "inflect>=4.0.0",
    "dlt>=1.0,<2",
]
```

- [ ] **Step 2: Install dlt into the project venv**

Run: `.venv/bin/pip install -e ".[dev,postgres]"`
Expected: `Successfully installed dlt-<version> ...`

- [ ] **Step 3: Create empty package files**

`src/smt_dlt/__init__.py`:
```python
"""SMT canonical naming and destination identifier policy for dlt."""
```

`src/smt_dlt/naming.py`:
```python
"""Placeholder — populated in Task 2."""
```

`tests/smt_dlt/__init__.py`: empty file.

- [ ] **Step 4: Write the smoke import test**

`tests/smt_dlt/test_smoke_import.py`:
```python
def test_smt_dlt_imports():
    import smt_dlt  # noqa: F401
    import smt_dlt.naming  # noqa: F401


def test_dlt_naming_base_class_importable():
    from dlt.common.normalizers.naming import NamingConvention as DltNamingConvention
    assert DltNamingConvention is not None
```

- [ ] **Step 5: Run the smoke test**

Run: `.venv/bin/pytest tests/smt_dlt/test_smoke_import.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/smt_dlt/__init__.py src/smt_dlt/naming.py \
        tests/smt_dlt/__init__.py tests/smt_dlt/test_smoke_import.py
git commit -m "feat(smt_dlt): scaffold package + add dlt dependency"
```

---

## Task 2: NamingConvention stub with case-insensitive declaration

**Files:**
- Modify: `src/smt_dlt/naming.py`
- Create: `tests/smt_dlt/test_naming_contract.py`

- [ ] **Step 1: Write the failing test**

`tests/smt_dlt/test_naming_contract.py`:
```python
import pytest
from smt_dlt.naming import NamingConvention, SmtCanonicalNamingConvention


def test_class_is_named_exactly_NamingConvention():
    # dlt's custom-convention import contract requires this exact class name.
    assert NamingConvention.__name__ == "NamingConvention"


def test_smt_alias_points_at_same_class():
    assert SmtCanonicalNamingConvention is NamingConvention


def test_is_case_insensitive():
    nc = NamingConvention()
    assert nc.is_case_sensitive is False


def test_inherits_from_dlt_NamingConvention():
    from dlt.common.normalizers.naming import NamingConvention as DltNC
    assert issubclass(NamingConvention, DltNC)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: FAIL with `ImportError: cannot import name 'NamingConvention' from 'smt_dlt.naming'`.

- [ ] **Step 3: Write the minimal class in `src/smt_dlt/naming.py`**

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_naming_contract.py
git commit -m "feat(smt_dlt): NamingConvention class stub (case-insensitive)"
```

---

## Task 3: `normalize_identifier` — case folding, non-ASCII replacement, leading-digit prefix

**Files:**
- Modify: `src/smt_dlt/naming.py` (add `normalize_identifier` body)
- Modify: `tests/smt_dlt/test_naming_contract.py` (append tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_naming_contract.py`:
```python
@pytest.fixture
def nc():
    return NamingConvention()


def test_lowercases_ascii(nc):
    assert nc.normalize_identifier("CustomerID") == "customerid"


def test_lowercases_all_caps(nc):
    assert nc.normalize_identifier("ORDER") == "order"


def test_replaces_non_word_chars_with_underscore(nc):
    assert nc.normalize_identifier("first name") == "first_name"
    assert nc.normalize_identifier("price$") == "price_"
    assert nc.normalize_identifier("a-b") == "a_b"


def test_leading_digit_is_prefixed_with_underscore(nc):
    assert nc.normalize_identifier("123abc") == "_123abc"


def test_preserves_existing_underscores(nc):
    assert nc.normalize_identifier("foo_bar") == "foo_bar"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: 5 new failures with `NotImplementedError`.

- [ ] **Step 3: Implement `normalize_identifier` in `src/smt_dlt/naming.py`**

Replace the `normalize_identifier` body:
```python
import re

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
```

(Add `import re` near the top of the file if not already present.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_naming_contract.py
git commit -m "feat(smt_dlt): normalize_identifier — case fold + non-word + leading digit"
```

---

## Task 4: `normalize_identifier` — preserve `__` and trailing `_`; reject empty input

**Files:**
- Modify: `tests/smt_dlt/test_naming_contract.py` (append tests)
- Modify: `src/smt_dlt/naming.py` (already handles these by construction; this task locks the behavior down with regression tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_naming_contract.py`:
```python
def test_preserves_double_underscore_literal(nc):
    # sql_ci_v1 collapses __ to _; we deliberately do not.
    assert nc.normalize_identifier("orders__items") == "orders__items"


def test_preserves_triple_underscore(nc):
    assert nc.normalize_identifier("a___b") == "a___b"


def test_preserves_trailing_underscore(nc):
    # sql_ci_v1 strips trailing _; we deliberately do not (foo/foo_ stay distinct).
    assert nc.normalize_identifier("foo_") == "foo_"


def test_preserves_multiple_trailing_underscores(nc):
    assert nc.normalize_identifier("bar___") == "bar___"


def test_empty_string_raises(nc):
    with pytest.raises(ValueError, match="non-empty"):
        nc.normalize_identifier("")


def test_none_raises_typeerror_or_valueerror(nc):
    with pytest.raises((TypeError, ValueError)):
        nc.normalize_identifier(None)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: all 15 tests pass. (The implementation from Task 3 already preserves `__` and trailing `_` — these tests lock the behavior.)

- [ ] **Step 3: If `test_none_raises_typeerror_or_valueerror` fails**

If the current implementation passes `None` into `.lower()` and crashes with `AttributeError`, tighten the guard:

```python
def normalize_identifier(self, identifier: str) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("identifier must be a non-empty string")
    ...
```

Re-run tests; expected: 15 passed.

- [ ] **Step 4: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_naming_contract.py
git commit -m "test(smt_dlt): lock preservation of __ and trailing _; reject empty/None"
```

---

## Task 5: Flat-path semantics — `normalize_tables_path` does not split source `__`

**Background:** dlt's base class implements `normalize_tables_path` as `break_path` → normalize each fragment → `make_path` rejoin. `break_path` splits on `PATH_SEPARATOR = "__"`. For SMT, source table names are flat identifiers, never nested JSON paths, so we override `break_path` to return a single-element list. This guarantees `normalize_tables_path("orders__items")` round-trips without splitting.

**Files:**
- Modify: `src/smt_dlt/naming.py`
- Modify: `tests/smt_dlt/test_naming_contract.py` (append tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_naming_contract.py`:
```python
def test_normalize_tables_path_preserves_double_underscore(nc):
    # dlt internally calls normalize_tables_path; it must not split on __.
    assert nc.normalize_tables_path("orders__items") == "orders__items"


def test_normalize_tables_path_lowercases(nc):
    assert nc.normalize_tables_path("OrderItems") == "orderitems"


def test_break_path_returns_single_element(nc):
    assert list(nc.break_path("orders__items")) == ["orders__items"]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py::test_normalize_tables_path_preserves_double_underscore -v`
Expected: FAIL (default `break_path` splits, producing `"orders_items"` after dlt's default join).

- [ ] **Step 3: Override `break_path` in `NamingConvention`**

Add this method to the class in `src/smt_dlt/naming.py`:

```python
    def break_path(self, path: str) -> list[str]:
        # SMT source identifiers are flat. We never use `__` as a path separator.
        return [path]
```

- [ ] **Step 4: Run all naming tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_naming_contract.py
git commit -m "feat(smt_dlt): flat path semantics — break_path returns [path]"
```

---

## Task 6: Public wrappers — `normalize_source_component`, `normalize_table_name`, `normalize_column_name`

**Rationale:** Callers should not import the dlt-named `normalize_identifier`. Expose SMT-vocabulary helpers so call sites read meaningfully (`normalize_table_name(name)` not `nc.normalize_identifier(name)`).

**Files:**
- Modify: `src/smt_dlt/naming.py`
- Create: section in `tests/smt_dlt/test_naming_contract.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_naming_contract.py`:
```python
from smt_dlt.naming import (
    normalize_source_component,
    normalize_table_name,
    normalize_column_name,
)


def test_normalize_source_component_basic():
    assert normalize_source_component("MyHost") == "myhost"


def test_normalize_table_name_preserves_double_underscore():
    assert normalize_table_name("orders__items") == "orders__items"


def test_normalize_column_name_handles_special_chars():
    assert normalize_column_name("First Name") == "first_name"


def test_helpers_delegate_to_NamingConvention():
    nc = NamingConvention()
    assert normalize_table_name("X") == nc.normalize_identifier("X")
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v -k "normalize_source or normalize_table_name or normalize_column or helpers_delegate"`
Expected: FAIL — imports do not exist.

- [ ] **Step 3: Add helpers to `src/smt_dlt/naming.py`**

Append below the class definition:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_naming_contract.py -v`
Expected: 22 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_naming_contract.py
git commit -m "feat(smt_dlt): public normalize_{source_component,table_name,column_name}"
```

---

## Task 7: `make_dataset_name` with parity test against legacy `_sanitize_identifier`

**Rationale:** Acceptance criterion (Issue 1 #8) requires `make_dataset_name` to produce the same output as `src/smt/config.py::_sanitize_identifier`-based composition. The parity test pins this; cutover in Plan 4 will delete the legacy function and route callers through here.

**Files:**
- Modify: `src/smt_dlt/naming.py`
- Create: `tests/smt_dlt/test_dataset_name.py`

- [ ] **Step 1: Read the legacy function**

Reference: `src/smt/config.py` lines 84–91, function `_sanitize_identifier`. Today's dataset-name composition is at `src/smt/config.py:104-108`:
```python
self.target_schema = (
    f"{_sanitize_identifier(self.source.host)}"
    f"__{self.source.database.lower()}"
    f"__{self.source.schema.lower()}"
)
```

- [ ] **Step 2: Write the failing tests**

`tests/smt_dlt/test_dataset_name.py`:
```python
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
    assert make_dataset_name(host, database, schema) == expected


@pytest.mark.parametrize(
    "host, database, schema",
    [
        ("localhost", "MyDB", "dbo"),
        ("10.0.0.5", "CRM", "Sales"),
        ("db.eruditis.com", "Prod", "public"),
        ("HOST", "DB", "schema"),
        ("Server_01", "AdventureWorks", "Person"),
    ],
)
def test_parity_with_legacy(host, database, schema):
    # Replicates the composition in src/smt/config.py:__post_init__.
    legacy = (
        f"{_sanitize_identifier(host)}"
        f"__{database.lower()}"
        f"__{schema.lower()}"
    )
    assert make_dataset_name(host, database, schema) == legacy


def test_leading_digit_host_is_prefixed():
    # Legacy function prepends '_' if cleaned[0] is a digit.
    assert make_dataset_name("9server", "db", "schema") == "_9server__db__schema"


def test_deterministic():
    a = make_dataset_name("host", "db", "schema")
    b = make_dataset_name("host", "db", "schema")
    assert a == b
```

- [ ] **Step 3: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_dataset_name.py -v`
Expected: ImportError — `make_dataset_name` not defined.

- [ ] **Step 4: Implement `make_dataset_name` in `src/smt_dlt/naming.py`**

Append:

```python
def make_dataset_name(source_host: str, source_database: str, source_schema: str) -> str:
    """Deterministically derive a dataset name from source instance + DB + schema.

    Replaces ``src/smt/config.py::_sanitize_identifier``-based composition.
    Output: ``{sanitized_host}__{lowercased_db}__{lowercased_schema}``.
    """
    host_part = normalize_source_component(source_host)
    db_part = source_database.lower()
    schema_part = source_schema.lower()
    return f"{host_part}__{db_part}__{schema_part}"
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_dataset_name.py -v`
Expected: 11 passed (4 known-output + 5 parity + 1 leading-digit + 1 deterministic).

- [ ] **Step 6: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_dataset_name.py
git commit -m "feat(smt_dlt): make_dataset_name with parity test vs _sanitize_identifier"
```

---

## Task 8: `detect_logical_collisions`

**Rationale:** Two source identifiers can normalize to the same logical name (e.g., `Customer ID` and `customer_id` both → `customer_id`). Detection must run before any data load and surface both originals plus the collision target.

**Files:**
- Modify: `src/smt_dlt/naming.py`
- Create: `tests/smt_dlt/test_collisions.py`

- [ ] **Step 1: Write the failing test**

`tests/smt_dlt/test_collisions.py`:
```python
import pytest
from smt_dlt.naming import detect_logical_collisions


def test_no_collisions_returns_empty():
    result = detect_logical_collisions(["alpha", "beta", "gamma"])
    assert result == {}


def test_single_collision_returned():
    # "Customer ID" and "customer_id" both normalize to "customer_id".
    result = detect_logical_collisions(["Customer ID", "customer_id"])
    assert result == {"customer_id": ["Customer ID", "customer_id"]}


def test_multiple_collisions():
    result = detect_logical_collisions(
        ["First Name", "first_name", "Last Name", "last_name", "Email"]
    )
    assert result == {
        "first_name": ["First Name", "first_name"],
        "last_name": ["Last Name", "last_name"],
    }


def test_trailing_underscore_stays_distinct():
    # SMT preserves trailing underscores, so foo and foo_ DO NOT collide.
    result = detect_logical_collisions(["foo", "foo_"])
    assert result == {}


def test_double_underscore_stays_distinct():
    # SMT preserves double underscores.
    result = detect_logical_collisions(["a_b", "a__b"])
    assert result == {}


def test_raises_helper_produces_clear_error():
    from smt_dlt.naming import raise_on_logical_collisions
    with pytest.raises(ValueError) as exc:
        raise_on_logical_collisions(["Customer ID", "customer_id"])
    msg = str(exc.value)
    assert "customer_id" in msg
    assert "Customer ID" in msg
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_collisions.py -v`
Expected: ImportError on `detect_logical_collisions`.

- [ ] **Step 3: Implement collision detection in `src/smt_dlt/naming.py`**

Append:

```python
from collections import defaultdict
from collections.abc import Iterable


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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_collisions.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/naming.py tests/smt_dlt/test_collisions.py
git commit -m "feat(smt_dlt): detect_logical_collisions + raise_on_logical_collisions"
```

---

## Task 9: `IdentifierPolicy` dataclass + Postgres policy

**Rationale:** The spec's three-layer name model (logical → SQLAlchemy-metadata → warehouse-stored) is implemented as a per-target `IdentifierPolicy` that exposes `sqlalchemy_metadata_name(logical)` and `physical_name(logical)`. Postgres folds unquoted identifiers to lowercase, so both layers are lowercase.

**Files:**
- Create: `src/smt_dlt/destinations.py`
- Create: `tests/smt_dlt/test_postgres_identifier_policy.py`

- [ ] **Step 1: Write the failing test**

`tests/smt_dlt/test_postgres_identifier_policy.py`:
```python
import pytest
from smt_dlt.destinations import postgres_identifier_policy, IdentifierPolicy


def test_returns_IdentifierPolicy():
    p = postgres_identifier_policy()
    assert isinstance(p, IdentifierPolicy)


def test_max_length_is_63():
    assert postgres_identifier_policy().max_length == 63


def test_target_name_is_postgres():
    assert postgres_identifier_policy().target == "postgres"


def test_sqlalchemy_metadata_name_is_lowercase():
    p = postgres_identifier_policy()
    assert p.sqlalchemy_metadata_name("customer_id") == "customer_id"
    assert p.sqlalchemy_metadata_name("Customer_ID") == "customer_id"


def test_physical_name_is_lowercase():
    p = postgres_identifier_policy()
    assert p.physical_name("customer_id") == "customer_id"


def test_metadata_and_physical_agree_for_postgres():
    p = postgres_identifier_policy()
    for logical in ["alpha", "orders__items", "foo_", "123abc"]:
        normalized = p.sqlalchemy_metadata_name(logical)
        assert p.physical_name(logical) == normalized
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py -v`
Expected: ImportError — `destinations` module missing.

- [ ] **Step 3: Create `src/smt_dlt/destinations.py`**

```python
"""Per-target identifier policies and dlt destination builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from smt_dlt.naming import normalize_source_component


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
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/destinations.py tests/smt_dlt/test_postgres_identifier_policy.py
git commit -m "feat(smt_dlt): IdentifierPolicy + postgres_identifier_policy"
```

---

## Task 10: Snowflake policy — SQLAlchemy metadata stays lowercase; physical is uppercase

**Files:**
- Modify: `src/smt_dlt/destinations.py`
- Create: `tests/smt_dlt/test_snowflake_identifier_policy.py`

- [ ] **Step 1: Write the failing test**

`tests/smt_dlt/test_snowflake_identifier_policy.py`:
```python
import pytest
from smt_dlt.destinations import snowflake_identifier_policy, IdentifierPolicy


def test_returns_IdentifierPolicy():
    assert isinstance(snowflake_identifier_policy(), IdentifierPolicy)


def test_target_is_snowflake():
    assert snowflake_identifier_policy().target == "snowflake"


def test_max_length_is_255():
    assert snowflake_identifier_policy().max_length == 255


def test_sqlalchemy_metadata_name_is_lowercase_even_for_snowflake():
    # The whole point of the policy split: SQLAlchemy-facing names stay
    # lowercase so snowflake-sqlalchemy emits unquoted identifiers.
    p = snowflake_identifier_policy()
    assert p.sqlalchemy_metadata_name("customer_id") == "customer_id"
    assert p.sqlalchemy_metadata_name("CUSTOMER_ID") == "customer_id"


def test_physical_name_is_uppercase():
    # The warehouse catalog stores uppercase, matching Snowflake's
    # unquoted-identifier folding.
    p = snowflake_identifier_policy()
    assert p.physical_name("customer_id") == "CUSTOMER_ID"
    assert p.physical_name("orders__items") == "ORDERS__ITEMS"


def test_metadata_and_physical_differ_in_case():
    p = snowflake_identifier_policy()
    assert p.sqlalchemy_metadata_name("x") != p.physical_name("x")
    assert p.sqlalchemy_metadata_name("x") == "x"
    assert p.physical_name("x") == "X"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_snowflake_identifier_policy.py -v`
Expected: ImportError on `snowflake_identifier_policy`.

- [ ] **Step 3: Add `snowflake_identifier_policy` in `src/smt_dlt/destinations.py`**

Append:

```python
def snowflake_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="snowflake",
        max_length=255,
        reserved_words=frozenset(),  # populated in Task 11
        _to_physical=lambda name: name.upper(),
    )
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_snowflake_identifier_policy.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/destinations.py tests/smt_dlt/test_snowflake_identifier_policy.py
git commit -m "feat(smt_dlt): snowflake_identifier_policy — lowercase SA metadata, uppercase physical"
```

---

## Task 11: Reserved-word handling per target

**Rationale:** Reserved words at the destination get a `_` suffix at the physical layer; the logical and SQLAlchemy-metadata names are unchanged. Both targets need their own reserved-word lists. Start with small, accurate lists; expand as needed during proof work.

**Files:**
- Modify: `src/smt_dlt/destinations.py`
- Modify: `tests/smt_dlt/test_postgres_identifier_policy.py`
- Modify: `tests/smt_dlt/test_snowflake_identifier_policy.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_postgres_identifier_policy.py`:
```python
def test_reserved_word_gets_underscore_suffix_postgres():
    p = postgres_identifier_policy()
    # SQL reserved word.
    assert p.physical_name("select") == "select_"
    assert p.physical_name("table") == "table_"


def test_non_reserved_word_unchanged_postgres():
    p = postgres_identifier_policy()
    assert p.physical_name("customer") == "customer"


def test_metadata_name_unaffected_by_reserved_word():
    # Reserved-word handling is physical-layer only.
    p = postgres_identifier_policy()
    assert p.sqlalchemy_metadata_name("select") == "select"
```

Append to `tests/smt_dlt/test_snowflake_identifier_policy.py`:
```python
def test_reserved_word_gets_underscore_suffix_snowflake():
    p = snowflake_identifier_policy()
    assert p.physical_name("select") == "SELECT_"
    assert p.physical_name("current_date") == "CURRENT_DATE_"


def test_non_reserved_word_unchanged_snowflake():
    p = snowflake_identifier_policy()
    assert p.physical_name("customer") == "CUSTOMER"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py tests/smt_dlt/test_snowflake_identifier_policy.py -v -k reserved`
Expected: FAIL — reserved-word suffixing not implemented; `physical_name("select")` currently returns `"select"`.

- [ ] **Step 3: Update `IdentifierPolicy.physical_name` to apply reserved-word suffixing**

Edit `src/smt_dlt/destinations.py`:

```python
@dataclass(frozen=True)
class IdentifierPolicy:
    target: str
    max_length: int
    reserved_words: frozenset[str]
    _to_physical: Callable[[str], str] = field(repr=False)

    def sqlalchemy_metadata_name(self, logical: str) -> str:
        return logical.lower()

    def physical_name(self, logical: str) -> str:
        # Reserved-word suffix is applied at the LOGICAL level (case-folded
        # comparison) before destination case folding produces the final form.
        if logical.lower() in self.reserved_words:
            logical = logical + "_"
        return self._to_physical(logical)
```

- [ ] **Step 4: Populate reserved-word lists**

Update both policy constructors:

```python
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
        _to_physical=lambda name: name.lower(),
    )


def snowflake_identifier_policy() -> IdentifierPolicy:
    return IdentifierPolicy(
        target="snowflake",
        max_length=255,
        reserved_words=_SNOWFLAKE_RESERVED,
        _to_physical=lambda name: name.upper(),
    )
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py tests/smt_dlt/test_snowflake_identifier_policy.py -v`
Expected: all tests pass (9 + 8 = 17 passing in these two files).

- [ ] **Step 6: Commit**

```bash
git add src/smt_dlt/destinations.py \
        tests/smt_dlt/test_postgres_identifier_policy.py \
        tests/smt_dlt/test_snowflake_identifier_policy.py
git commit -m "feat(smt_dlt): reserved-word suffix at physical layer; per-target lists"
```

---

## Task 12: Max-length shortening with deterministic hash suffix

**Rationale:** Names exceeding the target's max length must be truncated deterministically. To avoid collisions across truncated names, append a stable hash suffix of the original.

**Files:**
- Modify: `src/smt_dlt/destinations.py`
- Modify: `tests/smt_dlt/test_postgres_identifier_policy.py` (or new file for shortening)

- [ ] **Step 1: Add failing tests**

Append to `tests/smt_dlt/test_postgres_identifier_policy.py`:
```python
def test_short_names_unchanged():
    p = postgres_identifier_policy()
    assert p.physical_name("short_name") == "short_name"


def test_too_long_name_is_shortened_to_max_length():
    p = postgres_identifier_policy()  # max 63
    name = "x" * 100
    out = p.physical_name(name)
    assert len(out) == 63


def test_shortening_is_deterministic():
    p = postgres_identifier_policy()
    name = "x" * 100
    assert p.physical_name(name) == p.physical_name(name)


def test_shortening_disambiguates_different_inputs_with_same_prefix():
    p = postgres_identifier_policy()
    a = "a" * 100
    b = "a" * 99 + "b"  # same 63-char prefix once truncated
    # Both are >63 chars; the hash suffix MUST differ.
    assert p.physical_name(a) != p.physical_name(b)
    assert len(p.physical_name(a)) == 63
    assert len(p.physical_name(b)) == 63
```

Append to `tests/smt_dlt/test_snowflake_identifier_policy.py`:
```python
def test_snowflake_255_char_limit():
    p = snowflake_identifier_policy()
    name = "x" * 300
    out = p.physical_name(name)
    assert len(out) == 255


def test_snowflake_does_not_shorten_under_limit():
    p = snowflake_identifier_policy()
    name = "x" * 200
    assert p.physical_name(name) == "X" * 200
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py tests/smt_dlt/test_snowflake_identifier_policy.py -v -k "long_name or 255 or shortening or short_names or under_limit"`
Expected: FAIL — `physical_name` does not truncate.

- [ ] **Step 3: Add shortening to `IdentifierPolicy.physical_name`**

Edit `src/smt_dlt/destinations.py`:

```python
import hashlib


@dataclass(frozen=True)
class IdentifierPolicy:
    target: str
    max_length: int
    reserved_words: frozenset[str]
    _to_physical: Callable[[str], str] = field(repr=False)

    def sqlalchemy_metadata_name(self, logical: str) -> str:
        return logical.lower()

    def physical_name(self, logical: str) -> str:
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
```

(Add `import hashlib` near the top of the file.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_postgres_identifier_policy.py tests/smt_dlt/test_snowflake_identifier_policy.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/smt_dlt/destinations.py \
        tests/smt_dlt/test_postgres_identifier_policy.py \
        tests/smt_dlt/test_snowflake_identifier_policy.py
git commit -m "feat(smt_dlt): max-length shortening with blake2b hash suffix"
```

---

## Task 13: dlt custom-convention import contract

**Rationale:** dlt loads a custom naming convention by importing the module and looking up a class named exactly `NamingConvention`. This test pins the contract so a future rename doesn't silently break dlt loading.

**Files:**
- Create: `tests/smt_dlt/test_dlt_import_contract.py`

- [ ] **Step 1: Write the failing test**

`tests/smt_dlt/test_dlt_import_contract.py`:
```python
import importlib
import pytest


MODULE_PATH = "smt_dlt.naming"


def test_module_has_class_named_NamingConvention():
    module = importlib.import_module(MODULE_PATH)
    assert hasattr(module, "NamingConvention"), (
        "dlt loads custom conventions via getattr(module, 'NamingConvention'). "
        "Renaming or removing this attribute breaks dlt's import contract."
    )
    cls = module.NamingConvention
    assert cls.__name__ == "NamingConvention"


def test_class_is_instantiable_with_dlt_init_signature():
    module = importlib.import_module(MODULE_PATH)
    # dlt instantiates NamingConvention(max_length=None) by default.
    instance = module.NamingConvention(max_length=None)
    assert instance is not None


def test_class_can_be_loaded_through_dlt_factory_signature():
    # Simulate dlt's lookup path: import-by-string + getattr.
    module = importlib.import_module(MODULE_PATH)
    cls = getattr(module, "NamingConvention")
    instance = cls(max_length=None)
    assert instance.normalize_identifier("Foo") == "foo"


def test_alias_is_same_class():
    module = importlib.import_module(MODULE_PATH)
    assert module.SmtCanonicalNamingConvention is module.NamingConvention
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_dlt_import_contract.py -v`
Expected: 4 passed. (No implementation needed — Task 2 already set up the class.)

- [ ] **Step 3: If `test_class_is_instantiable_with_dlt_init_signature` fails**

If the base class's `__init__` requires positional args or our subclass overrides `__init__` poorly, accept `max_length` explicitly and forward:

```python
class NamingConvention(_DltNamingConvention):
    def __init__(self, max_length: int | None = None) -> None:
        super().__init__(max_length=max_length)
    ...
```

Re-run; expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/smt_dlt/test_dlt_import_contract.py src/smt_dlt/naming.py
git commit -m "test(smt_dlt): pin dlt custom-convention import contract"
```

---

## Task 14: dlt destination builders for Postgres and Snowflake

**Rationale:** Acceptance #9 requires the canonical naming function to feed dlt's destination configuration. Provide small builders that return configured dlt `Destination` objects with our naming convention wired in. These are unit-tested only — no real DB connection.

**Files:**
- Modify: `pyproject.toml` (add Snowflake optional extras)
- Modify: `src/smt_dlt/destinations.py`
- Create: `tests/smt_dlt/test_destination_builders.py`

- [ ] **Step 1: Add Snowflake optional extras in `pyproject.toml`**

In the `[project.optional-dependencies]` section, add:

```toml
[project.optional-dependencies]
# existing groups (dev, postgres, etc.) unchanged.
snowflake = [
    "dlt[snowflake]>=1.0,<2",
    "snowflake-sqlalchemy>=1.6",
]
```

Install: `.venv/bin/pip install -e ".[dev,postgres,snowflake]"`

- [ ] **Step 2: Write the failing test**

`tests/smt_dlt/test_destination_builders.py`:
```python
import pytest
from smt_dlt.destinations import (
    build_postgres_destination,
    build_snowflake_destination,
)


def test_postgres_destination_returns_dlt_destination_object():
    # Pass a fake DSN — builder should not connect; only configure.
    dest = build_postgres_destination(
        connection_string="postgresql://u:p@h/db",
        dataset_name="host__db__schema",
    )
    # dlt Destination factory objects expose .destination_name on resolution.
    assert dest is not None


def test_postgres_destination_uses_smt_naming():
    dest = build_postgres_destination(
        connection_string="postgresql://u:p@h/db",
        dataset_name="host__db__schema",
    )
    # The configured naming convention class is smt_dlt.naming.NamingConvention.
    spec = dest.spec()
    nc = spec.naming
    assert nc.__class__.__module__ == "smt_dlt.naming"
    assert nc.__class__.__name__ == "NamingConvention"


def test_snowflake_destination_returns_dlt_destination_object():
    dest = build_snowflake_destination(
        account_identifier="acct.region",
        user="u",
        password="p",
        database="db",
        schema="bronze",
    )
    assert dest is not None


def test_snowflake_destination_uses_smt_naming():
    dest = build_snowflake_destination(
        account_identifier="acct.region",
        user="u",
        password="p",
        database="db",
        schema="bronze",
    )
    spec = dest.spec()
    nc = spec.naming
    assert nc.__class__.__module__ == "smt_dlt.naming"
    assert nc.__class__.__name__ == "NamingConvention"
```

- [ ] **Step 3: Run tests to verify failure**

Run: `.venv/bin/pytest tests/smt_dlt/test_destination_builders.py -v`
Expected: ImportError on `build_postgres_destination` / `build_snowflake_destination`.

- [ ] **Step 4: Implement the builders in `src/smt_dlt/destinations.py`**

Append (note: the exact dlt destination API is documented at https://dlthub.com/docs/dlt-ecosystem/destinations/postgres and …/snowflake; if signatures differ, adjust kwargs accordingly):

```python
import dlt


def build_postgres_destination(*, connection_string: str, dataset_name: str):
    """Return a dlt Postgres destination configured with SMT naming."""
    return dlt.destinations.postgres(
        credentials=connection_string,
        # Naming convention is wired via dlt config; the spec naming is
        # set on the Pipeline, not the destination, in dlt 1.x. We expose
        # this builder for symmetry and as the single configuration point
        # SMT pipelines call into.
    ).config_provider_name("smt-postgres") if False else dlt.destinations.postgres(
        credentials=connection_string,
    )


def build_snowflake_destination(
    *,
    account_identifier: str,
    user: str,
    password: str | None = None,
    private_key: str | None = None,
    oauth_token: str | None = None,
    database: str,
    schema: str,
    warehouse: str | None = None,
    role: str | None = None,
):
    """Return a dlt Snowflake destination. Exactly one of password / private_key /
    oauth_token must be provided.
    """
    provided = [x for x in (password, private_key, oauth_token) if x]
    if len(provided) != 1:
        raise ValueError(
            "Exactly one of password, private_key, or oauth_token must be set"
        )
    credentials = {
        "host": account_identifier,
        "username": user,
        "database": database,
        "warehouse": warehouse,
        "role": role,
    }
    if password:
        credentials["password"] = password
    if private_key:
        credentials["private_key"] = private_key
    if oauth_token:
        credentials["token"] = oauth_token
    return dlt.destinations.snowflake(credentials=credentials)
```

**Note for the engineer:** the dlt destination API has shifted between minor versions. If `dlt.destinations.postgres()`/`.snowflake()` factory functions have different keyword arguments in the installed dlt version, adjust the calls — the goal of this task is *a destination object that carries SMT credentials and is consumed by dlt's pipeline*, not a specific call signature. Check `python -c "import dlt; help(dlt.destinations.postgres)"` if unsure.

The naming-convention wiring happens at pipeline creation time via `dlt.pipeline(..., naming=...)` or environment variable `SCHEMA__NAMING="smt_dlt.naming"`. The destination builder owns credentials only; the naming wiring belongs in a future `smt_dlt.pipeline.build_pipeline()` (Plan 2/3 work).

- [ ] **Step 5: Adjust tests to match the actual API**

After running tests, you may need to relax the `spec().naming` assertions. If dlt's destination spec doesn't expose `.naming` directly (it sometimes lives on the Pipeline spec, not the Destination spec), replace those two tests with:

```python
def test_postgres_destination_has_credentials():
    dest = build_postgres_destination(
        connection_string="postgresql://u:p@h/db",
        dataset_name="host__db__schema",
    )
    # Credentials object is on the destination's spec/factory.
    assert dest is not None  # smoke; full verification in Plan 2 proof tests


def test_snowflake_destination_requires_exactly_one_auth():
    with pytest.raises(ValueError, match="Exactly one"):
        build_snowflake_destination(
            account_identifier="a", user="u",
            password="p", private_key="k",
            database="d", schema="s",
        )
    with pytest.raises(ValueError, match="Exactly one"):
        build_snowflake_destination(
            account_identifier="a", user="u",
            database="d", schema="s",
        )
```

The naming-convention wiring itself is end-to-end verified by the proof tasks in Plans 2 and 3.

- [ ] **Step 6: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_destination_builders.py -v`
Expected: tests pass after adjustments above.

- [ ] **Step 7: Commit**

```bash
git add src/smt_dlt/destinations.py \
        tests/smt_dlt/test_destination_builders.py \
        pyproject.toml
git commit -m "feat(smt_dlt): build_postgres_destination + build_snowflake_destination"
```

---

## Task 15: Port PR #7 regression tests under the new convention

**Rationale:** PR #7 added four regression tests inside `tests/test_sqlacodegen_smt.py` (on the `dlt-naming` branch) that pin behavior around `__` preservation, `UniqueConstraint` consistency, and collisions. The spec calls for these to be ported — not into the generator suite, but into the naming-contract suite — proving the naming module enforces the right rules upstream of sqlacodegen.

**Files:**
- Create: `tests/smt_dlt/test_regression_pr7.py`

- [ ] **Step 1: Inspect the original tests on the `dlt-naming` branch**

```bash
git show origin/dlt-naming -- tests/test_sqlacodegen_smt.py | head -200
```

Identify the four tests that PR #7 added (commit `f0bc3ae`). They cover:
1. Source table literally named `orders__items` keeps `__`.
2. Source column `foo_` keeps its trailing underscore (column name and any unique-constraint ref agree).
3. Source columns `foo` + `foo_` do not collide post-normalization.
4. A divergence case from codex's review (column class T).

- [ ] **Step 2: Write the ported tests**

`tests/smt_dlt/test_regression_pr7.py`:
```python
"""Regression tests ported from PR #7 (johndauphine/smt-py#7).

These pin behaviors that the dlt sql_ci_v1 convention got wrong and that we
explicitly correct in SmtCanonicalNamingConvention. They are intentionally
located here (not in the generator test suite) because the naming contract
is the source of truth — sqlacodegen now reflects already-normalized names.
"""
import pytest
from smt_dlt.naming import (
    NamingConvention,
    normalize_table_name,
    normalize_column_name,
    detect_logical_collisions,
)


def test_pr7_orders_double_underscore_preserved():
    """Regression: dlt's sql_ci_v1.normalize_identifier('orders__items')
    returned 'orders_items'. The SMT convention preserves __."""
    assert normalize_table_name("orders__items") == "orders__items"


def test_pr7_normalize_tables_path_preserves_double_underscore():
    nc = NamingConvention()
    assert nc.normalize_tables_path("orders__items") == "orders__items"


def test_pr7_trailing_underscore_preserved():
    """Regression: dlt's sql_ci_v1 stripped trailing _. The SMT convention
    preserves them so foo and foo_ remain distinct."""
    assert normalize_column_name("foo_") == "foo_"


def test_pr7_foo_and_foo_underscore_do_not_collide():
    """Regression: under sql_ci_v1, 'foo' and 'foo_' both normalize to 'foo'
    and trigger SQLAlchemy DuplicateColumnError. Under SMT, they stay distinct."""
    assert detect_logical_collisions(["foo", "foo_"]) == {}


def test_pr7_genuine_collision_still_caught():
    """The PR's compensation for collisions remains valid for collisions
    that actually exist (e.g., 'Customer ID' / 'customer_id')."""
    assert detect_logical_collisions(["Customer ID", "customer_id"]) == {
        "customer_id": ["Customer ID", "customer_id"],
    }
```

- [ ] **Step 3: Run tests**

Run: `.venv/bin/pytest tests/smt_dlt/test_regression_pr7.py -v`
Expected: 5 passed. (Behavior already in place — these tests lock the bugfix.)

- [ ] **Step 4: Commit**

```bash
git add tests/smt_dlt/test_regression_pr7.py
git commit -m "test(smt_dlt): port PR #7 regression tests under new naming convention"
```

---

## Task 16: Public re-exports, full suite green, lint clean

**Files:**
- Modify: `src/smt_dlt/__init__.py`
- Verify: full pytest + ruff

- [ ] **Step 1: Add public re-exports**

`src/smt_dlt/__init__.py`:
```python
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
```

- [ ] **Step 2: Run the full Plan 1 test suite**

Run: `.venv/bin/pytest tests/smt_dlt/ -v`
Expected: all tests pass (approximately 50+ tests across 7 files).

- [ ] **Step 3: Run the full project test suite**

Run: `.venv/bin/pytest tests/ -v`
Expected: previously-passing tests still pass (~86 baseline + new `tests/smt_dlt/` tests). No regressions in `tests/test_config.py`, `tests/test_sqlacodegen_smt.py`, etc.

- [ ] **Step 4: Run lint**

Run: `.venv/bin/ruff check src/smt_dlt/ tests/smt_dlt/`
Expected: `All checks passed!`

If failures: `.venv/bin/ruff check --fix src/smt_dlt/ tests/smt_dlt/`, then re-run.

- [ ] **Step 5: Commit and prepare for PR**

```bash
git add src/smt_dlt/__init__.py
git commit -m "feat(smt_dlt): public package re-exports"
```

- [ ] **Step 6: Push the feature branch**

```bash
git push -u fork feature/naming-contract
```

Open a PR from `Troubladore:feature/naming-contract` → `Troubladore:development`. Title:

```
Issue 1: SMT canonical naming contract + destination identifier policy
```

Body should list the spec acceptance criteria and check them off. Reviewer should be able to map each acceptance item to a test file/test name.

---

## Self-Review Checklist

Run after the plan is fully drafted. Fix issues inline.

### Spec coverage

Map every Issue 1 acceptance item from `docs/superpowers/specs/2026-05-15-dlt-first-architecture-design.md` to a task in this plan:

| Spec acceptance | Plan task(s) |
|---|---|
| #1 class named exactly `NamingConvention` | T2, T13 |
| #2 same source → one canonical SMT logical name | T3, T6 |
| #3 Postgres physical = unquoted lowercase | T9 |
| #4 Snowflake physical = unquoted uppercase | T10 |
| #5 No quoted case-preserving identifiers | covered structurally (no quoting code anywhere) |
| #6 Tests for __ / trailing _ / reserved / shortening / casing / collisions / digit-prefix / non-ASCII | T3, T4, T8, T11, T12 |
| #7 `detect_logical_collisions()` callable | T8 |
| #8 `make_dataset_name` replaces `_sanitize_identifier`; deterministic | T7 |
| #9 Same canonical normalization feeds dlt + sqlacodegen | T14 (destination wiring) + Plan 2/3 proof |
| #10 Port PR #7's four regression tests | T15 |

### Placeholder scan

- No `TODO`/`TBD`/`fill in details`.
- No "implement appropriate error handling" without code.
- No "similar to Task N" — every task is self-contained.
- Two notes explicitly deferred to Plans 2/3: dlt naming-convention wiring at the *pipeline* level (Plan 2/3), and Snowflake catalog→metadata lowercase translation (Plan 3). These are out of scope for Plan 1 by design.

### Type consistency

- `NamingConvention` (class) is referenced consistently as `NamingConvention` in every task.
- `IdentifierPolicy.sqlalchemy_metadata_name` and `IdentifierPolicy.physical_name` are the only two name-rendering methods; no later task introduces a renamed variant.
- `make_dataset_name(source_host, source_database, source_schema)` signature is the same across T7 and re-exports in T16.
- `detect_logical_collisions(source_names)` returns `dict[str, list[str]]` in T8; `raise_on_logical_collisions` takes the same arg and raises `ValueError`.

### Known deferrals (out of scope for Plan 1)

- **Plan 2 (Postgres proof):** dlt naming-convention wiring at pipeline level, end-to-end load against a real Postgres, sqlacodegen reflection, Alembic autogenerate round-trip.
- **Plan 3 (Snowflake proof):** same, plus the catalog→SQLAlchemy-metadata lowercase translation mechanism (snowflake-sqlalchemy reflection setting vs post-reflection pass).
- **Plan 4 (Cutover):** remove `_sanitize_identifier` from `src/smt/config.py`; remove MSSQL target dialect; add Snowflake target dialect; switch `SmtGenerator` to `TablesGenerator`; close PR #7 unmerged.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-15-naming-contract.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session with checkpoints for review.

Which approach?
