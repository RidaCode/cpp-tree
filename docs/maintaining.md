# Maintainer guide

## First public push

The supplied project is prepared for `RidaCode/cpp-tree`, branch `main`. No remote
repository or release is created just by extracting these files. If you choose a
different owner/name, update the repository URLs in `README.md`, `pyproject.toml`,
and the default in `install.sh` before publishing.

1. Review the MIT license and copyright line in `LICENSE`, the third-party
   attribution in `NOTICE.md`, and the project's conduct and security policies.
2. Run the checks below. Inspect the files you are about to stage; no progress,
   personal notes, credentials, or temporary development files belong in the repo.
3. Create an empty public GitHub repository named `cpp-tree`, without initializing
   a second README, license, or `.gitignore`.
4. Commit and push the project. From this extracted project folder, using an
   installed/authenticated GitHub CLI, the commands are:

```sh
git init -b main
git add .
git commit -m "Prepare C++ Talent Tree for open-source use"
gh repo create RidaCode/cpp-tree --public --source=. --remote=origin --push
```

Alternatively create the empty repository on GitHub, then add its remote and push:

```sh
git remote add origin https://github.com/RidaCode/cpp-tree.git
git push -u origin main
```

The public installation URL becomes usable only after `main/install.sh` and the
source files exist in that repository. Test the exact README command in a temporary
account/directory after the first push; local archive tests do not prove public
hosting or network downloads work.

## Repository settings

Before announcing the project:

- Enable private vulnerability reporting under repository security settings.
  Confirm that **Security → Report a vulnerability** is visible.
- Check that the conduct-reporting route in `CODE_OF_CONDUCT.md` is available; add
  a private project contact later if you want a direct maintainer reporting channel.
- Let the `CI` workflow finish on Linux and macOS. Add a branch rule requiring its
  checks before merging; use the actual check names shown by GitHub.
- Set the description to “An offline, Vim-friendly talent tree for tracking your
  LearnCpp progress.” Suggested topics: `cpp`, `learncpp`, `terminal`, `tui`, `python`,
  `learning`, `vim`.

Do not imply a support SLA you cannot maintain. Use issues for ordinary support,
keep decisions public where appropriate, and credit contributors.

## Checks before merging

```sh
python3 -m unittest discover -s tests -v
ruff check .
ruff format --check .
python3 scripts/build.py
python3 dist/cpp-tree.pyz --demo --summary
```

Install the optional linter with the setup in `CONTRIBUTING.md`. For changes to
packaging, also build a wheel (`python3 -m pip wheel --no-deps . -w dist`) and test
it in an empty virtual environment. Source-checkout imports must not mask missing
package resources.

## Release

1. Keep `cpp_tree/__init__.py` as the version source. Update it and the changelog.
2. Run all checks and wait for required GitHub checks to pass.
3. Tag the tested commit, for example `v1.2.0`, and push that tag.
4. Run the **Build release artifacts** workflow on that tag. Download the artifact,
   inspect it, and create a GitHub release attaching `cpp-tree.pyz` and `SHA256SUMS`.
   This workflow only builds artifacts; it does not publish a release automatically.
5. In release notes, state any changes to saves, dependencies, installer behavior,
   or the outline. Verify the public install/update/uninstall path again.

The README install command tracks `main`. To install a particular published tag,
fetch `install.sh` from that same tag and set `CPP_TREE_REF` to it. For forks, set
`CPP_TREE_REPO` to the chosen `owner/repository` as well.

## Reference

The launch structure follows [Starting an Open Source Project](https://opensource.guide/starting-a-project/)
and [Best Practices for Maintainers](https://opensource.guide/best-practices/):
explain what the project does, document setup and contributions, choose a license,
state behavioral expectations, and make routine checks repeatable.
