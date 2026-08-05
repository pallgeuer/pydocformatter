"""Tests for deterministic persistent-cache fingerprints."""

# Future imports
from __future__ import annotations

# Standard library imports
import io
import os
import json
import typing
import tomllib
import subprocess
import dataclasses
import importlib.metadata
from pathlib import Path

# Third-party imports
import pytest

# First-party imports
import pydocformatter
import pydocformatter.rules.collection as rule_collection
import pydocformatter.cache.fingerprint as cache_fingerprint
from pydocformatter import formatter, rules_selection
from pydocformatter.cache.models import CACHE_PROTOCOL_VERSION, CACHE_SCHEMA_VERSION, EngineFingerprint
from pydocformatter.cli import settings_check
from pydocformatter.cli.global_args import GlobalArgs
from pydocformatter.formatter import CleanSourceSnapshot
from pydocformatter.source_path import SourcePathContext


if typing.TYPE_CHECKING:
    # Third-party imports
    from pytest_mock import MockerFixture

    # First-party imports
    from pydocformatter.settings import SettingsProfile


_ALTERNATE_DIRECT_ANALYSIS_VALUES = {
    "line_length": 89,
    "url_aware_wrapping": False,
    "line_ending": settings_check.LineEnding.LF,
    "indent_style": settings_check.IndentStyle.TAB,
    "indent_width": 2,
    "docstring_convention": settings_check.DocstringConvention.GOOGLE,
    "docstring_blank_line_style": settings_check.DocstringBlankLineStyle.ALIGNED,
    "docstring_blank_line_after_last_section": True,
    "docstring_missing_documentation": settings_check.DocstringMissingDocumentation.ALL_DOCSTRINGS,
    "docstring_missing_documentation_public_only": False,
    "docstring_require_init_attribute_documentation": True,
    "docstring_include_assertion_errors": True,
    "docstring_class_attribute_no_type_base_classes": ("project.Enum",),
    "docstring_forbidden_function_decorators": ("project.forbidden",),
    "docstring_optional_function_decorators": ("project.optional",),
    "docstring_placeholder_markers": ("WIP",),
    "docstring_property_decorators": ("project.property",),
    "docstring_parse_list_items": False,
    "docstring_parse_headings": False,
    "docstring_parse_doctests": False,
    "docstring_parse_code_fences": False,
    "docstring_parse_block_quotes": False,
    "docstring_parse_tables": False,
    "docstring_parse_directives": False,
    "docstring_parse_literal_blocks": False,
    "comment_join_standalone_lines": True,
    "comment_format_list_items": False,
    "comment_task_marker_mode": settings_check.CommentTaskMarkerMode.HANGING,
    "comment_task_markers": ("TASK",),
    "comment_preserve_headings": False,
    "comment_preserve_doctests": False,
    "comment_preserve_code_fences": False,
    "comment_format_block_quotes": False,
    "comment_preserve_tables": False,
    "comment_preserve_directives": False,
    "comment_trailing_extraction_syntax_aware": False,
    "comment_trailing_extraction_content_aware": False,
    "comment_detect_code": True,
    "comment_detect_statements": False,
    "comment_detect_expressions": True,
}

_ALTERNATE_EXCLUDED_VALUES = {
    "cache": False,
    "cache_dir": "alternate-cache",
    "parallelism": 2.0,
    "include": ("*.pyw",),
    "extend_include": ("*.pyw",),
    "exclude": ("build",),
    "extend_exclude": ("generated",),
    "respect_gitignore": False,
    "force_exclude": True,
}


def _loaded_profile(root: Path, **field_overrides: object) -> SettingsProfile[settings_check.CheckSettings]:
    """Return a validated isolated profile with field overrides."""
    return settings_check.SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(isolated=True), field_overrides=typing.cast("settings_check.CheckSettingsOverrides", field_overrides), path=str(root))


def test_source_digest_is_chunk_independent() -> None:
    source = b"a" * (1024 * 1024 + 17)

    digest, size = formatter.digest_source_file(io.BytesIO(source))

    assert digest == formatter.digest_source_bytes(source)
    assert size == len(source)


@pytest.mark.parametrize(("first", "second"), [(b"abc", b"abd"), (b"abc", b"ab"), (b"source\n", b"source\r\n"), (b"source\n", b"\xef\xbb\xbfsource\n")])
def test_source_digest_distinguishes_exact_raw_bytes(first: bytes, second: bytes) -> None:
    assert formatter.digest_source_bytes(first) != formatter.digest_source_bytes(second)


def test_canonical_encoding_is_independent_of_mapping_order() -> None:
    first = {"a": (1, 2), "b": frozenset({"x", "y"})}
    second = {"b": frozenset({"y", "x"}), "a": (1, 2)}

    assert cache_fingerprint.canonical_bytes(first) == cache_fingerprint.canonical_bytes(second)
    assert cache_fingerprint.canonical_digest(first) == cache_fingerprint.canonical_digest(second)


def test_canonical_encoding_is_independent_of_python_hash_seed() -> None:
    script = "import pydocformatter.cache.fingerprint as f; print(f.canonical_bytes({key: frozenset({key, 'shared'}) for key in {'alpha', 'beta', 'gamma'}}).hex())"
    outputs = []
    for seed in ("1", "8675309"):
        result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            ["uv", "run", "python", "-c", script], cwd=Path(__file__).parents[1], env={**os.environ, "PYTHONHASHSEED": seed}, shell=False, check=True, capture_output=True, text=True
        )
        outputs.append(result.stdout)

    assert outputs[0] == outputs[1]


def test_canonical_encoding_covers_supported_nested_types(tmp_path: Path) -> None:
    value = {
        "enum": settings_check.LineEnding.CR_LF,
        "tuple": (1, "two"),
        "frozenset": frozenset({"b", "a"}),
        "path": tmp_path / "module.py",
        "dataclass": CleanSourceSnapshot(source_digest=b"s" * 32, source_size=3, mtime_ns=os.stat(tmp_path).st_mtime_ns),
    }

    encoded = cache_fingerprint.canonical_bytes(value, project_root=tmp_path)

    assert encoded == cache_fingerprint.canonical_bytes(value, project_root=tmp_path)
    assert b"project-relative" in encoded
    assert b"cr-lf" in encoded


def test_canonical_user_lists_cannot_impersonate_internal_tags(tmp_path: Path) -> None:
    metadata = CleanSourceSnapshot(source_digest=b"s" * 32, source_size=3, mtime_ns=os.stat(tmp_path).st_mtime_ns)
    collisions = (
        (1.0, ["float", "0x1.0000000000000p+0"]),
        (("a",), ["tuple", ["a"]]),
        ({"a": 1}, ["mapping", [["a", 1]]]),
        (
            metadata,
            [
                "dataclass",
                f"{type(metadata).__module__}.{type(metadata).__qualname__}",
                [["source_digest", ["bytes", metadata.source_digest.hex()]], ["source_size", metadata.source_size], ["mtime_ns", metadata.mtime_ns]],
            ],
        ),
        (tmp_path / "module.py", ["project-relative", "module.py"]),
        (b"a", ["bytes", "61"]),
        (frozenset(("a",)), ["frozenset", ["a"]]),
        ([["float", "0x1.0000000000000p+0"]], ["list", [["float", "0x1.0000000000000p+0"]]]),
    )

    for internal_value, impersonating_list in collisions:
        encoded = cache_fingerprint.canonical_bytes(internal_value, project_root=tmp_path)
        assert encoded != cache_fingerprint.canonical_bytes(impersonating_list, project_root=tmp_path)
        assert encoded == cache_fingerprint.canonical_bytes(internal_value, project_root=tmp_path)


@pytest.mark.parametrize("value", [0.0, -0.0, 1.0, -2.0, 0.5, 1.5])
def test_canonical_float_encoding_accepts_finite_values_with_stable_hex_spelling(value: float) -> None:
    encoded = cache_fingerprint.canonical_bytes(value)

    assert encoded == json.dumps(["float", float(value).hex()], ensure_ascii=True, separators=(",", ":")).encode()
    assert encoded == cache_fingerprint.canonical_bytes(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_canonical_float_encoding_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        cache_fingerprint.canonical_bytes(value)


def test_analysis_settings_encoding_names_every_direct_field_and_no_other_field(tmp_path: Path) -> None:
    profile = _loaded_profile(tmp_path)
    identity = settings_check.analysis_settings_identity(profile)
    encoded = cache_fingerprint.canonical_bytes(identity)
    direct_fields = tuple(field for field, _ in identity)
    expected_direct_fields = tuple(definition.field for definition in settings_check.DIRECT_ANALYSIS_DEFINITIONS)

    assert direct_fields == expected_direct_fields
    assert set(_ALTERNATE_DIRECT_ANALYSIS_VALUES) == set(expected_direct_fields)
    for field in dataclasses.fields(settings_check.CheckSettings):
        if field.name in expected_direct_fields:
            assert json.dumps(field.name).encode() in encoded
        else:
            assert json.dumps(field.name).encode() not in encoded


@pytest.mark.parametrize(("field", "alternate"), _ALTERNATE_DIRECT_ANALYSIS_VALUES.items())
def test_every_direct_analysis_value_changes_analysis_settings_key(tmp_path: Path, field: str, alternate: object) -> None:
    base = _loaded_profile(tmp_path)
    changed = _loaded_profile(tmp_path, **{field: alternate})

    assert getattr(base.settings, field) != getattr(changed.settings, field)
    assert cache_fingerprint.analysis_settings_key(settings_check.analysis_settings_identity(base)) != cache_fingerprint.analysis_settings_key(settings_check.analysis_settings_identity(changed))


@pytest.mark.parametrize(("field", "alternate"), _ALTERNATE_EXCLUDED_VALUES.items())
def test_run_and_discovery_values_do_not_change_analysis_settings_key(tmp_path: Path, field: str, alternate: object) -> None:
    base = _loaded_profile(tmp_path)
    changed = _loaded_profile(tmp_path, **{field: alternate})

    assert getattr(base.settings, field) != getattr(changed.settings, field)
    assert cache_fingerprint.analysis_settings_key(settings_check.analysis_settings_identity(base)) == cache_fingerprint.analysis_settings_key(settings_check.analysis_settings_identity(changed))


def test_profile_bases_priorities_and_project_root_do_not_change_analysis_settings_key(tmp_path: Path) -> None:
    profile = _loaded_profile(tmp_path)
    changed = dataclasses.replace(
        profile,
        field_bases={field: str(tmp_path / "alternate-base") for field in profile.field_bases},
        field_priorities={field: priority + 1 for field, priority in profile.field_priorities.items()},
        project_root=str(tmp_path / "alternate-project"),
    )

    identity = settings_check.analysis_settings_identity(profile)
    changed_identity = settings_check.analysis_settings_identity(changed)

    assert identity == changed_identity
    assert cache_fingerprint.analysis_settings_key(identity) == cache_fingerprint.analysis_settings_key(changed_identity)


def test_effective_per_file_settings_change_analysis_key(tmp_path: Path) -> None:
    profile = _loaded_profile(tmp_path, select=("PDF101",), per_file_settings=(("*.py", (("line-length", 100),)),))
    target = tmp_path / "module.py"
    effective = settings_check.effective_profile_for_path(profile, str(target))
    selected = rules_selection.select_rules(profile.settings, profile=profile).for_path(str(target))

    assert effective.settings.line_length == 100
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(profile), selected)[1]
        != cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(effective), selected)[1]
    )


def test_unapplied_per_file_maps_do_not_change_analysis_key(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    first = _loaded_profile(tmp_path, select=("PDF101",), per_file_settings=(("other.py", (("line-length", 100),)),))
    second = _loaded_profile(tmp_path, select=("PDF101",), per_file_settings=(("*.txt", (("line-length", 120),)),))
    first_effective = settings_check.effective_profile_for_path(first, str(target))
    second_effective = settings_check.effective_profile_for_path(second, str(target))
    first_rules = rules_selection.select_rules(first.settings, profile=first).for_path(str(target))
    second_rules = rules_selection.select_rules(second.settings, profile=second).for_path(str(target))

    assert first_effective.settings.line_length == second_effective.settings.line_length == settings_check.CheckSettings().line_length
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(first_effective), first_rules)[1]
        == cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(second_effective), second_rules)[1]
    )


def test_parallelism_does_not_change_complete_analysis_key(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    first = _loaded_profile(tmp_path, select=("PDF300",), parallelism=1.0)
    second = _loaded_profile(tmp_path, select=("PDF300",), parallelism=4.0)
    first_rules = rules_selection.select_rules(first.settings, profile=first).for_path(str(target))
    second_rules = rules_selection.select_rules(second.settings, profile=second).for_path(str(target))

    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(first), first_rules)[1]
        == cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(second), second_rules)[1]
    )


def test_equivalent_selector_syntax_and_specificity_do_not_change_rule_or_analysis_keys(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    other_pdf3_codes = tuple(rule.meta.code.tag for rule in rule_collection.RULE_COLLECTION.rules if rule.meta.code.tag.startswith("PDF3") and rule.meta.code.tag != "PDF300")
    exact = _loaded_profile(tmp_path, select=("PDF300",), require_explicit=())
    broad = _loaded_profile(tmp_path, select=("PDF3",), ignore=other_pdf3_codes, require_explicit=())
    exact_rules = rules_selection.select_rules(exact.settings, profile=exact).for_path(str(target))
    broad_rules = rules_selection.select_rules(broad.settings, profile=broad).for_path(str(target))

    assert tuple(rule.rule.code.tag for rule in exact_rules) == tuple(rule.rule.code.tag for rule in broad_rules) == ("PDF300",)
    assert exact_rules[0].enabled_specificity != broad_rules[0].enabled_specificity
    assert cache_fingerprint.selected_rules_key(exact_rules) == cache_fingerprint.selected_rules_key(broad_rules)
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(exact), exact_rules)[1]
        == cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(broad), broad_rules)[1]
    )


def test_selector_source_priority_does_not_change_rule_or_analysis_keys(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    inline = settings_check.SETTINGS_SCHEMA.load_profile(global_values=GlobalArgs(isolated=True, config_options=('select = ["PDF300"]',)), path=str(tmp_path))
    overridden = _loaded_profile(tmp_path, select=("PDF300",))
    inline_rules = rules_selection.select_rules(inline.settings, profile=inline).for_path(str(target))
    overridden_rules = rules_selection.select_rules(overridden.settings, profile=overridden).for_path(str(target))

    assert tuple(rule.rule.code.tag for rule in inline_rules) == tuple(rule.rule.code.tag for rule in overridden_rules) == ("PDF300",)
    assert inline_rules[0].enabled_priority != overridden_rules[0].enabled_priority
    assert cache_fingerprint.selected_rules_key(inline_rules) == cache_fingerprint.selected_rules_key(overridden_rules)
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(inline), inline_rules)[1]
        == cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(overridden), overridden_rules)[1]
    )


def test_fixability_does_not_change_rule_or_analysis_keys(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    base = _loaded_profile(tmp_path, select=("PDF300",))
    unfixable = _loaded_profile(tmp_path, select=("PDF300",), unfixable=("PDF300",))
    base_rules = rules_selection.select_rules(base.settings, profile=base).for_path(str(target))
    unfixable_rules = rules_selection.select_rules(unfixable.settings, profile=unfixable).for_path(str(target))

    assert tuple(rule.rule.code.tag for rule in base_rules) == tuple(rule.rule.code.tag for rule in unfixable_rules) == ("PDF300",)
    assert base_rules[0].fixable
    assert not unfixable_rules[0].fixable
    assert cache_fingerprint.selected_rules_key(base_rules) == cache_fingerprint.selected_rules_key(unfixable_rules)
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(base), base_rules)[1]
        == cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(unfixable), unfixable_rules)[1]
    )


def test_different_final_ordered_rule_codes_change_rule_and_analysis_keys(tmp_path: Path) -> None:
    target = tmp_path / "module.py"
    first = _loaded_profile(tmp_path, select=("PDF300",))
    second = _loaded_profile(tmp_path, select=("PDF301",))
    first_rules = rules_selection.select_rules(first.settings, profile=first).for_path(str(target))
    second_rules = rules_selection.select_rules(second.settings, profile=second).for_path(str(target))
    combined_rules = (*first_rules, *second_rules)

    assert cache_fingerprint.selected_rules_key(first_rules) != cache_fingerprint.selected_rules_key(second_rules)
    assert cache_fingerprint.selected_rules_key(combined_rules) != cache_fingerprint.selected_rules_key(tuple(reversed(combined_rules)))
    assert (
        cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(first), first_rules)[1]
        != cache_fingerprint.analysis_fingerprint(settings_check.analysis_settings_identity(second), second_rules)[1]
    )


def test_path_keys_relocate_with_project_and_external_paths_do_not(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first_context = SourcePathContext.for_path(str(first_root / "package" / "module.py"))
    second_context = SourcePathContext.for_path(str(second_root / "package" / "module.py"))

    assert cache_fingerprint.PathFingerprintBuilder(str(first_root)).fingerprints(first_context)[0] == cache_fingerprint.PathFingerprintBuilder(str(second_root)).fingerprints(second_context)[0]
    other_builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path / "other"))
    assert other_builder.fingerprints(first_context)[0] != other_builder.fingerprints(second_context)[0]


def test_path_builder_is_deterministic_across_path_and_package_semantics(tmp_path: Path) -> None:
    project = tmp_path / "project"
    package = project / "_private_package"
    nested = package / "public_nested"
    external = tmp_path / "external"
    nested.mkdir(parents=True)
    external.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (nested / "__init__.pyi").write_text("", encoding="utf-8")
    paths = (project / "root_module.py", nested / "public_module.py", nested / "_private_module.py", nested / "__init__.py", external / "external_module.py")
    for path in paths:
        path.write_text("", encoding="utf-8")
    missing = nested / "missing.py"
    broken = project / "broken.py"
    try:
        broken.symlink_to(project / "absent.py")
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    contexts = tuple(SourcePathContext.for_path(str(path)) for path in (*paths, missing, broken, Path(os.path.abspath(os.sep))))
    for context in contexts:
        first = cache_fingerprint.PathFingerprintBuilder(str(project / "nested" / "..")).fingerprints(context)
        second = cache_fingerprint.PathFingerprintBuilder(str(project)).fingerprints(context)
        assert first == second


def test_path_builder_distinguishes_symlink_aliases_and_handles_json_escaping(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    target = real / 'quoted"\\module.py'
    target.write_text("", encoding="utf-8")
    aliases = (tmp_path / "first_alias.py", tmp_path / "second_alias.py")
    try:
        for alias in aliases:
            alias.symlink_to(target)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    contexts = tuple(SourcePathContext.for_path(str(alias)) for alias in aliases)
    builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path))

    assert contexts[0].resolved_path == contexts[1].resolved_path
    assert builder.fingerprints(contexts[0])[0] != builder.fingerprints(contexts[1])[0]
    assert builder.fingerprints(contexts[0])[1] != builder.fingerprints(contexts[1])[1]


def test_path_builder_preserves_relocated_project_identity(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_target = first_root / "package" / "module.py"
    second_target = second_root / "package" / "module.py"
    first_target.parent.mkdir(parents=True)
    second_target.parent.mkdir(parents=True)
    first_target.write_text("", encoding="utf-8")
    second_target.write_text("", encoding="utf-8")
    first_context = SourcePathContext.for_path(str(first_target))
    second_context = SourcePathContext.for_path(str(second_target))

    first_keys = cache_fingerprint.PathFingerprintBuilder(str(first_root)).fingerprints(first_context)
    second_keys = cache_fingerprint.PathFingerprintBuilder(str(second_root)).fingerprints(second_context)

    assert first_keys == second_keys


def test_path_builder_preserves_commonpath_failure_fallback(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("", encoding="utf-8")
    context = SourcePathContext.for_path(str(target))
    expected = cache_fingerprint.PathFingerprintBuilder(str(tmp_path)).fingerprints(context)
    commonpath = mocker.patch("pydocformatter.cache.fingerprint.os.path.commonpath", side_effect=ValueError("different drives"), autospec=True)

    actual = cache_fingerprint.PathFingerprintBuilder(str(tmp_path)).fingerprints(context)

    assert actual != expected
    assert commonpath.call_count >= 1


def test_path_builder_matches_pure_helpers_when_context_path_is_project_root(tmp_path: Path) -> None:
    context = SourcePathContext.for_path(str(tmp_path))
    builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path))

    assert builder.fingerprints(context)[0] == '["project-relative","."]'


def test_path_builder_normalizes_the_project_root_once(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text("", encoding="utf-8")
    normalize = mocker.spy(cache_fingerprint, "_normalize_absolute_path")

    builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path / "."))
    for target in targets:
        builder.fingerprints(SourcePathContext.for_path(str(target)))

    normalize.assert_called_once_with(str(tmp_path / "."))


def test_path_builder_reuses_lexical_encoding_for_equal_resolved_paths(tmp_path: Path, mocker: MockerFixture) -> None:
    target = tmp_path / "module.py"
    target.write_text("", encoding="utf-8")
    context = SourcePathContext.for_path(str(target))
    assert context.lexical_path == context.resolved_path
    builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path))
    canonical_path = mocker.spy(builder, "_canonical_path")

    builder.fingerprints(context)

    canonical_path.assert_called_once_with(context.lexical_path)


def test_path_builder_reuses_canonical_parent_encoding_for_siblings(tmp_path: Path, mocker: MockerFixture) -> None:
    targets = (tmp_path / "first.py", tmp_path / "second.py")
    for target in targets:
        target.write_text("", encoding="utf-8")
    builder = cache_fingerprint.PathFingerprintBuilder(str(tmp_path))
    encode_absolute = mocker.spy(cache_fingerprint, "_canonical_absolute_path")

    for target in targets:
        builder.fingerprints(SourcePathContext.for_path(str(target)))

    encode_absolute.assert_called_once_with(os.path.normcase(os.path.abspath(tmp_path)), os.path.normcase(os.path.abspath(tmp_path)))


def test_implementation_source_digest_changes_for_tree_mutations(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    first = package / "first.py"
    first.write_text("value = 1\n", encoding="utf-8")
    original = cache_fingerprint.implementation_source_digest(package)

    first.write_text("value = 2\n", encoding="utf-8")
    changed = cache_fingerprint.implementation_source_digest(package)
    first.rename(package / "renamed.py")
    renamed = cache_fingerprint.implementation_source_digest(package)
    (package / "added.py").write_text("value = 3\n", encoding="utf-8")
    added = cache_fingerprint.implementation_source_digest(package)
    (package / "renamed.py").unlink()
    removed = cache_fingerprint.implementation_source_digest(package)

    assert len({original, changed, renamed, added, removed}) == 5


def test_implementation_source_digest_tracks_symlink_file_target_identity_and_content(tmp_path: Path) -> None:
    package = tmp_path / "package"
    targets = tmp_path / "targets"
    package.mkdir()
    targets.mkdir()
    first_target = targets / "first.py"
    second_target = targets / "second.py"
    first_target.write_text("value = 1\n", encoding="utf-8")
    second_target.write_text("value = 1\n", encoding="utf-8")
    source = package / "module.py"
    try:
        source.symlink_to(first_target)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    first = cache_fingerprint.implementation_source_digest(package)
    source.unlink()
    source.symlink_to(second_target)
    retargeted = cache_fingerprint.implementation_source_digest(package)
    second_target.write_text("value = 2\n", encoding="utf-8")
    changed = cache_fingerprint.implementation_source_digest(package)

    assert first is not None
    assert len({first, retargeted, changed}) == 3


def test_implementation_source_digest_follows_directory_symlinks_and_preserves_aliases(tmp_path: Path) -> None:
    package = tmp_path / "package"
    target = tmp_path / "target"
    package.mkdir()
    target.mkdir()
    (target / "module.py").write_text("value = 1\n", encoding="utf-8")
    aliases = (package / "first", package / "second")
    try:
        for alias in aliases:
            alias.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    with_aliases = cache_fingerprint.implementation_source_digest(package)
    aliases[1].unlink()
    with_one_alias = cache_fingerprint.implementation_source_digest(package)

    assert with_aliases is not None
    assert with_one_alias is not None
    assert with_aliases != with_one_alias


def test_implementation_source_digest_supports_symlinked_package_root(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    source = package / "module.py"
    source.write_text("value = 1\n", encoding="utf-8")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(package, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    original = cache_fingerprint.implementation_source_digest(alias)
    source.write_text("value = 2\n", encoding="utf-8")
    changed = cache_fingerprint.implementation_source_digest(alias)

    assert original is not None
    assert changed is not None
    assert original != changed


def test_implementation_source_digest_fails_closed_for_relevant_broken_links_and_cycles(tmp_path: Path) -> None:
    broken_package = tmp_path / "broken-package"
    cyclic_package = tmp_path / "cyclic-package"
    broken_package.mkdir()
    cyclic_package.mkdir()
    try:
        (broken_package / "module.py").symlink_to(tmp_path / "missing.py")
        (cyclic_package / "module.py").write_text("value = 1\n", encoding="utf-8")
        (cyclic_package / "loop").symlink_to(cyclic_package, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")

    assert cache_fingerprint.implementation_source_digest(broken_package) is None
    assert cache_fingerprint.implementation_source_digest(cyclic_package) is None


class _ManifestPath:
    """Distribution manifest path with recorded hash and size metadata."""

    def __init__(self, path: str, *, algorithm: str = "sha256", encoded_hash: str = "YWJj", size: int | None = 3) -> None:
        self.path = path
        self.hash = importlib.metadata.FileHash(f"{algorithm}={encoded_hash}")
        self.size = size

    def __str__(self) -> str:
        return self.path


class _Distribution:
    """Minimal distribution metadata view used by artifact identity tests."""

    def __init__(self, files: tuple[_ManifestPath, ...] | None, *, direct_url: str | None = None, version: str = "1.2.3", package_root: Path | None = None) -> None:
        self.files = files
        self.direct_url = direct_url
        self.version = version
        self.package_root = Path(pydocformatter.__file__).parent if package_root is None else package_root

    def read_text(self, filename: str) -> str | None:
        return self.direct_url if filename == "direct_url.json" else None

    def locate_file(self, path: str) -> Path:
        assert path == "pydocformatter"
        return self.package_root


def test_installed_wheel_uses_sorted_hashed_manifest_without_reading_sources(mocker: MockerFixture) -> None:
    first = _Distribution((_ManifestPath("pydocformatter/z.py", encoded_hash="eno"), _ManifestPath("pydocformatter/a.py", encoded_hash="dHdv", size=7), _ManifestPath("metadata.txt")))
    second = _Distribution(tuple(reversed(first.files or ())))
    distribution = mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.distribution", side_effect=(first, second), autospec=True)
    source_identity = mocker.patch("pydocformatter.cache.fingerprint.implementation_source_digest", side_effect=AssertionError("wheel identity must not read package sources"), autospec=True)
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.version", return_value="2.0.0", autospec=True)

    first_engine = cache_fingerprint.engine_fingerprint()
    second_engine = cache_fingerprint.engine_fingerprint()

    assert first_engine is not None
    assert second_engine is not None
    assert first_engine == second_engine
    assert first_engine[0].implementation_digest == second_engine[0].implementation_digest
    assert first_engine[0].distribution_version == "1.2.3"
    assert distribution.call_count == 2
    source_identity.assert_not_called()


def test_manifest_from_a_different_install_falls_back_to_imported_source_identity(tmp_path: Path, mocker: MockerFixture) -> None:
    expected = b"s" * 32
    distribution = _Distribution((_ManifestPath("pydocformatter/module.py"),), package_root=tmp_path / "stale-install" / "pydocformatter")
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.distribution", return_value=distribution, autospec=True)
    source_identity = mocker.patch("pydocformatter.cache.fingerprint.implementation_source_digest", return_value=expected, autospec=True)
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.version", side_effect=lambda name: "1.2.3" if name == "pydocformatter" else "2.0.0", autospec=True)

    engine, _ = cache_fingerprint.engine_fingerprint()

    assert engine.implementation_digest == expected
    source_identity.assert_called_once_with(None)


@pytest.mark.parametrize(
    "distribution",
    [
        _Distribution((_ManifestPath("pydocformatter/module.py"),), direct_url='{"url":"file:///source","dir_info":{"editable":true}}'),
        _Distribution(None),
        _Distribution((_ManifestPath("pydocformatter/module.py", size=None),)),
        _Distribution((_ManifestPath("pydocformatter/module.py"),), direct_url="not-json"),
        _Distribution((_ManifestPath("metadata.txt"),)),
        _Distribution((_ManifestPath("pydocformatter/../module.py"),)),
        _Distribution((_ManifestPath("pydocformatter/module.py"), _ManifestPath("pydocformatter/module.py"))),
    ],
    ids=("editable", "missing-manifest", "missing-size", "malformed-direct-url", "empty-package-manifest", "malformed-package-path", "duplicate-package-path"),
)
def test_editable_and_malformed_installs_fall_back_to_complete_source_identity(distribution: _Distribution, mocker: MockerFixture) -> None:
    expected = b"s" * 32
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.distribution", return_value=distribution, autospec=True)
    source_identity = mocker.patch("pydocformatter.cache.fingerprint.implementation_source_digest", return_value=expected, autospec=True)
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.version", side_effect=lambda name: "1.2.3" if name == "pydocformatter" else "2.0.0", autospec=True)

    result = cache_fingerprint.engine_fingerprint()

    assert result is not None
    assert result[0].implementation_digest == expected
    source_identity.assert_called_once_with(None)


def test_artifact_manifest_identity_changes_for_every_recorded_component(mocker: MockerFixture) -> None:
    distributions = (
        _Distribution((_ManifestPath("pydocformatter/module.py"),)),
        _Distribution((_ManifestPath("pydocformatter/renamed.py"),)),
        _Distribution((_ManifestPath("pydocformatter/module.py", algorithm="sha512"),)),
        _Distribution((_ManifestPath("pydocformatter/module.py", encoded_hash="ZGVm"),)),
        _Distribution((_ManifestPath("pydocformatter/module.py", size=4),)),
    )
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.distribution", side_effect=distributions, autospec=True)

    identities = tuple(cache_fingerprint._installed_artifact_identity() for _ in distributions)

    assert all(identity is not None for identity in identities)
    assert len({identity[0] for identity in identities if identity is not None}) == len(distributions)


def test_engine_key_changes_for_all_declared_identity_components(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "module.py").write_text("value = 1\n", encoding="utf-8")
    result = cache_fingerprint.engine_fingerprint(package)
    assert result is not None
    engine, key = result
    variants: tuple[EngineFingerprint, ...] = (
        dataclasses.replace(engine, protocol_version=CACHE_PROTOCOL_VERSION + 1),
        dataclasses.replace(engine, schema_version=CACHE_SCHEMA_VERSION + 1),
        dataclasses.replace(engine, distribution_version=engine.distribution_version + ".changed"),
        dataclasses.replace(engine, implementation_digest=b"x" * 32),
        dataclasses.replace(engine, filelock_version=engine.filelock_version + ".changed"),
        dataclasses.replace(engine, libcst_version=engine.libcst_version + ".changed"),
        dataclasses.replace(engine, python_implementation=engine.python_implementation + "-changed"),
        dataclasses.replace(engine, python_cache_tag=(engine.python_cache_tag or "") + "-changed"),
        dataclasses.replace(engine, python_version=(*engine.python_version, "changed")),
        dataclasses.replace(engine, os_name=engine.os_name + "-changed"),
        dataclasses.replace(engine, platform=engine.platform + "-changed"),
        dataclasses.replace(engine, byteorder="changed"),
        dataclasses.replace(engine, architecture=("changed", "changed")),
        dataclasses.replace(engine, line_separator=engine.line_separator + "changed"),
    )

    assert all(cache_fingerprint.canonical_digest(variant) != key for variant in variants)


def test_engine_fingerprint_fails_closed_when_source_cannot_be_enumerated_or_read(tmp_path: Path, mocker: MockerFixture) -> None:
    missing = tmp_path / "missing"
    package = tmp_path / "package"
    package.mkdir()
    (package / "module.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(cache_fingerprint.CacheFingerprintError):
        cache_fingerprint.engine_fingerprint(missing)
    mocker.patch("pathlib.Path.read_bytes", side_effect=OSError("denied"), autospec=True)
    with pytest.raises(cache_fingerprint.CacheFingerprintError):
        cache_fingerprint.engine_fingerprint(package)


def test_engine_fingerprint_fails_closed_when_runtime_identity_is_unavailable(tmp_path: Path, mocker: MockerFixture) -> None:
    package = tmp_path / "package"
    package.mkdir()
    (package / "module.py").write_text("value = 1\n", encoding="utf-8")
    mocker.patch("pydocformatter.cache.fingerprint.importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("metadata unavailable"), autospec=True)

    with pytest.raises(cache_fingerprint.CacheFingerprintError):
        cache_fingerprint.engine_fingerprint(package)


def test_direct_runtime_dependency_inventory_is_fingerprinted() -> None:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependency_names = {dependency.split(">", 1)[0].split("=", 1)[0].lower() for dependency in project["dependencies"]}

    assert dependency_names == {"filelock", "libcst"}
    assert {"filelock_version", "libcst_version"} <= {field.name for field in dataclasses.fields(EngineFingerprint)}
