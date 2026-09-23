# Versioning and compatibility

pydocformatter follows semantic versioning. This policy describes the compatibility commitments for current and future releases. Historical exceptions remain documented in the [Changelog](project/changelog.md).

## Public compatibility surface

The compatibility-sensitive public interface consists of:

- Documented `pydocfmt` commands, options, exit behavior, and file-selection behavior.
- Configuration names, defaults, accepted values, and precedence.
- Rule codes, canonical rule names, selection behavior, and published rule metadata.
- Diagnostics and formatted output.

Python imports are internal unless the API reference explicitly identifies them as public. The command-line interface is the supported integration boundary.

## Release compatibility

Patch releases may correct defects, unsafe behavior, and deviations from documented intent. Minor releases may add commands, settings, rules, and other backward-compatible capabilities. Correctness and safety fixes in patch or minor releases may change diagnostics or formatted output toward the documented behavior; such changes require focused tests and a changelog entry.

Intentional incompatible policy changes, removals, renames, and rule-code reassignments require a major release. Deprecated interfaces remain supported and documented for at least one minor release and are removed only in a major release.

An unsafe fix or otherwise harmful behavior may be disabled promptly without a deprecation window. The changelog and affected documentation will prominently explain the change and any migration.

## Runtime support

pydocformatter supports the current CPython versions and operating systems listed in [Installation](installation.md). Dropping a supported Python version, implementation, or platform normally requires a major release. A security issue or unavoidable upstream constraint may require an earlier drop; the release notes and installation documentation will make that exception prominent.

## Rule lifecycle

Shipped rules are stable and record their first stable version in `stable_since`; pydocformatter does not imply a separate preview lifecycle for them. Minor releases may add broadly applicable, low-disruption rules to the default selection.

Noisy, policy-oriented, convention-specific, or otherwise disruptive rules are introduced behind explicit selection or a convention gate. Release notes explain selection changes that could produce new findings or fixes. Removing a rule, renaming its canonical identity, or reassigning its code follows the major-release and deprecation policy above.

## Fix guarantees

For the same pydocformatter version, settings, selected rules, and input source, a successful error-free fix run reaches a fixed point: rerunning it produces no further changes. A detected fix cycle or iteration limit is an operational error rather than a successful result.

Before applying edits, pydocformatter validates source ranges and rejects overlapping changes. It reparses rewritten Python and requires each applied edit to map to the exact planned source range. Source-literal rewrites preserve the evaluated docstring value when the rule requires semantic equivalence. Documentation-formatting rules may intentionally change the resulting `__doc__` text, so pydocformatter does not claim that all docstrings or runtime semantics remain unchanged.

When processing fenced Python in Markdown, pydocformatter preserves content outside supported fences. If any rewritten block cannot be reconstructed and validated safely, the Markdown file is rolled back atomically instead of being partially updated.
