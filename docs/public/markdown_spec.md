# Markdown source specification

This document specifies how `pydocfmt` checks and formats fenced Python blocks in Markdown sources.

## File and fence selection

The built-in `.md` extension selects Markdown handling, and the default include patterns discover `.md` files alongside Python source. The `extension` setting can assign another filename extension to Markdown without changing discovery:

```toml
[tool.pydocfmt]
extend-include = ["*.mdx"]

[tool.pydocfmt.extension]
mdx = "markdown"
```

The mapping is sufficient for an explicit path or `--stdin-filename`, because those inputs bypass include matching. Directory traversal also needs a matching `include` or `extend-include` pattern. Bare `-` input retains Python handling.

Extension matching uses the final filename suffix and is ASCII case-insensitive. Configured keys may have one leading dot, are normalized to lowercase, and cannot replace the fixed built-in assignments. A selected path without a built-in or configured language is not parsed or modified: pydocfmt reports an operational error for that path, continues with other selected files, and exits unsuccessfully. `--show-files` retains the accepted discovery decision and reports the same missing-language error.

pydocfmt recognizes closed backtick and tilde fences whose first info-string token is `python`, `py`, or `python3`, compared case-insensitively. Recognition examines raw physical lines and treats only CR, LF, and CRLF as line endings. An opening or closing fence line may have zero to three leading spaces before its marker. A closing fence must use the same marker character, contain at least as many markers as the opener, and have no content after the markers except spaces or tabs.

pydocfmt does not parse CommonMark block quote or list container prefixes. A raw line beginning with a block quote marker is not a fence line, and a marker indented by four or more spaces is not recognized. Conversely, any raw line satisfying the zero-to-three-space form is eligible even when a full CommonMark container parser might assign it to surrounding list content. Other fence languages, nested fence-like text, and unclosed fences are left untouched. In an unclosed fence, the opener consumes the remainder of the file for discovery purposes, so later fence-like lines are not treated as separate blocks.

Add the standalone `pydocfmt-skip` token after the language to leave an otherwise recognized block untouched:

````md
```python pydocfmt-skip
def intentionally_incomplete(): ...
```
````

The token is case-sensitive and must be whitespace-delimited. Other info-string tokens may appear before or after it.

## Parsing and formatting

Each recognized block body is parsed as independent Python source and receives the effective settings and rules for the containing Markdown path. For a fence indented by up to three spaces, pydocformatter removes up to the opener's indentation from each physical body line before Python parsing, matching CommonMark's fence-body indentation rule within the raw-line scope above. Unchanged physical lines are preserved byte for byte; generated or changed nonblank logical lines receive the opener's indentation when reconstructed, while generated blank lines remain empty rather than gaining trailing spaces. This also preserves a UTF-8 byte order mark before a first-line opener.

Markdown text, opening and closing fences, other code blocks, and explicitly skipped block bodies are preserved byte for byte. Fixes replace only recognized Python block bodies. After reconstruction, pydocformatter rescans the complete candidate and verifies every fence delimiter, info string, selected body, and unselected body. If formatted Python would alter the Markdown fence topology or intended logical bodies, pydocformatter rejects the complete file rewrite, reports an operational error, and reports the findings from the original source.

Findings, parse diagnostics, and rule operational-error line details use line numbers from the containing Markdown file. Source suppressions inside a block use normal Python suppression semantics and remain local to that parsed block.

Check mode reports a LibCST parsing error for each malformed recognized block while continuing to check other recognized blocks. Fix and diff modes are atomic per Markdown file: if any recognized block is malformed or produces an operational error, pydocfmt does not apply changes to any block in that file.

Disk-backed Markdown files participate in persistent clean-proof caching under the same eligibility and invalidation rules as Python files. The resolved source language is part of the clean-proof identity, so changing a custom extension between Python and Markdown handling cannot reuse an incompatible proof. Standard-input requests are never cached. Diff mode previews the same file-atomic candidate that fix mode would write.

## Language-aware defaults

A fenced example is commonly a fragment rather than a complete importable module. Every source assigned to Markdown therefore receives these effective defaults, whether Markdown was selected by the built-in `.md` extension or a custom extension mapping:

```toml
source-context = "fragment"
docstring-missing-documentation = "has-section"
```

`source-context = "fragment"` disables rules whose meaning requires a complete module, including package and module documentation requirements, missing definition docstrings, and module-attribute ownership policies. This applicability is hard metadata, so exact rule selection does not restore module-only rules in fragment context. Other rules still check docstrings and comments that examples contain. `docstring-missing-documentation = "has-section"` avoids requiring entries merely because an illustrative definition exists while retaining completeness checks for documentation sections authors chose to include.

The Markdown defaults apply after hard-coded defaults and ordinary project configuration. Matching `per-file-settings` then apply on top. Inline `--config` values, dedicated command-line options, and in-process field overrides have higher source priority and are not replaced by the language defaults. Consequently, a project's ordinary Python-oriented `source-context` or missing-documentation setting does not need Markdown filename patterns, while an explicit higher-priority invocation can still change either behavior.

Use a per-file entry to opt complete embedded modules back into module semantics:

```toml
[tool.pydocfmt.per-file-settings]
"docs/complete_modules/*.md" = { source-context = "module", docstring-missing-documentation = "all-docstrings" }
```

Custom Markdown extensions receive the same automatic defaults. A per-file pattern is needed only for files that deliberately override them, and normal filename pattern matching still applies:

```toml
[tool.pydocfmt.extension]
mdx = "markdown"

[tool.pydocfmt.per-file-settings]
"docs/complete_modules/*.mdx" = { source-context = "module", docstring-missing-documentation = "all-docstrings" }
```

Use `pydocfmt-skip` for intentionally malformed, pedagogically incomplete, or deliberately nonconforming examples that cannot be expressed meaningfully through project-wide or per-file settings.

## Related specifications

- [File selection specification](file_selection_spec.md) defines include, exclude, and explicit-path behavior.
- [Settings specification](settings_spec.md) defines `source-context`, per-file settings, and precedence.
- [Rule selection specification](rule_selection_spec.md) defines rule applicability and selector resolution.
