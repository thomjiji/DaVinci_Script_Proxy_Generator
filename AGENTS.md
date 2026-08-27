## Python Constraint

Resolve's `fusionscript` binding requires a **system** (python.org) CPython —
uv-managed interpreters silently fail to connect, hence
`python-preference = "only-system"`.

## Releases

Versions are monotonically increasing release identifiers, not Semantic Versioning compatibility promises.

- Increment the third number for routine releases, including fixes, small features, and scoped behavior changes.
- Increment the second number for larger feature batches.
- Increment the first number only when the maintainer explicitly declares a new project era. Breaking changes do not automatically require it; call them out in the release notes instead.
- `hatch-vcs` derives the version from git tags; do not edit a version string in source code.
- Release useful accumulated work with `git tag vX.Y.Z` followed by `git push origin vX.Y.Z`; the tag workflow builds and publishes the GitHub Release artifacts.
