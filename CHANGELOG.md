# Changelog

## 1.2.0 — Repository preparation

This version is prepared for publication; the tag/release is not created by these files.

### Added

- A modular Python package, separate curriculum JSON, and an executable zipapp build.
- A one-command bootstrap installer, local installer, and `cpp-tree --uninstall`.
- `--state-path` to locate the active profile without creating files.
- README preview, install/update/uninstall instructions, contributor and maintainer
  guides, an MIT license, attribution, conduct and security policies.
- Regression tests, a Linux/macOS CI matrix, issue forms, and a pull request template.

### Changed

- `--summary` is read-only and can run while the interactive app has the profile open.
- Invalid optional view preferences are normalized; malformed progress still fails
  visibly without overwriting it.
- The installer refuses to overwrite unrelated files or symlinks and preserves
  progress on update and uninstall.

### Compatibility

The original 1.1.6 script's lesson entries, version-1 saves, notes, pins, default
state location, key bindings, colors, and OBS `stream.txt` behavior are retained.

## 1.1.6 — Original script

Baseline version supplied as `cpp-tree-dev.py`. Earlier release history is not
reconstructed here.
