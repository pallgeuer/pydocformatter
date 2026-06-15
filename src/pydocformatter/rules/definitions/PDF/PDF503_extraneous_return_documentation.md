# extraneous-return-documentation (PDF503)

Fix is not available.

## What it does
Implementation pending. This rule is reserved for reporting return documentation on functions that do not return a meaningful value.

## Why is this useful?
Extraneous return sections can imply a result where the function returns only `None`.

## Ruff compatibility
This rule is intended to replace Ruff's `DOC202`.

## Example
The pending implementation will eventually report extraneous return documentation. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value():
    """Do the work.

    Returns:
        int: The value.
    """

[output=unchanged]
```

## Options
None.
