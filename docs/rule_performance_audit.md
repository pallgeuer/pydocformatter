# Rule Performance Audit

Rule inventory up-to-date commit: `1770d287742708de7f710f81535e37c316e8255e`

This plan is a ready-to-use tracking ledger for a future audit of every rule category and rule implementation for unnecessarily or avoidably slow code. The audit must combine performance evidence with code analysis and must not introduce externally visible behavior changes. If an optimization would require treating current behavior as a bug, record it as a user-confirmation item before any implementation work.

## Goal Command

Paste this command into Codex when you want the audit to start:

```text
/goal Audit every pydocformatter rule category and rule implementation for unnecessarily or avoidably slow code. First update every inventory table in docs/rule_performance_audit.md from the latest Git-tracked rule category and rule implementation files, because rules may have been added, removed, renamed, or substantially changed since the rule inventory up-to-date commit recorded at the top of the file. Then measure or otherwise characterize performance, analyze the implementation code for behavior-preserving speedups, and maintain docs/rule_performance_audit.md continuously as the source of truth. Do not implement fixes during the audit unless I explicitly ask for an implementation pass. Do not recommend externally visible behavior changes unless they are confirmed bugs; if an apparent speedup depends on changing behavior, record the bug-versus-intended-behavior question in the plan and ask me to confirm before treating it as an optimization. The goal is complete only when every category and every rule row in the plan has performance evidence, code-analysis notes, potential speedup classification, and any detailed findings or no-finding rationale recorded.
```

## Scope

- Audit category implementations in `src/pydocformatter/rules/definitions/*/*.py`.
- Audit every concrete rule implementation in `src/pydocformatter/rules/definitions/*/*_*.py`.
- Record all findings here before implementation.
- Keep behavior-preserving opportunities separate from possible bug fixes.

## Audit Commands

Record exact commands here when the audit is executed. Use `uv` for all Python execution and do not configure a custom uv cache.

| Purpose                | Command | Notes                                                                              |
|------------------------|---------|------------------------------------------------------------------------------------|
| Baseline full check    | TBD     | Record wall time, CPU time if available, selected options, and working-tree state. |
| Category focused check | TBD     | Record one row per category if focused selection is possible.                      |
| Rule focused check     | TBD     | Record one row per rule if focused selection is possible.                          |
| Profiling              | TBD     | Record profiler, output path, and interpretation notes.                            |
| Behavior guard         | TBD     | Record golden-output or test commands used to prove no external behavior change.   |

## Status Legend

- `Not started`: no audit work recorded yet.
- `Measuring`: timing or profiling is underway.
- `Analyzing`: implementation code is being inspected.
- `Done`: performance evidence and code-analysis notes are recorded.
- `Blocked`: progress needs user input or missing tooling.

## Category Inventory

| Category | Implementation                                    | Status      | Performance evidence | Code-analysis notes | Potential | Findings |
|----------|---------------------------------------------------|-------------|----------------------|---------------------|-----------|----------|
| PCF      | `src/pydocformatter/rules/definitions/PCF/PCF.py` | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF      | `src/pydocformatter/rules/definitions/PDF/PDF.py` | Not started | TBD                  | TBD                 | TBD       | TBD      |

## Rule Inventory

| Rule   | Implementation                                                                              | Status      | Performance evidence | Code-analysis notes | Potential | Findings |
|--------|---------------------------------------------------------------------------------------------|-------------|----------------------|---------------------|-----------|----------|
| PCF001 | `src/pydocformatter/rules/definitions/PCF/PCF001_standalone_comment_formatting.py`          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PCF002 | `src/pydocformatter/rules/definitions/PCF/PCF002_trailing_comment_spacing.py`               | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PCF003 | `src/pydocformatter/rules/definitions/PCF/PCF003_comment_directive_normalization.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PCF004 | `src/pydocformatter/rules/definitions/PCF/PCF004_trailing_comment_extraction.py`            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF000 | `src/pydocformatter/rules/definitions/PDF/PDF000_docstring_literal_normalization.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF001 | `src/pydocformatter/rules/definitions/PDF/PDF001_docstring_quote_style.py`                  | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF002 | `src/pydocformatter/rules/definitions/PDF/PDF002_docstring_backslash_raw_prefix.py`         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF100 | `src/pydocformatter/rules/definitions/PDF/PDF100_docstring_indentation.py`                  | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF101 | `src/pydocformatter/rules/definitions/PDF/PDF101_docstring_reflow.py`                       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF102 | `src/pydocformatter/rules/definitions/PDF/PDF102_docstring_trailing_whitespace.py`          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF103 | `src/pydocformatter/rules/definitions/PDF/PDF103_docstring_blank_line_whitespace.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF104 | `src/pydocformatter/rules/definitions/PDF/PDF104_opening_quotes_whitespace.py`              | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF105 | `src/pydocformatter/rules/definitions/PDF/PDF105_closing_quotes_whitespace.py`              | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF106 | `src/pydocformatter/rules/definitions/PDF/PDF106_multiline_opening_quotes_same_line.py`     | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF107 | `src/pydocformatter/rules/definitions/PDF/PDF107_multiline_opening_quotes_separate_line.py` | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF108 | `src/pydocformatter/rules/definitions/PDF/PDF108_multiline_closing_quotes_same_line.py`     | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF109 | `src/pydocformatter/rules/definitions/PDF/PDF109_multiline_closing_quotes_separate_line.py` | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF110 | `src/pydocformatter/rules/definitions/PDF/PDF110_one_line_docstring.py`                     | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF200 | `src/pydocformatter/rules/definitions/PDF/PDF200_too_many_blank_lines.py`                   | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF201 | `src/pydocformatter/rules/definitions/PDF/PDF201_missing_blank_line.py`                     | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF202 | `src/pydocformatter/rules/definitions/PDF/PDF202_empty_docstring.py`                        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF203 | `src/pydocformatter/rules/definitions/PDF/PDF203_summary_too_long.py`                       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF300 | `src/pydocformatter/rules/definitions/PDF/PDF300_summary_trailing_period.py`                | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF301 | `src/pydocformatter/rules/definitions/PDF/PDF301_summary_terminal_punctuation.py`           | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF302 | `src/pydocformatter/rules/definitions/PDF/PDF302_non_imperative_summary.py`                 | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF303 | `src/pydocformatter/rules/definitions/PDF/PDF303_signature_like_summary.py`                 | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF304 | `src/pydocformatter/rules/definitions/PDF/PDF304_summary_first_word_capitalization.py`      | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF305 | `src/pydocformatter/rules/definitions/PDF/PDF305_summary_starts_with_this.py`               | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF400 | `src/pydocformatter/rules/definitions/PDF/PDF400_section_name_capitalization.py`            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF401 | `src/pydocformatter/rules/definitions/PDF/PDF401_section_name_pluralization.py`             | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF402 | `src/pydocformatter/rules/definitions/PDF/PDF402_section_name_term_normalization.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF403 | `src/pydocformatter/rules/definitions/PDF/PDF403_section_name_trailing_content.py`          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF404 | `src/pydocformatter/rules/definitions/PDF/PDF404_section_name_trailing_colon.py`            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF405 | `src/pydocformatter/rules/definitions/PDF/PDF405_section_underline_format.py`               | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF406 | `src/pydocformatter/rules/definitions/PDF/PDF406_empty_section.py`                          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF407 | `src/pydocformatter/rules/definitions/PDF/PDF407_section_order.py`                          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF408 | `src/pydocformatter/rules/definitions/PDF/PDF408_repeated_section.py`                       | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF409 | `src/pydocformatter/rules/definitions/PDF/PDF409_docstring_entry_spacing.py`                | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF410 | `src/pydocformatter/rules/definitions/PDF/PDF410_exception_entry_normalization.py`          | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF411 | `src/pydocformatter/rules/definitions/PDF/PDF411_type_like_token_spacing_normalization.py`  | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF500 | `src/pydocformatter/rules/definitions/PDF/PDF500_missing_parameter_documentation.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF501 | `src/pydocformatter/rules/definitions/PDF/PDF501_extraneous_parameter_documentation.py`     | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF502 | `src/pydocformatter/rules/definitions/PDF/PDF502_missing_return_documentation.py`           | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF503 | `src/pydocformatter/rules/definitions/PDF/PDF503_extraneous_return_documentation.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF504 | `src/pydocformatter/rules/definitions/PDF/PDF504_missing_yield_documentation.py`            | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF505 | `src/pydocformatter/rules/definitions/PDF/PDF505_extraneous_yield_documentation.py`         | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF506 | `src/pydocformatter/rules/definitions/PDF/PDF506_missing_exception_documentation.py`        | Not started | TBD                  | TBD                 | TBD       | TBD      |
| PDF507 | `src/pydocformatter/rules/definitions/PDF/PDF507_extraneous_exception_documentation.py`     | Not started | TBD                  | TBD                 | TBD       | TBD      |

## Findings

Add detailed findings here during the audit. Use one subsection per finding.

### Finding Template

- **Status:** Open
- **Potential:** TBD
- **Affected rows:** TBD
- **Files/functions:** TBD
- **Evidence:** TBD
- **Code analysis:** TBD
- **Behavior-preserving approach:** TBD
- **Behavior-risk analysis:** TBD
- **Tests/verification:** TBD
- **User decisions needed:** None

## Possible Bug Decisions

Record possible bug-versus-intended-behavior questions here before recommending any speedup that would change externally visible behavior.

| Question | Affected rules/categories | Why it matters for performance | User decision | Status      |
|----------|---------------------------|--------------------------------|---------------|-------------|
| TBD      | TBD                       | TBD                            | TBD           | Not started |

## Completion Checklist

- [ ] Baseline commands and environment recorded.
- [ ] PCF category implementation checked.
- [ ] PDF category implementation checked.
- [ ] Every PCF rule checked.
- [ ] Every PDF rule checked.
- [ ] Findings documented with behavior-risk analysis.
- [ ] Possible bug decisions recorded separately.
- [ ] Highest-value behavior-preserving opportunities summarized.
