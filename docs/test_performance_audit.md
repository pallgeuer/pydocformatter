# Test Performance Audit

Test inventory up-to-date commit: `1770d287742708de7f710f81535e37c316e8255e`

This plan is a ready-to-use tracking ledger for a future audit of the complete test set for unnecessarily or avoidably slow tests, fixtures, helpers, and testing approaches. The audit must combine performance evidence with code analysis and must not weaken any tests. If a speedup would reduce meaningful coverage, loosen an assertion, remove a regression case, hide a failure mode, or otherwise make the suite less protective, record it as out of scope unless the user explicitly approves a separate test-design change.

## Goal Command

Paste this command into Codex when you want the audit to start:

```text
/goal Audit the complete pydocformatter test set for unnecessarily or avoidably slow tests, fixtures, helpers, and testing approaches without weakening any tests. First update every inventory table in docs/test_performance_audit.md from the latest Git-tracked tests and test-support files, because tests may have been added, removed, renamed, or substantially changed since the test inventory up-to-date commit recorded at the top of the file. Also check whether src/pydocformatter/rules/definitions/**/*.py has changed since docs/rule_performance_audit.md was last updated, and record in docs/rule_performance_audit.md which rule categories or rules need to be rechecked before relying on that rule-performance audit. Then measure or otherwise characterize test performance, analyze the test code for coverage-preserving speedups, and maintain docs/test_performance_audit.md continuously as the source of truth. Do not implement fixes during the audit unless I explicitly ask for an implementation pass. Do not weaken tests: do not delete meaningful cases, relax assertions, skip tests, mark tests xfail, reduce fixture realism, narrow parametrization, or replace end-to-end coverage with narrower coverage unless the same behavior remains protected elsewhere and that equivalence is documented. The goal is complete only when every test file and every shared helper/fixture row in the plan has performance evidence, code-analysis notes, potential speedup classification, and any detailed findings or no-finding rationale recorded.
```

## Scope

- Audit every Git-tracked test file under `tests/`.
- Audit shared test fixtures and helpers, including `tests/conftest.py`, package-level helpers, and rule-specific helper modules.
- Audit test data generation, subprocess usage, filesystem usage, parser/formatter setup, parametrization size, repeated imports, and repeated full-suite or integration-style checks.
- Record all findings here before implementation.
- Keep coverage-preserving opportunities separate from possible test-design changes.
- Do not weaken any tests.

## Audit Commands

Record exact commands here when the audit is executed. Use `uv` for all Python execution and do not configure a custom uv cache.

| Purpose               | Command | Notes                                                                                   |
|-----------------------|---------|-----------------------------------------------------------------------------------------|
| Refresh inventory     | TBD     | First action of the audit; record exact commands used to regenerate the inventory rows. |
| Baseline full suite   | TBD     | Record wall time, CPU time if available, selected options, and working-tree state.      |
| Slowest tests         | TBD     | Record pytest timing options or plugins used, plus the slowest tests discovered.        |
| Focused test file     | TBD     | Record one row per focused test file or test group when focused timing is useful.       |
| Fixture/helper timing | TBD     | Record commands or instrumentation used to isolate shared setup costs.                  |
| Profiling             | TBD     | Record profiler, output path, and interpretation notes.                                 |
| Coverage guard        | TBD     | Record commands or reasoning used to prove no test coverage was weakened.               |
| Behavior guard        | TBD     | Record commands proving test outcomes remain equivalent after any later fix pass.       |

## Status Legend

- `Not started`: no audit work recorded yet.
- `Measuring`: timing or profiling is underway.
- `Analyzing`: test, fixture, or helper code is being inspected.
- `Done`: performance evidence and code-analysis notes are recorded.
- `Blocked`: progress needs user input or missing tooling.

## Potential Legend

- `None`: no credible coverage-preserving speedup found.
- `Low`: small or uncertain speedup, likely not worth immediate implementation.
- `Medium`: localized coverage-preserving speedup with measurable value.
- `High`: repeated or suite-wide cost with clear coverage-preserving mitigation.
- `Test-design decision`: possible speedup would alter coverage, assertion strength, or test semantics and needs explicit user approval.

## Test Inventory

Refresh this table before starting the audit.

| Test file                                                      | Area                | Status      | Performance evidence | Code-analysis notes | Potential | Findings |
|----------------------------------------------------------------|---------------------|-------------|----------------------|---------------------|-----------|----------|
| `tests/rules/PCF/test_PCF.py`                                  | Rule category       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PCF/test_PCF001.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PCF/test_PCF002.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PCF/test_PCF003.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PCF/test_PCF004.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF.py`                                  | Rule category       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF000.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF001.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF002.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF100.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF101.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF102.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF103.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF104.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF105.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF106.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF107.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF108.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF109.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF110.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF200.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF201.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF202.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF203.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF300.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF301.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF302.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF303.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF304.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF305.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF400.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF401.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF402.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF403.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF404.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF405.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF406.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF407.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF408.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF409.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF410.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF411.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF500.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF501.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF502.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF503.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF504.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF505.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF506.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PDF/test_PDF507.py`                               | Rule implementation | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_decorators.py`            | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_docstring_conventions.py` | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_docstring_sections.py`    | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_rest_fields.py`           | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_source_text.py`           | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_string_literals.py`       | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/definition_helpers/test_text_layout.py`           | Rule helper         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_cli_linter.py`                                     | CLI                 | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_cli_rule.py`                                       | CLI                 | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_cli_show_files.py`                                 | CLI                 | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_comments.py`                                       | Comments            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_file_selection.py`                                 | File selection      | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_formatter.py`                                      | Formatter           | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_formatting_rules_doc.py`                           | Documentation       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_glob_matcher.py`                                   | File selection      | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_markdown_tables.py`                                | Documentation       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_pydocfmt.py`                                       | Legacy formatter    | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_rule_categories.py`                                | Rule metadata       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_rule_edits.py`                                     | Rule edits          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_rule_markdown_examples.py`                         | Documentation       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_rules.py`                                          | Rule metadata       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_settings.py`                                       | Settings            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/test_utils.py`                                          | Utilities           | Not started | TBD                  | TBD                 | TBD       | TBD      |

## Helper And Fixture Inventory

Refresh this table before starting the audit.

| File                         | Area            | Status      | Performance evidence | Code-analysis notes | Potential | Findings |
|------------------------------|-----------------|-------------|----------------------|---------------------|-----------|----------|
| `tests/__init__.py`          | Test package    | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/conftest.py`          | Shared fixtures | Not started | TBD                  | TBD                 | TBD       | TBD      |
| `tests/rules/PCF/helpers.py` | Rule helper     | Not started | TBD                  | TBD                 | TBD       | TBD      |

## Testing-Approach Inventory

Use this table for cross-cutting opportunities that may not belong to one file.

| Approach                                    | Status      | Performance evidence | Code-analysis notes | Potential | Findings |
|---------------------------------------------|-------------|----------------------|---------------------|-----------|----------|
| Full formatter integration tests            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| CLI subprocess tests                        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Temporary filesystem tests                  | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Rule Markdown example execution             | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Markdown documentation validation           | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Large parametrized rule matrices            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Repeated LibCST parsing and metadata setup  | Not started | TBD                  | TBD                 | TBD       | TBD      |
| Repeated settings and rule collection setup | Not started | TBD                  | TBD                 | TBD       | TBD      |

## Findings

Add detailed findings here during the audit. Use one subsection per finding.

### Finding Template

- **Status:** Open
- **Potential:** TBD
- **Affected rows:** TBD
- **Files/functions:** TBD
- **Evidence:** TBD
- **Code analysis:** TBD
- **Coverage-preserving approach:** TBD
- **Coverage-risk analysis:** TBD
- **Tests/verification:** TBD
- **User decisions needed:** None

## Test-Design Decisions

Record possible test-design questions here before recommending any speedup that would weaken, narrow, or otherwise change test coverage.

| Question | Affected tests/helpers | Why it matters for performance | Coverage risk | User decision | Status      |
|----------|------------------------|--------------------------------|---------------|---------------|-------------|
| TBD      | TBD                    | TBD                            | TBD           | TBD           | Not started |

## Rule-Audit Refresh Notes

Use this section to record whether rule implementation changes require updates to `docs/rule_performance_audit.md` before relying on that plan.

| Rule implementation scope | Change evidence | Needed rule-audit action | Status      |
|---------------------------|-----------------|--------------------------|-------------|
| TBD                       | TBD             | TBD                      | Not started |

## Completion Checklist

- [ ] Test and helper inventory refreshed as the first audit action.
- [ ] Rule implementation changes checked against `docs/rule_performance_audit.md`.
- [ ] Baseline commands and environment recorded.
- [ ] Slowest tests identified.
- [ ] Every test file checked.
- [ ] Every shared fixture and helper checked.
- [ ] Cross-cutting testing approaches checked.
- [ ] Findings documented with coverage-risk analysis.
- [ ] Test-design decisions recorded separately.
- [ ] Highest-value coverage-preserving opportunities summarized.
