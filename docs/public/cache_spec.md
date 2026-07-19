# Persistent cache

pydocformatter uses a persistent cache by default for selected files on disk. The cache stores a strict proof that exact source bytes completed successfully without findings under the same analysis semantics. It never stores source text, formatted output, diagnostics, exceptions, or serialized Python objects.

A validated cache hit skips UTF-8 decoding, LibCST parsing, metadata preparation, rule execution, fix planning, and source generation. File discovery, settings resolution, rule selection, path-context construction, and a complete cryptographic source-content check still run. Caching is therefore most effective for clean files whose analysis is substantially more expensive than reading and hashing them.

## Configuration and commands

Caching and its location are controlled by run-level settings:

```toml
[tool.pydocfmt]
cache = true
cache-dir = ".pydocfmt_cache"
```

The corresponding command-line controls are:

```text
pydocfmt check --cache
pydocfmt check --no-cache
pydocfmt check --cache-dir PATH
pydocfmt check --cache-stats
pydocfmt clean
pydocfmt clean --cache-dir PATH
```

`cache` and `cache-dir` cannot be changed through `per-file-settings`. `--cache-stats` is a debugging flag, not a setting, and does not affect cache keys, normal diagnostics, or exit status. See the [Settings specification](settings_spec.md#persistent-clean-proof-cache) for configuration-source precedence and path-base rules.

The default `.pydocfmt_cache` location is relative to the directory containing the auto-discovered current-working-directory `pyproject.toml` with `[tool.pydocfmt]`. It is relative to the current working directory when no such configuration exists. An explicitly configured relative path follows the normal base for its configuration source.

pydocformatter may create the configured cache directory, but its immediate parent must already exist as a directory; it never creates missing ancestors. When enabled caching has selected disk files and that immediate parent is missing or is not a directory, the invocation runs uncached, counts one store error and every selected file as uncacheable, and emits exactly one warning before optional cache statistics. Findings, fixes, and exit status remain the same as an uncached run. Empty selections, standard-input checks, disabled caching, and valid parents do not emit this warning.

```text
pydocfmt check: Cache warning: Cache directory parent does not exist or is not a directory; running without persistent cache: <parent>
```

Use a dedicated cache directory rather than a project root, source directory, or directory containing unrelated data. pydocformatter may claim an empty untagged directory only when creating the cache. Lookup, persistence, quarantine, pruning, and cleanup require the exact ownership tag. File discovery specially prunes only the run root resolved from the current-working-directory profile, and only when that root is already owned or is empty and claimable while caching is enabled. Nested profiles do not select or prune additional cache stores. See [File selection](file_selection_spec.md#file-selection-algorithm) for the exact behavior.

## Positive-hit contract

A cache proof is accepted only when all of these identities match:

- the complete raw source bytes, checked with a domain-separated SHA-256 digest and byte length;
- every effective analysis-affecting setting value after matching per-file settings;
- the final ordered path-specific rule codes after selection and per-file ignores are resolved;
- the lexical project-relative path and resolved physical target;
- module and package parts, package-initializer status, and public/private path classification;
- the internal cache protocol, persistent schema, and analysis-key encoding versions;
- the installed pydocformatter distribution version and a complete implementation identity;
- the filelock and LibCST versions; and
- the Python implementation and bytecode cache tag, complete Python version, operating-system family, platform, architecture and linkage, byte order, and native line separator.

The analysis-setting identity deliberately includes every setting classified as a direct analysis value, even when the current selected rule subset does not read it. Run controls such as concurrency, cache enablement/location, and output format are excluded. File-discovery settings are excluded after the file has been selected. Raw selector expressions, selector source priority and specificity, configuration provenance, and the unapplied per-file settings map are excluded after they have produced the effective values and final ordered rule codes. Fixability is also excluded: it changes how dirty findings are labeled or repaired, but it cannot make a finding-free source state dirty. Equivalent changes to those excluded inputs reuse a proof only when the selected file, effective analysis values, and final ordered rule codes remain the same.

For a normal installed wheel, the implementation identity uses the trusted distribution manifest metadata for every `pydocformatter/**/*.py` entry only after the distribution's package root is verified as the physical root of the imported `pydocformatter` package. This prevents stale metadata from another installation from identifying the running code. The identity includes each normalized logical path, hash algorithm, encoded file hash, and file size; missing, mismatched, or ambiguous metadata rejects this fast path. The package version is obtained from the same distribution object. pydocformatter trusts matching installed distribution metadata as part of the local cache trust model and does not reopen every installed source file on each invocation.

Editable installs, source-tree execution, and unusable wheel manifests use a complete implementation-source digest instead. This digest follows valid symlinked package roots, Python files, and directories. It includes each logical Python path, the spelling and resolved identity of symlinks leading to it, and its complete target bytes. Distinct logical aliases remain distinct inputs. Broken relevant targets, unreadable source trees, non-regular Python sources, and directory-link cycles make the engine identity unavailable and therefore disable caching for that invocation rather than risking reuse under an incomplete identity.

Canonical cache values use explicit type tags, including distinct encodings for lists, tuples, mappings, data classes, paths, bytes, frozen sets, and finite floats. Non-finite floats are rejected, so structurally different analysis values cannot collide through an untagged representation.

File size and nanosecond modification time are negative-only hints. A mismatch rejects a candidate without a parent-side source read, but matching metadata never establishes a hit. pydocformatter always reads and hashes the complete current file before accepting a proof. A same-size edit with a preserved timestamp is therefore reanalyzed, while a timestamp-only touch is conservatively treated as a miss.

Adding or removing an ancestor `__init__.py` or `__init__.pyi` can change package and visibility semantics without changing the checked file. That context is computed once, fingerprinted, and passed to rule execution, so such a change also invalidates the proof.

Package-marker observations form an invocation-local request-preparation snapshot. The first observation of each resolved directory is reused for later siblings in the same preparation pass, including a missing-marker observation that stops a package chain. Marker changes completed before an invocation are observed, and changes between invocations change affected path-context keys. pydocformatter does not lock package markers or selected sources against concurrent mutation; reuse within one pass gives sibling contexts a consistent observation rather than sampling the same directory repeatedly.

The proof applies to the source snapshot that pydocformatter opened. As with an uncached run, another process can replace a path after that snapshot is read; the cache does not lock source files against concurrent writers.

## Population and mode reuse

Only a finding-free, error-free final state that exists on disk can populate the cache.

| Situation                                                     | Lookup           | Population                  |
|---------------------------------------------------------------|------------------|-----------------------------|
| Clean `check` input                                           | Yes              | Yes                         |
| Clean `--fix` input                                           | Yes              | Yes                         |
| Successfully fixed to a clean on-disk state                   | Miss and analyze | Yes, using post-write bytes |
| Clean `--diff` input                                          | Yes              | Yes                         |
| Check or diff would change source                             | Miss and analyze | No                          |
| Findings remain                                               | Miss and analyze | No                          |
| Parse, decode, rule, read, or write error                     | Miss and analyze | No                          |
| No selected rules and valid source                            | Yes              | Yes                         |
| No selected rules and invalid source                          | Miss and parse   | No                          |
| Rule-selection error                                          | No               | No                          |
| Any selected rule declares external or unmodeled dependencies | No               | No                          |
| Standard input                                                | No               | No                          |

A clean proof is safely reusable across check, fix, and diff modes because the proven source has nothing to diagnose, rewrite, or display as a diff. A hit during `--fix --exit-non-zero-on-fix` does not count as a current-invocation modification.

Worker processes analyze misses only. An all-hit run does not start the analysis process pool. One miss runs sequentially; multiple misses use a process pool sized from the miss count and the current invocation's configured `parallelism`. Parent-side source validation uses a bounded thread pool controlled by that same current value. Parallelism is excluded from proof identity, so reusing a proof never reuses the invocation that created it or its scheduling configuration.

## Storage and retention

The version-one layout is:

```text
<cache-dir>/
    CACHEDIR.TAG
    .gitignore
    .pydocfmt.lock
    v1/
        cache.sqlite3
        cache.sqlite3-wal
        cache.sqlite3-shm
```

The standard `CACHEDIR.TAG` must be a non-symlinked regular file with the exact pydocfmt ownership marker. Newly created cache directories use user-only permissions where supported. The retained `.pydocfmt.lock` is a native file lock coordinating database writes, recovery, quarantine, retention pruning, and cleanup across processes. Normal persistence waits only for the short store timeout and then falls back to uncached operation; cleanup waits up to five seconds before returning status `2`.

The SQLite database is opened read-only for lookup, closed before analysis workers start, and reopened in the parent only for one batched transaction after all results complete normally. After acquiring the mutation lock, every writer freshly validates the database currently at the live path. A stale earlier lookup can therefore never replace a newer compatible database. Concurrent invocations may replace the same proof, but every later hit still requires matching path context and source content.

Proofs not seen for 30 days and engine namespaces not seen for 30 days are pruned opportunistically at most once per UTC day. Hit retention is updated at most once per day, so repeated same-day warm runs with no new proofs perform no proof write. Retention timestamps follow the currently observed UTC day even when the wall clock moves backward; because cache data is disposable, this favors potentially earlier reanalysis over allowing a future timestamp to extend retention unnaturally.

`pydocfmt clean` resolves the configured location using the normal global configuration arguments and accepts `--cache-dir PATH` with normal command-line precedence. It verifies ownership and removes only numeric pydocfmt-owned version directories and known quarantine groups inside those version directories. Root-level files that merely resemble quarantine names are unrelated data and remain untouched. Cleanup deliberately retains the configured root, ownership tag, `.gitignore`, lock file, and unrelated children. A missing root is an idempotent success, while even an empty untagged root is refused because cleanup never claims ownership. Cleanup also refuses malformed or symlinked roots rather than risking deletion of user data. Filesystem failures produce a contextual command error and status `2` without a traceback. Cleanup stops at the first failure; paths removed earlier remain removed, and rerunning the command safely retries the remaining owned paths.

## Failures, portability, and trust

Persistent storage is a best-effort optimization. A missing database is an empty cache. Unsupported schemas, malformed rows, corruption, locks, read-only paths, permission failures, unavailable SQLite locking, disk-full conditions, and other storage failures degrade to uncached analysis without changing findings, source writes, or exit status. The missing-immediate-parent warning described above is the deliberate exception to otherwise silent cache fallback.

Only a database below a cache root with the exact ownership tag may be queried, quarantined, replaced, or mutated. Owned databases with supported SQLite corruption or non-database error codes may be moved to bounded quarantine names before a fresh database is created on a later clean write. Readable incompatible databases are checkpointed first. The main database, WAL, and shared-memory files are then moved as one recoverable quarantine group, using a common `cache.sqlite3.<kind>-<timestamp>-<pid>` base with `-wal` and `-shm` sidecars. Retention counts and removes whole groups, and a partial move is rolled back best-effort. Programming, binding, integrity, lock, permission, and similar operational errors do not trigger quarantine. When ownership cannot be proved, the database and its sidecars remain untouched and the invocation runs uncached.

Cache roots, version directories, and database leaves must not themselves be symlinks. This storage restriction is separate from implementation-source and selected-source fingerprinting, which support valid symlinks. Symlinks in ancestor workspace paths and selected source paths remain supported. SQLite write-ahead logging is preferred when available and falls back to the rollback journal when necessary.

Cache data is trusted local optimization state, not a security boundary. A process that can deliberately rewrite the database can forge a clean proof. Use `--no-cache` for cache artifacts restored from an untrusted source. CI caches are appropriate only when the cache provider and restore inputs are trusted.

The cache is portable across relocated copies of the same project when project-contained settings bases and paths retain equivalent relative identities. Changes in pydocformatter code, dependencies, Python, or platform create a different engine namespace rather than reusing incompatible proofs.

## Cache statistics

`pydocfmt check --cache-stats` writes one line to standard error with these counters:

| Counter             | Meaning                                                                                                    |
|---------------------|------------------------------------------------------------------------------------------------------------|
| `candidates`        | Selected disk files eligible for lookup                                                                    |
| `hits`              | Proofs accepted after full source validation                                                               |
| `metadata-rejected` | Stored candidates rejected by size or modification time                                                    |
| `digest-rejected`   | Metadata-compatible candidates rejected by full-content digest                                             |
| `misses`            | Cacheable files sent to normal analysis                                                                    |
| `uncacheable`       | Files bypassed because caching was disabled, the cache engine was unavailable, or policy did not permit it |
| `read-errors`       | Parent-side probe reads that fell back to normal analysis                                                  |
| `writes`            | Clean proofs submitted successfully in the batched store transaction                                       |
| `store-errors`      | Best-effort cache preparation or storage failures                                                          |

These counters are diagnostic only. Cache errors are intentionally absent from normal output except for the single missing-immediate-parent warning described above.

## Performance expectations

Warm caching avoids decoding, parsing, metadata preparation, rule execution, fix planning, and source generation for validated clean files, but it cannot avoid discovery, configuration, request fingerprinting, cache lookup, or complete source reads and hashing. Clean files with relatively expensive analysis generally benefit most. Fixed per-file cache work can dominate exceptionally cheap analysis, so the result depends on the workload, filesystem, cache state, configured parallelism, and host platform.

Measure representative workloads when cache performance is important. Use `cache = false` or `--no-cache` when measured results favor uncached analysis, or when diagnosing cache behavior. pydocformatter does not automatically enable or disable caching based on workload heuristics, and it makes no universal or cross-platform timing guarantee.
