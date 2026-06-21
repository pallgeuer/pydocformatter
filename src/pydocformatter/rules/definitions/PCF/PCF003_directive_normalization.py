from __future__ import annotations

import re

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata

_LIST_ITEM_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_NOQA_CODE_RE = re.compile(r"^[A-Za-z]+[A-Za-z0-9-]*\d+[A-Za-z0-9-]*$")
_TYPE_IGNORE_RE = re.compile(r"^type\s*:\s*ignore(?P<codes>\[[^\]]*\])?(?P<rest>.*)$", re.IGNORECASE)
_NOQA_RE = re.compile(r"^noqa(?:\s*:\s*(?P<codes>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_PREFIXED_NOQA_RE = re.compile(r"^(?P<head>ruff|flake8)\s*:\s*noqa(?:\s*:\s*(?P<codes>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_PYLINT_RE = re.compile(r"^pylint\s*:\s*(?P<action>disable|enable|disable-next)\s*=\s*(?P<messages>[^#]*?)(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_COLON_VALUE_RE = re.compile(r"^(?P<head>pyright|mypy|ruff|flake8|fmt|isort|pragma)\s*:\s*(?P<value>.*)$", re.IGNORECASE)


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF003DirectiveNormalization(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF003"),
        name="directive-normalization",
        message="Directive comment should be normalized",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return directive normalization findings."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply directive normalization fixes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all directive normalization changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    changes: list[rule_edits.PlannedSourceChange] = []
    for comment in data.comments:
        if comment.kind not in (PCF_definition.CommentKind.TYPE_DIRECTIVE, PCF_definition.CommentKind.TOOL_DIRECTIVE):
            continue
        content = _normalized_directive_content(comment.content)
        if comment.placement == PCF_definition.CommentPlacement.TRAILING:
            replacement = f"{comment.line_prefix}{PCF_definition.render_comment(content, include_indent=False)}"
        else:
            replacement = PCF_definition.render_comment(content, indent=comment.indent)
        change = PCF_definition.planned_full_line_change(data, comment, replacement)
        if change is not None:
            changes.append(change)
    return tuple(changes)


def _normalized_directive_content(content: str) -> str:
    """Return safely normalized directive content without the leading hash."""
    if (match := _TYPE_IGNORE_RE.match(content)) is not None:
        return f"type: ignore{_normalized_bracketed_list(match.group('codes'))}{match.group('rest')}"
    if (match := _NOQA_RE.match(content)) is not None:
        return _normalized_noqa("noqa", match.group("codes"), match.group("rest"))
    if (match := _PREFIXED_NOQA_RE.match(content)) is not None:
        head = match.group("head").lower()
        return _normalized_noqa(f"{head}: noqa", match.group("codes"), match.group("rest"))
    if (match := _PYLINT_RE.match(content)) is not None:
        action = match.group("action").lower()
        messages = _normalized_comma_list(match.group("messages"), item_re=_LIST_ITEM_RE)
        return f"pylint: {action}={messages}{match.group('rest')}"
    if (match := _COLON_VALUE_RE.match(content)) is not None:
        return _normalized_colon_value(match.group("head"), match.group("value"))
    for keyword in ("nosec", "nosemgrep"):
        if content.lower().startswith(keyword):
            return f"{keyword}{content[len(keyword):]}"
    return content


def _normalized_noqa(head: str, codes: str | None, rest: str) -> str:
    """Return a normalized noqa-style directive."""
    if codes is None:
        return f"{head}{rest}"
    normalized_codes = _normalized_comma_list(codes, item_re=_NOQA_CODE_RE, uppercase=True)
    return _normalized_colon_payload(head, f"{normalized_codes}{rest}")


def _normalized_bracketed_list(text: str | None) -> str:
    """Return a normalized bracketed directive list when it is clearly comma-separated."""
    if text is None:
        return ""
    inner = text[1:-1]
    normalized = _normalized_comma_list(inner, item_re=_LIST_ITEM_RE)
    return f"[{normalized}]"


def _normalized_comma_list(text: str, *, item_re: re.Pattern[str], uppercase: bool = False) -> str:
    """Normalize a comma-separated directive list when every item has a safe token shape."""
    items = tuple(item.strip() for item in text.split(","))
    if not items or not all(item and item_re.match(item) is not None for item in items):
        return text.strip()
    if uppercase:
        items = tuple(item.upper() for item in items)
    return ", ".join(items)


def _normalized_colon_value(head: str, value: str) -> str:
    """Return a normalized colon directive while preserving unknown value text."""
    normalized_head = head.lower()
    if normalized_head == "fmt" and value.lower() in {"on", "off", "skip"}:
        value = value.lower()
    elif normalized_head == "isort" and value.lower() in {"skip", "skip_file"}:
        value = value.lower()
    elif normalized_head == "pragma" and value.lower() in {"no cover", "no branch"}:
        value = value.lower()
    return _normalized_colon_payload(normalized_head, value)


def _normalized_colon_payload(head: str, payload: str) -> str:
    """Return a colon directive without adding trailing whitespace for an empty payload."""
    if not payload:
        return f"{head}:"
    if payload[0] in " \t\f":
        return f"{head}:{payload}"
    return f"{head}: {payload}"
