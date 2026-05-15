# DLT-first local development with sqlacodegen/Alembic promotion

**Status:** Draft, pending review
**Date:** 2026-05-15
**Supersedes:** the in-flight approach in PR #7 (https://github.com/johndauphine/smt-py/pull/7), which routes identifier normalization through `dlt.sql_ci_v1` inside `SmtGenerator`.

## Background

SMT today reflects a source database and uses sqlacodegen + Alembic to materialize a normalized target schema. PR #7 routed `SmtGenerator`'s identifier normalization through dlt's `sql_ci_v1.NamingConvention.normalize_tables_path`. The PR found real regressions (`__` segments collapsing, trailing-underscore stripping desyncing `UniqueConstraint` refs from column names, post-normalization collisions) and worked around each one with custom code inside `SmtGenerator`. That work surfaced that identifier rules belong **below** sqlacodegen, not inside it.

This spec defines the target architecture: DLT owns local-dev schema creation, sqlacodegen + Alembic own promotion to shared environments, and a single canonical naming contract — not the dlt default — defines logical identity.

## Goals

1. **DLT owns local-dev schema.** Normalization, schema definition, and DDL application against a developer's local target database are all driven by dlt.
2. **Alembic owns promotion.** dev/int/qa/prod schemas are created and evolved by reviewed Alembic migrations generated from sqlacodegen output that reflects the proven local target.
3. **One canonical naming contract.** A single SMT case-insensitive naming convention defines logical identity; physical identifier rendering is destination-native (unquoted lowercase on Postgres, unquoted uppercase on Snowflake).
4. **Drop MSSQL as a target.** SQL Server is supported as a source only. The two supported targets are Postgres and Snowflake.
5. **Reduce `SmtGenerator`.** Remove identifier-normalization responsibility from `SmtGenerator` once the local target already holds canonical names.

## Non-goals

- Replacing the source-DB extraction pattern. Source databases (SQL Server, Postgres, and other tech accessible via dlt sources) remain primary for extraction and discovery.
- Upstreaming the SMT naming convention to dlt in the first cut. Upstreaming may follow once the local contract is proven.
- Per-environment dlt schema mutation in shared environments. In dev/int/qa/prod, dlt runs as a loader against an Alembic-created schema, with schema contracts set to fail on drift.
- Always-quoted, case-preserving identifiers. Postgres and Snowflake each receive unquoted identifiers in their natural case-folding direction.
- Two independently evolving naming systems (one per target). Logical identity is single-sourced.

## Architecture

### End-to-end data flow

```
source systems
  (SQL Server / Postgres / APIs / Parquet / Events / others via dlt sources)
        |
        v
dlt resources
  + SMT canonical naming contract
  + dlt schema contracts
        |
        v
local proof target
  (developer's Postgres OR Snowflake instance, dlt-created and -evolved)
        |
        v
sqlacodegen reflects the local target schema
        |
        v
Alembic autogenerate produces a migration
        |
        v
shared environments (dev / int / qa / prod)
  - `alembic upgrade head` creates or evolves the schema
  - dlt runs as a loader; schema_contract={"tables":"freeze","columns":"freeze","data_type":"freeze"}
```

### Naming contract

A single `SmtCanonicalNamingConvention` defines case-insensitive logical identity. The destination layer renders physically:

| Object | Logical (canonical) | Postgres physical | Snowflake physical |
|---|---|---|---|
| Column `CustomerID` | `customer_id` | `customer_id` (unquoted) | `CUSTOMER_ID` (unquoted) |
| Table `Order__Items` | `order__items` | `order__items` | `ORDER__ITEMS` |
| Schema name from `host__db__schema` derivation | `sales_db1__crm__dbo` | `sales_db1__crm__dbo` | `SALES_DB1__CRM__DBO` |

Invariants:

1. **Single logical identity.** Same source object → same SMT logical name, regardless of target.
2. **Destination-native physical rendering.** Case-insensitive convention so dlt emits unquoted identifiers in each destination's native folding direction. Never quoted-lowercase Snowflake; never always-quoted case-preserving.
3. **Double underscores preserved.** A source column literally named `orders__items` keeps the `__`. (This is why `sql_ci_v1.normalize_identifier` is wrong; `normalize_tables_path` is closer but conflates path separation with literal `__`.)
4. **Trailing underscores: preserved.** Source identifier `foo_` maps to logical `foo_`, not `foo`. This is the call we are making to avoid the collision class entirely.
5. **Reserved-word handling.** Per-target; applied at the physical rendering layer. Reserved word at destination → append `_`. The logical name is unchanged. The mapping from logical to physical (including reserved-word suffixing and any max-length shortening) is recorded and made available to dlt, sqlacodegen, and Alembic. Tests assert both the canonical logical name and the final target physical name. (Snowflake unquoted identifiers are restricted to letters / digits / underscores / `$`, max 255 chars; Postgres unquoted identifiers fold to lowercase, max 63 chars.)
6. **Max-length shortening.** Target-aware. Postgres 63; Snowflake 255. Shortening happens at the physical layer with a deterministic hash suffix for collision avoidance.
7. **Collision detection.** Runs at the logical layer before any data loads. If two source identifiers map to the same logical name, the load fails with a clear error naming both originals and the collision target.
8. **Non-ASCII / digit-prefixed / special chars.** Non-`[a-z0-9_]` characters replaced with `_`; leading digit prefixed with `_` to produce a valid SQL identifier. This logic is shared by table/column normalization and schema-name derivation (replaces today's `_sanitize_identifier`).

### Generated artifact shape: Core `Table` metadata over Declarative ORM

Bronze schemas are generated as SQLAlchemy Core `Table` metadata, not Declarative ORM classes. sqlacodegen ships a `TablesGenerator` for exactly this. `SmtGenerator` switches its base class from `DeclarativeGenerator` to `TablesGenerator` as part of Issue 4. Rationale: Bronze is a movement layer, not an application persistence layer — there is no ORM consumer that benefits from declarative classes, and Core metadata is more honest about what is being modeled (a set of named tables and columns). Switching also retires two `SmtGenerator` overrides that exist only because of Declarative semantics: Python keyword escaping for attribute names, and the empty `generate_relationships()` override.

### Module layout

```
src/smt_dlt/
  __init__.py
  naming.py        Defines `class NamingConvention(dlt's NamingConvention)`.
                   dlt loads custom conventions by importing the module and
                   looking for a class named exactly `NamingConvention`.
                   Exposed in this codebase as
                   `SmtCanonicalNamingConvention = NamingConvention` for clarity.
                   Also: normalize_source_component(), normalize_table_name(),
                   normalize_column_name(), make_dataset_name(),
                   detect_logical_collisions().
  destinations.py  build_postgres_destination(), build_snowflake_destination(),
                   destination_identifier_policy()
  pipeline.py      build_pipeline() — wires naming convention + dataset_name + destination

src/sqlacodegen_smt/
  generator.py     SmtGenerator: keep MSSQL source-type fallback, Identity(),
                   keyword escaping, multi-file output, file headers,
                   no-relationships, collation stripping.
                   DROP: all DB identifier normalization, _check_db_name_collisions,
                   custom UniqueConstraint render branch.

src/smt/
  config.py        DROP _sanitize_identifier (delegate to smt_dlt.naming).
                   DROP MSSQL target dialect support.
                   ADD Snowflake target dialect support.
  database.py      DROP MSSQL target DDL paths.
                   ADD Snowflake target DDL paths.
  pipeline.py      Add a DLT-driven local-creation step before sqlacodegen reflection.
                   (Exact API surface in implementation plan.)
  migration.py     Unchanged interface; will need target-aware alembic.ini.

src/smt/generated/postgres/
  metadata.py      Generated SQLAlchemy Core `Table` metadata for Postgres
                   target; do not hand-edit.

src/smt/generated/snowflake/
  metadata.py      Generated SQLAlchemy Core `Table` metadata for Snowflake
                   target; do not hand-edit.

migrations/postgres/
  env.py           Loads src/smt/generated/postgres/metadata.py
  versions/

migrations/snowflake/
  env.py           Registers snowflake-sqlalchemy's `SnowflakeImpl`
                   (`__dialect__ = "snowflake"`) and loads
                   src/smt/generated/snowflake/metadata.py
  versions/

tests/
  smt_dlt/
    test_naming_contract.py            # in-memory; no DB
    test_postgres_identifier_policy.py # in-memory; no DB
    test_snowflake_identifier_policy.py# in-memory; no DB
  proof_postgres/                      # marker pytest -m proof_pg
  proof_snowflake/                     # marker pytest -m proof_sf
```

### `SmtGenerator` residual surface

`SmtGenerator` switches base class from sqlacodegen's `DeclarativeGenerator` to its `TablesGenerator` (see "Generated artifact shape" above). After the cut, `SmtGenerator` keeps:

- Multi-file output (one file per table).
- File headers with provenance metadata.
- MSSQL **source** type fallback (`_MSSQL_TYPE_OVERRIDES`) — SQL Server is still a source; its reflected types must map to portable SQLAlchemy types.
- `Identity()` rendering for autoincrement PKs — **retained only for legacy / source-reflection compatibility until Issues 2/3 confirm whether dlt-created target schemas still require it.** Bronze target tables should not generate replacement identities for source identity columns unless explicitly designed.
- Collation stripping from reflected types.

Removed by the base-class switch (no longer applicable under `TablesGenerator`):

- Python keyword escaping for attribute names — Core `Table` uses string names, not Python identifiers.
- The empty `generate_relationships()` override — Core metadata has no relationship concept.

Removed because responsibility moves to `smt_dlt.naming` or vanishes:

- All `.lower()` and `_normalize()` calls on identifiers in `render_class_variables`, `render_constraint`, `render_column_attribute`. The local target's identifiers are already canonical, so reflection sees the final names verbatim.
- `_check_db_name_collisions`. Collisions are caught upstream by `smt_dlt.naming.detect_logical_collisions` before any data loads. Reaching `SmtGenerator` implies collisions have already been resolved.
- Custom `UniqueConstraint` render branch. Falls back to `super().render_constraint()` because nothing in `SmtGenerator` is renaming columns anymore.

### Local vs. shared environment policy

| Concern | Local dev | Shared (dev/int/qa/prod) |
|---|---|---|
| Schema creation | dlt creates and evolves | `alembic upgrade head` |
| dlt schema contract | `evolve` (defaults) | `{"tables":"freeze","columns":"freeze","data_type":"freeze"}` (fail closed; no silent row or value discard as the default) |
| Source of DDL changes | iterative via dlt | reviewed PRs touching migration files |
| Failure mode for unexpected schema | dlt evolves the local target | dlt load fails with contract violation |
| `_dlt_*` metadata tables | created by dlt | created by dlt on first load (separate from app schema) |

**Alembic ownership boundary:** Alembic owns user Bronze schemas and tables. dlt may own its internal metadata and staging objects in an explicitly scoped operational schema or dataset. Alembic comparison filters must exclude those objects; grants must prevent dlt from altering user Bronze DDL in shared-env mode. A later issue may add a deliberate dead-letter / quarantine policy on top of the fail-closed contract; silent row discard is not the default for governed Bronze ingestion.

## Risks and mitigations

- **`sql_ci_v1` doesn't match SMT semantics.** dlt's `sql_ci_v1` collapses `__`, strips trailing `_`, and contracts repeated underscores. Mitigation: subclass `NamingConvention` directly and define our own rules; do not extend `sql_ci_v1`.
- **Snowflake hint enforcement.** Snowflake does not enforce PK/UNIQUE/FK. Models will declare them; runtime won't honor them. Mitigation: document explicitly; proof tests assert hint presence in migration files, not runtime enforcement.
- **Postgres proof does not prove Snowflake.** Different physical rendering, different types, different staging behavior, different reserved words. Mitigation: parallel proof issues with independent acceptance criteria.
- **PR #7 conflict.** PR #7 contains code this spec says to remove. Mitigation options:
  - (a) Close PR #7 unmerged; the work to replace `_normalize()` and the constraint workarounds is captured in Issue 4.
  - (b) Merge PR #7 as a regression-detector / interim fix, then Issue 4 removes the code it added.
  - The recommendation is **(a)** — merging code we plan to delete inflates the diff history and risks confusion. Reserve PR #7's regression tests (the four added test cases) — port them to `tests/smt_dlt/test_naming_contract.py` under the new convention.
- **dlt destination feature coverage for Snowflake.** Not all sqlacodegen-emitted constructs are supported the same way (e.g., `Identity()` → `AUTOINCREMENT`, `VARIANT` types, merge strategies). Issue 3 documents the coverage matrix.
- **Two paths to the same DDL must agree.** dlt-created local schema and alembic-from-sqlacodegen-promoted schema must be **catalog-equivalent under a normalized comparator** (excluding explicitly dlt-owned metadata/staging objects). Bit-identical DDL is too brittle — Snowflake reconstructs constraint DDL differently, and unnamed constraints can disappear from `GET_DDL`. Mitigation: Issues 2 and 3 both include an acceptance test that runs `alembic upgrade head` on a fresh DB and compares the catalog state against a dlt-only run using the normalized comparator.

## Implementation breakdown

Four GitHub issues; ordering and dependencies below.

### Issue 1 — Define SMT canonical naming + Postgres/Snowflake physical identifier contract

Acceptance:

1. `src/smt_dlt/naming.py` defines a class named exactly `NamingConvention` that subclasses `dlt.common.normalizers.naming.NamingConvention` (matching dlt's custom-convention import contract: dlt imports the module and looks up a class with that exact name). The module also exposes `SmtCanonicalNamingConvention = NamingConvention` for readability in the rest of the codebase.
2. Same source object → one canonical SMT logical name across both targets.
3. Postgres physical identifiers are unquoted lowercase.
4. Snowflake physical identifiers are unquoted uppercase.
5. No quoted case-preserving identifiers by default in either target.
6. Tests cover: double underscores preserved, trailing underscores preserved, reserved words at each target, max-length shortening (PG 63 / SF 255) with deterministic suffixing, source casing variants, post-normalization collision detection, digit-prefixed source names, non-ASCII characters.
7. `detect_logical_collisions()` callable independently and invoked before data load.
8. `make_dataset_name(source_instance, source_database, source_schema)` replaces `src/smt/config.py::_sanitize_identifier`. Identical inputs produce identical dataset names (deterministic across hosts).
9. The same canonical normalization feeds dlt `dataset_name` / resource / table / column naming **and** the sqlacodegen reflection path (i.e., it's the source-of-truth function for any identifier SMT writes to a database).
10. Port PR #7's four regression tests into the new test module under the new convention.

### Issue 2 — Prove Postgres target: schema, load, promotion

Acceptance:

1. dlt pipeline configured against a representative SQL Server source loads into a local Postgres target schema using the SMT naming convention.
2. dlt staging behavior (`_dlt_*` columns, load packages, staging dataset) documented in `docs/dlt-postgres.md`.
3. sqlacodegen reflects the dlt-created local Postgres schema; the generated `metadata.py` imports cleanly and exposes the `MetaData` object used by the Postgres Alembic `env.py`.
4. Alembic autogenerate against that same dlt-created schema produces no user-table operations.
5. `alembic upgrade head` against a fresh Postgres creates the user-table schema.
6. A second Alembic autogenerate against the upgraded Postgres produces no user-table operations.
7. The upgraded schema is catalog-equivalent (normalized comparator) to the dlt-created proof schema, excluding explicitly dlt-owned metadata/staging objects.
8. dlt run against the alembic-created schema with `schema_contract={"tables":"freeze","columns":"freeze","data_type":"freeze"}` succeeds when the source is unchanged; fails with a clear contract violation when a source column is added.

### Issue 3 — Prove Snowflake target: schema, load, promotion

Acceptance:

1. dlt pipeline configured against a representative SQL Server source loads into a local Snowflake target schema using the SMT naming convention.
2. Snowflake physical identifiers in the warehouse are unquoted uppercase (verifiable via `SHOW TABLES` / `INFORMATION_SCHEMA`).
3. Snowflake-specific type mappings exercised: `VARIANT`, `OBJECT`, `ARRAY`, `NUMBER(38,0)` for Identity-equivalents, `TIMESTAMP_TZ`, `BOOLEAN`.
4. dlt Snowflake destination load mechanics documented in `docs/dlt-snowflake.md`, covering: internal Snowflake stage usage, `PUT`, per-table built-in stages, `keep_staged_files` behavior, and merge / replace strategies.
5. Constraint enforcement boundary verified — Snowflake enforces `NOT NULL` and `CHECK` but does not enforce `PRIMARY KEY` / `UNIQUE` / `FK`. Migrations emit all of these. Tests assert presence in the migration file for all; tests assert runtime enforcement only for `NOT NULL` / `CHECK`.
6. sqlacodegen reflects the dlt-created local Snowflake schema; the generated `metadata.py` imports cleanly and exposes the `MetaData` object used by the Snowflake Alembic `env.py`.
7. The Snowflake Alembic `env.py` registers `snowflake-sqlalchemy`'s `SnowflakeImpl` (`__dialect__ = "snowflake"`) and uses the Snowflake generated metadata.
8. Alembic autogenerate against the dlt-created Snowflake schema produces no user-table operations.
9. `alembic upgrade head` against a fresh Snowflake creates the user-table schema.
10. A second Alembic autogenerate against the upgraded Snowflake produces no user-table operations.
11. The upgraded schema is catalog-equivalent (normalized comparator) to the dlt-created proof schema, excluding dlt-owned metadata/staging objects.
12. Tests assert that generated Snowflake migrations do not produce quoted lowercase identifiers.
13. dlt run against the alembic-created schema with `schema_contract={"tables":"freeze","columns":"freeze","data_type":"freeze"}` succeeds when the source is unchanged; fails on drift.

### Issue 4 — Repoint sqlacodegen promotion + remove MSSQL target + add Snowflake target

Acceptance:

1. `SmtGenerator` extends sqlacodegen's `TablesGenerator` instead of `DeclarativeGenerator`. Python-keyword-escaping logic and the `generate_relationships()` override are removed (not applicable to Core `Table` metadata).
2. `SmtGenerator` no longer normalizes DB identifiers. All `.lower()` / `_normalize()` calls on identifiers removed.
3. `_check_db_name_collisions` removed from `SmtGenerator`; collision detection lives in `smt_dlt.naming`.
4. Custom `UniqueConstraint` render branch removed; falls back to `super().render_constraint()`.
5. `src/smt/config.py::_sanitize_identifier` removed; callers use `smt_dlt.naming.make_dataset_name`.
6. MSSQL target dialect support removed: from `config.py` (validation, URL building, default driver/port), `database.py` (DDL dispatch, schema create/drop), and docs. SQL Server remains as a **source** only — `_MSSQL_TYPE_OVERRIDES` stays in `SmtGenerator`.
7. Snowflake target dialect added to `config.py` and `database.py`. `config.py`: dialect string `snowflake` (provided by the `snowflake-sqlalchemy` package); URL form `snowflake://{user}@{account_identifier}/{database}/{schema}` with auth-method-specific tail (`?warehouse=...&role=...` when set); no port field. Required field: `account_identifier`. Optional fields: `warehouse`, `role` (only needed when the Snowflake user has no configured defaults). Auth methods supported: password (`password` field), key-pair (private-key path or PEM string passed via `connect_args`), and OAuth (access token). `database.py`: DDL dispatch for Snowflake schema create/drop.
8. `tests/test_database.py`, `tests/test_config.py`, `tests/test_sqlacodegen_smt.py` updated for the new dialect set.
9. `docs/DESIGN.md`, `docs/TECH_SPEC.md`, `CLAUDE.md` updated to reflect the new architecture (Postgres + Snowflake targets; SQL Server source only; naming contract location; Core `Table` metadata over Declarative ORM).
10. PR #7 closed unmerged with a link to Issue 1 explaining where the work lands instead.

### Cross-issue testing strategy

- **Naming tests** live in `tests/smt_dlt/` and run without a database. CI lane: standard `pytest`.
- **Postgres proof tests** live in `tests/proof_postgres/` and require live credentials. CI lane: `pytest -m proof_pg`, gated on a `PG_PROOF_DSN` secret.
- **Snowflake proof tests** live in `tests/proof_snowflake/` and require live credentials. CI lane: `pytest -m proof_sf`, gated on `SNOWFLAKE_PROOF_*` secrets.
- Existing in-memory SQLite tests in `tests/test_sqlacodegen_smt.py` stay green throughout — `SmtGenerator`'s remaining surface still has unit-test coverage.

### Dependency graph and ordering

```
        Issue 1 (naming contract)
        /              \
       /                \
Issue 2 (PG proof)   Issue 3 (SF proof)
       \                /
        \              /
        Issue 4 (cut over + dialect swap)
```

- Issue 1 is the prerequisite for everything else.
- Issues 2 and 3 are independent and can run in parallel (different developers / different infrastructure).
- Issue 4 may begin as a branch after one of Issues 2/3 is green, but it must not merge until **both** Issue 2 and Issue 3 are green. Cutting over `SmtGenerator`, removing MSSQL-target support, and adding Snowflake-target support all land atomically with verified proof on both targets.
- Issue 4 lands the breaking change (MSSQL target removal, Snowflake target wiring, base-class switch to `TablesGenerator`). It is the only issue that bumps the major version.

## Open questions, deferred to implementation

- Exact dlt source(s) to use for the SQL Server source in proof tests. `dlt.sources.sql_database` is the obvious starting point; Issue 2 should justify if anything else is needed.
- Whether `smt_dlt.pipeline.build_pipeline()` lives in this repo or is replaced by direct dlt API calls from `smt/pipeline.py`. Decided during Issue 2.
- Concrete reserved-word lists per target. Pull from Postgres / Snowflake docs during Issue 1.
- Snowflake auth-method ergonomics in `smt.yaml` (password / key-pair / OAuth). Issue 3 should produce concrete YAML examples for each auth method.
- Whether the catalog-equivalence comparator used in Issues 2/3 acceptance lives in `tests/proof_postgres/` and `tests/proof_snowflake/` (per-target) or in a shared `tests/_catalog_compare/` helper. Decide in Issue 2.
