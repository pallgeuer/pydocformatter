# Releasing pydocformatter

This runbook covers a complete pydocformatter release from preparation through verification. Follow it in order and keep the release commit, command output, artifact checksums, and published URLs as the release record.

A release is complete only when the same version and commit are represented by the Git tag, GitHub release, PyPI distributions, changelog, and package metadata. Never rebuild or replace an artifact after any file for that version has been published.

## Release model and sources of truth

Releases are prepared, validated, and committed directly on a clean, current `main` checkout, then published manually after the pushed commit passes GitHub Actions. GitHub Actions validates the project and deploys the documentation site from `main`; it does not publish the package or create the GitHub release.

| Item                     | Source of truth                                                                                                              |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------|
| Package version          | `src/pydocformatter/_version.py`                                                                                             |
| Release tag              | `v<package-version>`                                                                                                         |
| Release notes and date   | `CHANGELOG.md`                                                                                                               |
| Package metadata         | `pyproject.toml`                                                                                                             |
| Locked development tools | `uv.lock`                                                                                                                    |
| Build configuration      | `[build-system]` and `[tool.hatch.*]` in `pyproject.toml`                                                                    |
| Published artifacts      | `pydocformatter-<version>.tar.gz` and `pydocformatter-<version>-py3-none-any.whl`                                            |
| CI and docs deployment   | `.github/workflows/pre_commit_checks.yml` and `.github/workflows/build_deploy_docs.yml`                                      |
| Pre-commit hooks         | `.pre-commit-hooks.yaml`                                                                                                     |
| Release destinations     | [PyPI](https://pypi.org/project/pydocformatter/) and [GitHub Releases](https://github.com/pallgeuer/pydocformatter/releases) |

The current versioning policy is documented in [Versioning](docs_site/versioning.md). Development setup and the normal quality workflow are documented in [Contributing](CONTRIBUTING.md).

## Before starting

The releaser needs:

- Permission to push directly to `main` and push tags to `pallgeuer/pydocformatter`.
- Permission to create GitHub releases and a working authenticated GitHub CLI.
- A project-scoped PyPI API token with upload permission for `pydocformatter`.
- Git, uv, Python 3.11 or newer, and the locked development environment described in [Contributing](CONTRIBUTING.md#development-setup).

Use one shell session for the commands below, or restore the variables whenever opening a new one. Replace the example version with the intended release version:

```bash
git fetch origin --tags
VERSION=1.0.0
TAG="v${VERSION}"
PREVIOUS_TAG="$(git describe --tags --abbrev=0 origin/main)"
PREVIOUS_VERSION="${PREVIOUS_TAG#v}"
RELEASE_DATE="$(date +%F)"
```

Confirm the values before continuing:

```bash
printf 'Version: %s\nTag: %s\nPrevious tag: %s\nRelease date: %s\n' "$VERSION" "$TAG" "$PREVIOUS_TAG" "$RELEASE_DATE"
```

Choose the version according to semantic versioning and the compatibility policy. Confirm that it is greater than `PREVIOUS_VERSION`, is not already present in the [PyPI release history](https://pypi.org/project/pydocformatter/#history), and has no local or remote tag:

```bash
git fetch origin --tags
git tag --list "$TAG"
git ls-remote --tags origin "refs/tags/${TAG}"
```

Both tag commands must produce no output for a new release. Stop if the version or tag already exists; published versions and public tags must not be reused or moved.

## Prepare the release on main

Start from an up-to-date, clean `main` checkout:

```bash
git switch main
git pull --ff-only origin main
test -z "$(git status --porcelain)"
uv sync --locked --no-default-groups --group dev
gh auth status
```

### Update the version and release references

- Set `__version__` in `src/pydocformatter/_version.py` to `VERSION`.
- Review every intentional reference to the previous and new versions. Historical changelog entries stay unchanged; current pre-commit examples, rule stability metadata, and release links must refer to the appropriate version.
- Update Python-version classifiers, the minimum Python version, dependencies, project URLs, license metadata, hook definitions, and build inclusions or exclusions if the release changed any of them.
- Run `uv lock` and commit `uv.lock` if dependency or lock-relevant project metadata changed. A version-only edit to the dynamic version file does not currently change `uv.lock`.

Use these searches as an audit, not as a blind replacement:

```bash
rg -n --fixed-strings "$PREVIOUS_VERSION" --glob '!CHANGELOG.md'
rg -n --fixed-strings "$VERSION"
rg -n 'stable_since|requires-python|Programming Language :: Python|license|project.scripts|repo: https://github.com/pallgeuer/pydocformatter' pyproject.toml src docs_site docs README.md .pre-commit-hooks.yaml .pre-commit-config.yaml
```

### Finalize the changelog

Rewrite the release notes compactly for external users rather than preserving the development diary. The version section must describe the final shipped state, including all material features, fixes, compatibility changes, and migrations, while omitting implementation churn, superseded intermediate behavior, test-only work, and stale changes to code that no longer exists.

- Move the relevant `Unreleased` material under `## v<VERSION>` and add `Released YYYY-MM-DD` using `RELEASE_DATE`.
- Put breaking changes and their replacements where users will see them clearly.
- Keep the standard `Added`, `Changed`, `Fixed`, and `Removed` categories only where they contain useful entries.
- Set the new `## Unreleased` section to `None.`. The next user- or developer-relevant change replaces `None.` with the appropriate category and entry.
- Point the `Unreleased` comparison at `v<VERSION>...HEAD` and add the release comparison from `PREVIOUS_TAG` to `TAG`.
- Make the version section suitable for copying verbatim into the GitHub release notes.

`RELEASE_DATE` is the intended publication date. If publication moves to another day, update the changelog date on `main`, rerun the affected release checks, commit and push the correction, and wait for its workflows before tagging.

### Review user-facing documentation

- Confirm that the README quick start, help links, installation guidance, examples, badges, and pre-commit examples match the released CLI and hooks.
- Confirm that the documentation site covers new or changed commands, settings, rule behavior, migration requirements, and supported platforms.
- Confirm that every added or changed rule has accurate adjacent documentation, stability metadata for this version, and executable examples.
- Confirm that `CONTRIBUTING.md`, this runbook, and public specifications still match the repository workflow.

### Run the release checks

Run the locked-environment check and the complete local CI-equivalent suite. Pre-commit may apply formatting fixes, so inspect those changes and rerun it until it exits successfully without changing files:

```bash
uv lock --check
uv run pre-commit run --all-files --show-diff-on-failure
git diff --check
git status --short
```

Generate and build the documentation sequentially because the build consumes the tree refreshed by the generator:

```bash
rm -rf -- .generated site zensical.generated.toml
uv run python tools/docs/generate_zensical.py
uv run zensical build --clean --strict -f zensical.generated.toml
```

Confirm the CLI version and its primary help surfaces:

```bash
test "$(uv run pydocfmt --version)" = "pydocfmt ${VERSION}"
uv run pydocfmt --help
uv run pydocfmt check --help
uv run pydocfmt config --help
uv run pydocfmt rule --help
```

### Build and inspect candidate artifacts

Build from a clean output directory and assign the exact expected paths:

```bash
uv build --clear
SDIST_NAME="pydocformatter-${VERSION}.tar.gz"
WHEEL_NAME="pydocformatter-${VERSION}-py3-none-any.whl"
SDIST="dist/${SDIST_NAME}"
WHEEL="dist/${WHEEL_NAME}"
test -f "$SDIST"
test -f "$WHEEL"
uv run twine check "$SDIST" "$WHEEL"
```

Inspect both file lists. The wheel should contain the importable package, rule documentation required by the CLI, metadata, and licenses, but not source-only rule templates. The source distribution should contain the files needed to build, document, and test the project, including the root pytest configuration and test suite, but not excluded CI or agent configuration.

```bash
uv run python -m zipfile -l "$WHEEL"
uv run python -m tarfile -l "$SDIST"
```

Smoke-test the wheel and source distribution independently in isolated environments:

```bash
test "$(uvx --isolated --from "./${WHEEL}" pydocfmt --version)" = "pydocfmt ${VERSION}"
printf '%s\n' '"""Package metadata."""' | uvx --isolated --from "./${WHEEL}" pydocfmt --isolated check -
test "$(uvx --isolated --from "./${SDIST}" pydocfmt --version)" = "pydocfmt ${VERSION}"
printf '%s\n' '"""Package metadata."""' | uvx --isolated --from "./${SDIST}" pydocfmt --isolated check -
```

Every version command must report `VERSION`, and both checks must report `All checks passed!`.

### Commit and push the release changes

Review the complete patch and stage only intended files:

```bash
git diff --stat
git diff
git status --short
git add --patch
git diff --cached --check
git diff --cached
git commit -m "Prepare ${TAG} release"
RELEASE_COMMIT="$(git rev-parse HEAD)"
git push origin main
test "$RELEASE_COMMIT" = "$(git rev-parse origin/main)"
printf 'Release commit: %s\n' "$RELEASE_COMMIT"
```

Record `RELEASE_COMMIT` and the exact checks run in the maintainer record. Successful commands need only be marked as passed; include full output only for a warning, failure, skipped check, or other result that needs explanation.

- Confirm that `RELEASE_COMMIT` is the intended release commit at the tip of `main`.
- Do not publish the candidate artifacts built before the commit; rebuild from the exact pushed commit below.

## Publish the release

Publishing is irreversible once any distribution reaches PyPI. Work through this section without changing commits, versions, or artifacts.

### Confirm the release commit

Update the local checkout and restore the release variables, including the recorded `RELEASE_COMMIT`, if necessary:

```bash
git switch main
git pull --ff-only origin main
git fetch origin --tags
test -z "$(git status --porcelain)"
test "$RELEASE_COMMIT" = "$(git rev-parse HEAD)"
test "$RELEASE_COMMIT" = "$(git rev-parse origin/main)"
test "$(uv run pydocfmt --version)" = "pydocfmt ${VERSION}"
```

Confirm that `CHANGELOG.md` contains the dated `v<VERSION>` notes, an empty `Unreleased` section, and the correct comparison links. Check the two workflows for `RELEASE_COMMIT` and wait until both have succeeded, including the documentation deployment from `main`:

```bash
gh run list --commit "$RELEASE_COMMIT" --limit 10
```

Do not continue while a workflow is queued, running, or unsuccessful.

### Rebuild the final artifacts

Build and validate once more from the exact release commit:

```bash
uv sync --locked --no-default-groups --group dev
uv lock --check
uv build --clear
SDIST_NAME="pydocformatter-${VERSION}.tar.gz"
WHEEL_NAME="pydocformatter-${VERSION}-py3-none-any.whl"
SDIST="dist/${SDIST_NAME}"
WHEEL="dist/${WHEEL_NAME}"
CHECKSUMS="/tmp/pydocformatter-${TAG}-SHA256SUMS"
RELEASE_NOTES="/tmp/pydocformatter-${TAG}-release-notes.md"
test -f "$SDIST"
test -f "$WHEEL"
uv run twine check "$SDIST" "$WHEEL"
uv run python -m zipfile -l "$WHEEL"
uv run python -m tarfile -l "$SDIST"
test "$(uvx --isolated --from "./${WHEEL}" pydocfmt --version)" = "pydocfmt ${VERSION}"
printf '%s\n' '"""Package metadata."""' | uvx --isolated --from "./${WHEEL}" pydocfmt --isolated check -
test "$(uvx --isolated --from "./${SDIST}" pydocfmt --version)" = "pydocfmt ${VERSION}"
printf '%s\n' '"""Package metadata."""' | uvx --isolated --from "./${SDIST}" pydocfmt --isolated check -
uv run la-dev-release-checksums --output "$CHECKSUMS" "$SDIST" "$WHEEL"
```

Inspect the final file lists against the same wheel and source-distribution inclusion criteria used for the candidate artifacts. Every version command must report `VERSION`, and both functional checks must report `All checks passed!`. The checksum generator removes any previous manifest before hashing and atomically writes and prints a new manifest only after reading both artifacts successfully. It exits unsuccessfully if either artifact or the manifest cannot be processed. The two manifest entries contain artifact basenames without a `dist/` prefix so that the manifest can be verified beside downloaded GitHub release assets.

Extract the version section for the GitHub release and inspect it before publishing:

```bash
awk -v heading="## v${VERSION}" '$0 == heading { copy = 1; next } copy && /^---$/ { exit } copy { print }' CHANGELOG.md > "$RELEASE_NOTES"
test -s "$RELEASE_NOTES"
cat "$RELEASE_NOTES"
```

Record the checksum output alongside `RELEASE_COMMIT` in the maintainer record.

### Create and push the tag

Create an annotated tag on the verified release commit, confirm its target, and push only that tag:

```bash
test -z "$(git tag --list "$TAG")"
git tag -a "$TAG" -m "pydocformatter ${TAG}" "$RELEASE_COMMIT"
test "$(git rev-list -n 1 "$TAG")" = "$RELEASE_COMMIT"
git push origin "$TAG"
```

From this point, do not amend, move, or replace the tag. If a code or artifact defect is discovered, follow the recovery guidance below.

### Publish to PyPI

Read the project-scoped PyPI token without putting it in shell history, export it for uv, and perform a dry run against the final files:

```bash
read -rsp 'PyPI token: ' UV_PUBLISH_TOKEN
printf '\n'
export UV_PUBLISH_TOKEN
uv publish --dry-run "$SDIST" "$WHEEL"
```

The dry run must identify exactly the wheel and source distribution for `VERSION`. Publish those same files. PyPI accepts an interrupted retry of the exact unchanged command and ignores files that were already uploaded with identical contents:

```bash
PUBLISH_STATUS=0
uv publish "$SDIST" "$WHEEL" || PUBLISH_STATUS=$?
unset UV_PUBLISH_TOKEN
(exit "$PUBLISH_STATUS")
```

Do not rebuild after this command. If it only partially succeeds, retain the exact local artifacts and follow [Recovery and resuming](#recovery-and-resuming).

### Create the GitHub release

Create a non-draft, non-prerelease GitHub release from the already pushed tag. Upload the exact PyPI artifacts and their checksum file:

```bash
gh release create "$TAG" "$SDIST" "$WHEEL" "$CHECKSUMS" --verify-tag --fail-on-no-commits --latest --title "pydocformatter ${TAG}" --notes-file "$RELEASE_NOTES"
gh release view "$TAG" --json tagName,name,isDraft,isPrerelease,isImmutable,publishedAt,url,assets
```

Confirm that the release targets `TAG`, is published as the latest stable release, contains the intended notes, and lists all three uploaded assets.

## Verify the published release

Allow a short period for PyPI and GitHub Pages propagation, then verify all public surfaces. Use explicit versions so cached or older installations cannot hide a problem.

### PyPI and installed CLI

- The [PyPI project page](https://pypi.org/project/pydocformatter/) shows `VERSION`, the correct metadata and rendered README, and both distributions.
- The wheel and source distribution filenames and hashes match the files that were published.
- A fresh isolated installation reports the released version and passes a basic check:

```bash
test "$(uvx --isolated --refresh-package pydocformatter --from "pydocformatter==${VERSION}" pydocfmt --version)" = "pydocfmt ${VERSION}"
printf '%s\n' '"""Package metadata."""' | uvx --isolated --refresh-package pydocformatter --from "pydocformatter==${VERSION}" pydocfmt --isolated check -
```

### GitHub and pre-commit

- The [GitHub release](https://github.com/pallgeuer/pydocformatter/releases) is visible, marked latest, and points to `RELEASE_COMMIT` through `TAG`.
- The release notes and assets are complete and the uploaded checksum file matches `CHECKSUMS`.
- The published check hook installs from the tag and passes against the repository:

```bash
uv run pre-commit try-repo https://github.com/pallgeuer/pydocformatter pydocfmt-check --ref "$TAG" --all-files
```

### Documentation and repository state

- The [documentation site](https://pallgeuer.github.io/pydocformatter/) reflects the release commit and all direct links from the README work.
- Both `main` workflow runs for `RELEASE_COMMIT` are successful and there are no unexpected release commits or generated files.
- `CHANGELOG.md` shows `None.` under `Unreleased`; the first later noteworthy change replaces it with a normal changelog category and entry.

The release is complete when every verification above passes. Link any follow-up issue from the release record rather than silently changing a published release.

## Recovery and resuming

First determine exactly which irreversible steps completed: remote tag, PyPI filenames, and GitHub release. Keep the original artifacts and checksum file until all destinations are verified.

| State                                            | Action                                                                                                                                                                                                     |
|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Failure before the tag is pushed                 | Fix the release preparation on `main`, rerun every affected check, commit and push the correction, record the new release commit, wait for its workflows, and rebuild. No public release state exists yet. |
| Tag pushed, nothing uploaded to PyPI             | Retry a transient operation against the unchanged tag and artifacts. If source must change, do not move a public tag; prepare a new version.                                                               |
| Only one PyPI distribution uploaded              | Do not rebuild. Confirm the uploaded filename and hash, then rerun `uv publish "$SDIST" "$WHEEL"` with the original files so PyPI ignores the identical existing file and uploads the missing one.         |
| PyPI complete, GitHub release missing            | Push the existing tag if necessary, then rerun `gh release create` with the original artifacts, checksum file, and release notes.                                                                          |
| GitHub release exists but an asset upload failed | Inspect whether the release is a draft. Resume or recreate the draft with the original assets. Never replace assets on an already published immutable release.                                             |
| A published artifact is defective                | PyPI files cannot be replaced. Consider yanking the affected release with an explanation, document the problem, and publish a corrected patch version.                                                     |
| Documentation deployment failed                  | Fix the documentation on `main` through the normal pull request workflow. Do not retag or republish an otherwise correct package.                                                                          |
| A credential may have been exposed               | Revoke it immediately, remove it from any logs or files where possible, rotate the credential, and audit the affected account.                                                                             |

When resuming on another machine, fetch the tag, verify its commit against the release record, retrieve the original artifacts from a trusted retained copy, and compare their SHA-256 hashes before continuing. Never infer success from a command that was interrupted; check PyPI and GitHub directly.
