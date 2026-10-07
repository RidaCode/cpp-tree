# Troubleshooting

## `cpp-tree: command not found`

Run `~/.local/bin/cpp-tree --version`. If that succeeds, add `~/.local/bin` to your
PATH as described in the README. If you chose `--bin-dir`, use that directory.
Run `type -a cpp-tree` to find old aliases, functions, or copies that take priority.

## Installer refuses to overwrite a file

This is intentional. Inspect the reported path. If it is your old standalone
tracker, close it and rename it as described in the README. A pip/pipx install
should be removed with that package manager before switching install methods.
Do not force replacement of an executable you do not recognize.

## Python or curses is unavailable

Check `python3 --version` and `python3 -c 'import curses, fcntl'`. Use Python 3.10+
with those standard-library modules. A minimal/custom Python build may omit
curses. On Windows, run the app inside WSL; a native Windows Python install will
not supply the required Unix terminal/locking behavior.

## Progress looks empty after an upgrade

Compare `cpp-tree --state-path` with the path used by your old script. A different
`XDG_STATE_HOME`, a different user account, or a missing custom `--state` argument
selects a different profile. The app does not automatically discover other saves.
Do not overwrite either profile while investigating.

## “Cannot lock progress”

Close the other instance using that profile, or use a different `--state` path.
Check that the directory is writable. An empty `.lock` file is normal and deleting
it while an instance is open can undermine locking; do not use deletion as a fix.
A crashed process releases its OS lock automatically.

## Malformed progress / restore a backup

The app leaves unreadable progress untouched. Close all instances first. These
commands locate your default active profile, preserve the current file, and
restore its previous-save backup with overwrite prompts:

```sh
state_path=$(cpp-tree --state-path)
cp -i -- "$state_path" "$state_path.before-restore"
cp -i -- "$state_path.bak" "$state_path"
cpp-tree --summary
```

For a custom profile, include the same `--state /path/to/progress.json` in the
first and last commands. Check that the backup exists and contains the data you
want before copying. A `.bak` file contains only the preceding save; it is not a
history of all your changes.

## Colors or borders look wrong

Try `cpp-tree --color 256` for a terminal that mishandles truecolor, or
`cpp-tree --color truecolor` if your terminal supports RGB but detection misses it.
For broken Unicode borders, use `--ascii`. A monospace font and a UTF-8 locale work
best. Emoji, double-width glyphs, and complex text shaping are not fully supported
by this one-character-per-cell renderer.

## The display asks me to resize

The minimum is 72 columns × 22 rows. Increase the window size or reduce terminal
font size. Controls other than quit pause while the terminal is too small. At
118 columns the app can show the detail sidebar.

## Browser does not open

The app uses `open` on macOS, then `xdg-open` or `gio` on other systems, with Python's
webbrowser launcher as a fallback. Check your default browser. A headless or SSH
session may not have a desktop opener. In search, use `Ctrl-O`; ordinary `o` is
part of your search text. Live LearnCpp URLs may change; report a broken link.

## OBS text is not updating

Select the `stream.txt` next to the active profile. Start the interactive app to
create it; `--demo`, `--summary`, and `--state-path` do not write it. A pinned quest
continues to show until you pin a different lesson. Keep separate profiles in
separate directories to avoid sharing one stream file.

## Does stream view hide everything private?

It hides note contents and controls, and prevents editing notes until stream view
is turned off. Progress, lesson titles, the existence of attached notes, and some
status messages remain visible. It does not hide other windows, protect local
files, or prevent someone from pressing `s` to leave stream view.
