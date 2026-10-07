# Contributing

Thanks for helping make C++ Talent Tree easier to use. Documentation, link fixes,
and clear bug reports are useful contributions; you do not need to change Python
code to help.

## Scope

This project is a lightweight, offline LearnCpp progress tracker for the terminal.
We want reliable saves, good keyboard navigation, and a useful streaming view.
Keep runtime dependencies at zero unless a proposed change has a clear benefit
that has been discussed first. Accounts, cloud sync, and copying course material
are outside the current scope.

## Report a problem

Search existing issues, then use the bug report form. Include your OS, Python
version, terminal, app version, and a short sequence that reproduces the issue.
Screenshots help with layout bugs. Remove personal notes and paths before posting;
a synthetic `--demo` reproduction is preferred when it shows the same problem.

For security issues, follow [SECURITY.md](SECURITY.md). For conduct concerns, see
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Work on a change

1. Fork and clone the repository; create a branch for your change.
2. Run the app with `python3 -m cpp_tree --demo` from the repository root.
3. Make one focused change. Open an issue first for a large change or a new runtime dependency.
4. Run the checks below and explain what changed and how you verified it in your PR.

No installation is required to run the source or standard-library tests:

```sh
python3 -m unittest discover -s tests -v
```

For the formatter and linter, use an isolated development environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
```

Use `ruff check --fix .` and `ruff format .` when needed. The project targets Python
3.10+ and uses type annotations for module boundaries. Prefer small functions,
explicit inputs, and comments that explain a constraint or an edge case.

## Verify the behavior you changed

- **Saves:** check an existing version-1 profile, not only a blank one. Preserve
  unknown completed IDs, notes, and extension fields. Never silently reset data.
- **Input/UI:** try both the minimum 72×22 terminal size and a larger window; test
  search, notes, `--ascii`, and stream view if your change touches rendering.
- **Installer:** use a temporary `--bin-dir`; verify update and uninstall preserve
  state and refuse to replace unrelated executables.
- **Curriculum:** validate IDs, titles, groups, and URLs. Lesson keys are saved IDs,
  so changing them requires a deliberate migration. Do not copy tutorial bodies.

Add regression tests for a bug fix or risky behavior change. Documentation-only
changes generally do not need new tests. Tests must work without the network.

Build the distributable executable to catch missing resources:

```sh
python3 scripts/build.py
python3 dist/cpp-tree.pyz --demo --summary
```

The PR workflow checks formatting, Linux/macOS terminal behavior, packaging, and
Python versions. A green workflow is required before merging. Maintainer review
considers correctness, save compatibility, scope, and clarity. Response times are
not guaranteed; avoid repeatedly pinging a thread.

## Screenshots

The README image is rendered from the actual demo canvas. To regenerate it, install
the optional `Pillow` package in your development environment and provide a
monospace font:

```sh
python3 -m pip install Pillow
python3 scripts/render_preview.py --font /path/to/monospace.ttf
```

## Credit and licensing

Contributions are accepted under the project's [MIT License](LICENSE). Submit only
material you have permission to contribute, and retain third-party attribution.
Be respectful and follow the [code of conduct](CODE_OF_CONDUCT.md).
