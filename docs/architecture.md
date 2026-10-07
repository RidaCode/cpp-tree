# Architecture

The installed executable is a Python zipapp containing the package, curriculum,
and license notices. It imports the same modules as `python3 -m cpp_tree` in the
checkout. Python's standard library provides everything needed at runtime.

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `models.py` | Typed curriculum, CLI options, modal, and saved-state shapes |
| `curriculum.py` + `data/learncpp.json` | Validate/load the outline and provide chapter/lesson indexes |
| `paths.py` | Resolve the legacy XDG progress location |
| `storage.py` | Validate profiles, acquire one writer lock, atomically save/backup; read-only snapshots |
| `app.py` | Navigation, completion/undo, notes, search, quest pins, and save coordination |
| `views.py` | Render tree/cards/dialogs from application state |
| `canvas.py` + `text.py` + `theme.py` | Character grid, display sanitization, colors, and ASCII alternatives |
| `terminal.py` | Curses input, resizing, and truecolor/indexed output |
| `browser.py` | Validate a LearnCpp URL and launch a desktop opener asynchronously |
| `cli.py` + `__main__.py` | Environment checks, arguments, summaries, and application lifecycle |
| `installation.py` | Recognize managed executables, replace one atomically, and uninstall it |
| `scripts/build.py` + `scripts/install.py` | Build the executable; install it in a user-selected directory |

Rendering never writes files or terminal output. It does update display bookkeeping
such as scroll offsets and the current grid width. The terminal loop consumes the
canvas; `scripts/render_preview.py` uses the same canvas for documentation.

`App` owns the in-memory interaction state. Mutation methods call `save()` and roll
back if writing progress fails. Completion history is kept in memory for this
session. Notes are committed explicitly with `Ctrl-S`.

## Data contract

State format version **1** is intentionally unchanged. Lesson keys look like
`4:4.9`; note keys look like `lesson:4:4.9` or `chapter:4`. Unknown completed IDs,
note keys, and top-level extension fields survive saves so changing an outline
does not silently erase old data. Optional view preferences can be normalized.
Unsupported state versions and malformed progress are rejected, not reset.

Saving writes the previous file to `.bak`, writes a temporary new file, flushes it,
and replaces the target atomically. The backup is one previous save, not a journal.
The app keeps an advisory `flock` for the profile's lifetime; an OS-released lock
can leave its empty `.lock` file behind. `--summary` reads an atomic snapshot without
locking or writing. These semantics assume a local filesystem with working locks
and atomic rename; sharing a live profile over a network filesystem is not supported.

`stream.txt` is derived output, not authoritative state. A failure to update it
must not undo a successful progress save. Profiles in the same directory would
share that file, so document separate directories for separate profiles.

## Curriculum changes

The outline carried over from the original script has 35 chapter records and 356
lesson records. It is not downloaded at runtime. Edit the JSON directly; the loader
checks required fields, groups, key consistency, duplicate IDs, and HTTPS article
URLs. Live link freshness is a separate review task; schema validation does not
prove that a URL currently responds or that the outline is up to date.

Short chapter names are presentation hints in `curriculum.py`. The UI falls back
to the full title when a hint is absent. Changing a saved lesson key requires a
migration strategy and regression tests. Avoid churn in IDs merely to match a
renumbering on the website.

## Distribution

`build.py` allowlists Python/JSON package files and license notices, excludes bytecode,
and uses fixed archive timestamps. Equivalent inputs produce identical archives
on the same Python/zlib toolchain. `install.py` smoke-tests the archive before
replacing the installed executable. The archive carries a small format marker;
only a regular file with this marker is eligible for managed replacement/removal.
That marker identifies an installation; it is not a signature or proof of trust.

The bootstrap accepts `CPP_TREE_REPO` (default `RidaCode/cpp-tree`), `CPP_TREE_REF`
(default `main`), `CPP_TREE_BIN_DIR`, and, for offline tests, `CPP_TREE_ARCHIVE`.
It extracts only expected application/build files and rejects traversal, links,
duplicate selected paths, and oversized selected contents.

The package metadata also supports normal pip installation. The managed uninstaller
refuses to remove pip/pipx entry points: their package manager owns those installs.
