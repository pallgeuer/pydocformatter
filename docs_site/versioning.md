# Versioning

pydocformatter follows semantic versioning for the package API and command-line behavior.

## Rule stability

Rule documentation records the version where each rule became stable. New rules may be added in minor releases. Existing rule behavior may be refined when a fix improves correctness, safety, or compatibility with documented behavior.

## Fix compatibility

Automatic fixes are conservative. A rule may report a finding without a fix when preserving source semantics is uncertain.

## Deprecation

Deprecated command-line options, settings, or rule behaviors should remain documented through the release that removes them and should be called out in the [Changelog](project/changelog.md).
