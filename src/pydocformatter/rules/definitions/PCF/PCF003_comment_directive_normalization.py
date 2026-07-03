"""PCF003 comment-directive-normalization rule."""

from __future__ import annotations

import re

import pydocformatter.rules.definition_helpers.directives as directive_helpers
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata

_LIST_ITEM_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
# ty: prefixes are accepted only in type: ignore[...] lists, where mixed type-checker payloads are used.
_TYPE_IGNORE_ITEM_RE = re.compile(r"^(?:ty:)?[A-Za-z0-9_.-]+$")
_NOQA_CODE_RE = re.compile(r"^[A-Za-z]+[A-Za-z0-9-]*\d+[A-Za-z0-9-]*$")
_PYDOCFMT_SELECTOR_RE = re.compile(r"^(?:ALL|[A-Za-z]+[0-9]*)$")
_TYPE_IGNORE_RE = re.compile(r"^type\s*:\s*ignore(?P<codes>\[[^\]]*\])?(?P<rest>.*)$", re.IGNORECASE)
_TY_IGNORE_RE = re.compile(r"^ty\s*:\s*ignore(?P<codes>\[[^\]]*\])?(?P<rest>.*)$", re.IGNORECASE)
_PREFIXED_NOQA_RE = re.compile(r"^(?P<head>ruff|flake8)\s*:\s*noqa(?:\s*:\s*(?P<codes>[^#]*?))?(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_RUFF_BRACKET_RE = re.compile(r"^ruff\s*:\s*(?P<action>ignore|disable|enable|file-ignore)\s*(?P<codes>\[[^\]]*\])(?P<rest>.*)$", re.IGNORECASE)
_RUFF_ISORT_RE = re.compile(r"^ruff\s*:\s*isort\s*:\s*(?P<value>.*)$", re.IGNORECASE)
_NOINSPECTION_RE = re.compile(r"^noinspection(?:\s+(?P<inspections>.*))?$", re.IGNORECASE)
_LANGUAGE_INJECTION_RE = re.compile(r"^language\s*=\s*(?P<language>\S+)(?P<rest>.*)$", re.IGNORECASE)
_FORMATTER_MARKER_RE = re.compile(r"^@formatter\s*:\s*(?P<state>on|off)(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_PYLINT_RE = re.compile(r"^pylint\s*:\s*(?P<action>disable|enable|disable-next)\s*=\s*(?P<messages>[^#]*?)(?P<rest>[ \t\f]+#.*|)$", re.IGNORECASE)
_COLON_VALUE_RE = re.compile(r"^(?P<head>pyright|mypy|ruff|flake8|fmt|isort|pragma)\s*:\s*(?P<value>.*)$", re.IGNORECASE)


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF003CommentDirectiveNormalization(RuleBase):
    """Rule implementation for PCF003.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF003"),
        name="comment-directive-normalization",
        message="Directive comment should be normalized",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return directive normalization violations.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


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
        return f"type: ignore{_normalized_bracketed_list(match.group('codes'), item_re=_TYPE_IGNORE_ITEM_RE)}{match.group('rest')}"
    if (match := _TY_IGNORE_RE.match(content)) is not None:
        return f"ty: ignore{_normalized_bracketed_list(match.group('codes'), item_re=_LIST_ITEM_RE)}{match.group('rest')}"
    if (match := directive_helpers.NOQA_RE.match(content)) is not None:
        return _normalized_noqa("noqa", match.group("selectors"), match.group("rest"))
    if (match := directive_helpers.PYDOCFMT_NOQA_RE.match(content)) is not None:
        return _normalized_pydocfmt_noqa(match.group("selectors"), match.group("rest"))
    if (match := directive_helpers.PYDOCFMT_BRACKET_RE.match(content)) is not None and match.group("action").lower() in {"ignore", "file-ignore"}:
        action = match.group("action").lower()
        codes = _normalized_bracketed_list(match.group("codes"), item_re=_PYDOCFMT_SELECTOR_RE, allow_trailing_comma=True, uppercase=True)
        return f"pydocfmt: {action}{codes}{match.group('rest')}"
    if (match := _PREFIXED_NOQA_RE.match(content)) is not None:
        head = match.group("head").lower()
        return _normalized_noqa(f"{head}: noqa", match.group("codes"), match.group("rest"))
    if (match := _RUFF_BRACKET_RE.match(content)) is not None:
        action = match.group("action").lower()
        codes = _normalized_bracketed_list(match.group("codes"), item_re=_LIST_ITEM_RE, allow_trailing_comma=True)
        return f"ruff: {action}{codes}{match.group('rest')}"
    if (match := _RUFF_ISORT_RE.match(content)) is not None:
        return _normalized_colon_payload("ruff", _normalized_colon_value("isort", match.group("value")))
    if (match := _NOINSPECTION_RE.match(content)) is not None:
        inspections = match.group("inspections")
        if inspections is None:
            return "noinspection"
        return f"noinspection {_normalized_comma_list(inspections, item_re=_LIST_ITEM_RE)}"
    if (match := _LANGUAGE_INJECTION_RE.match(content)) is not None:
        return f"language={match.group('language')}{match.group('rest')}"
    if (match := _FORMATTER_MARKER_RE.match(content)) is not None:
        return f"@formatter:{match.group('state').lower()}{match.group('rest')}"
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


def _normalized_pydocfmt_noqa(codes: str | None, rest: str) -> str:
    """Return a normalized pydocfmt noqa directive."""
    if codes is None:
        return f"pydocfmt: noqa{rest}"
    normalized_codes = _normalized_comma_list(codes, item_re=_PYDOCFMT_SELECTOR_RE, uppercase=True)
    return _normalized_colon_payload("pydocfmt: noqa", f"{normalized_codes}{rest}")


def _normalized_bracketed_list(text: str | None, *, item_re: re.Pattern[str], allow_trailing_comma: bool = False, uppercase: bool = False) -> str:
    """Return a normalized bracketed directive list when it is clearly comma-separated."""
    if text is None:
        return ""
    inner = text[1:-1]
    normalized = _normalized_comma_list(inner, item_re=item_re, allow_trailing_comma=allow_trailing_comma, uppercase=uppercase)
    return f"[{normalized}]"


def _normalized_comma_list(text: str, *, item_re: re.Pattern[str], uppercase: bool = False, allow_trailing_comma: bool = False) -> str:
    """Normalize a comma-separated directive list when every item has a safe token shape."""
    items = tuple(item.strip() for item in text.split(","))
    if allow_trailing_comma and items and not items[-1]:
        items = items[:-1]
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
    elif normalized_head == "isort" and value.lower() in {"off", "on", "skip", "skip_file", "split"}:
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
