# Security policy

## Supported versions

Security fixes target the latest released version and the current `main` branch.
Older releases are not maintained separately. Until the first release is tagged,
use the current `main` branch.

## Report a vulnerability

Use this repository's **Security → Report a vulnerability** option for a private
report. Include the affected version, reproduction steps, expected impact, and a
minimal example without private notes or credentials.

If the private-reporting option is unavailable, open an issue asking the maintainer
to enable private reporting. Include no exploit details, private data, or sensitive
attachments in that public request. Do not post a vulnerability publicly merely
because the private channel has not yet been configured.

## Relevant behavior

- The tracker stores progress and notes as plain JSON on your machine. It does not
  encrypt them or provide account isolation beyond filesystem permissions.
- Tracking does not send telemetry or synchronize data to a server. Opening a
  lesson launches your browser; the bootstrap installer downloads GitHub source.
- The installer runs code from the selected repository/ref. Review it before
  running if needed. It does not request root access or alter your shell profile.
- The app opens HTTPS article URLs on `www.learncpp.com`. It never builds a shell
  command from a lesson URL or note.
- Stream view hides note contents in the terminal. It is not a security boundary
  against someone who can read your files or operate your keyboard.

See [the maintainer guide](docs/maintaining.md) for enabling private reporting
before public launch.
