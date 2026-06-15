# section-name-colon (PDF405)

Fix is sometimes available.

## What it does
Implementation pending. This rule is reserved for ensuring recognized Google-style section names end with a colon where that convention requires one.

## Why is this useful?
The colon is part of the Google-style section header spelling and helps distinguish headers from ordinary prose.

## Ruff compatibility
This rule is intended to replace Ruff's `D416`.

## Example
The pending implementation will eventually report section names missing a required colon. For now, the rule is a no-op:

```pydocfmt-example
[input]
def value(arg):
    """Return the value.

    Args
        arg: The value.
    """

[output=unchanged]
```

## Options
None.
