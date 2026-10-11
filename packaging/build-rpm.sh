#!/usr/bin/env bash
# Build the sdist and RPM packages. Bump the version in pyproject.toml and
# packaging/lithuanian-eid.spec before running. Extra args go to rpmbuild.
set -euo pipefail

cd "$(dirname "$0")/.."

SPEC=packaging/lithuanian-eid.spec
SOURCES_DIR="${HOME}/rpmbuild/SOURCES"

spec_version=$(sed -n 's/^Version:[[:space:]]*//p' "$SPEC" | head -n1)
project_version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -n1)

if [[ -z "$spec_version" || "$spec_version" != "$project_version" ]]; then
    echo "Version mismatch: spec=${spec_version:-?} pyproject.toml=${project_version:-?}" >&2
    exit 1
fi

tarball="lithuanian_eid-${spec_version}.tar.gz"

poetry build --format=sdist

if [[ ! -f "dist/${tarball}" ]]; then
    echo "Expected dist/${tarball} was not produced" >&2
    exit 1
fi

mkdir -p "$SOURCES_DIR"
install -m 644 "dist/${tarball}" "${SOURCES_DIR}/${tarball}"

rpmbuild -ba "$SPEC" "$@"
