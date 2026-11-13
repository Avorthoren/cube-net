# Cube Net: for developers

How to run Cube Net from its sources, test it, release it, and run its builds. What the application does and how
it's built is in [docs/idea.txt](docs/idea.txt) (the specification) and [docs/plan.md](docs/plan.md) (the design).

## 1. Running from the sources

You need **Python 3.14** (see `requires-python` in `pyproject.toml`). In a virtual environment, from the
repository's root:

```bash
pip install -e ".[dev]"
```

That installs the application in editable mode (changes to the sources take effect at the next start), its
dependencies (PyQt6, certifi), and the development tools (pytest, pytest-qt, hypothesis, ruff, mypy, packaging).
Then either of these starts it:

```bash
cube-net
```
```bash
python main.py
```

`cube-net` is the command `pip` installed; `main.py` is a thin launcher, handy in an IDE.

### Arguments

| Argument | What it does |
|---|---|
| `PROJECT_FILE` | Opens that project (`.cubenet`) instead of the one worked on last. If it can't be opened, the application asks what to do, as when the last one can't. Only the first argument that doesn't start with `-` counts. |
| `--smoke-test` | The builds' launch test: the window opens and the application quits by itself after 1.5 s, with exit code 0. It uses throwaway settings (the real ones aren't read or changed), opens no project and checks for no update. |
| Qt's own options | Qt takes these before the application sees its arguments. For example `-platform xcb` or `-platform wayland` (Linux), `-platform offscreen` (no window on the screen), `-reverse` (right-to-left layout). |

### Environment variables

| Variable | What it does |
|---|---|
| `QT_QPA_PLATFORM` | Like `-platform`: `xcb`, `wayland`, `offscreen`. The tests use `offscreen`. |
| `CUBE_NET_UPDATES_URL` | Where the update check asks for the releases, instead of GitHub (a JSON file shaped like GitHub's list of releases, or like a single release). For trying updates without publishing one: see `scripts/make_test_release.py` below. |

### Where it keeps its files

| | Settings | Session logs |
|---|---|---|
| Linux | `~/.config/cube_net/Cube Net.conf` | `~/.local/share/cube_net/Cube Net/sessions` |
| Windows | registry, `HKEY_CURRENT_USER\Software\cube_net` | `%APPDATA%\cube_net\Cube Net\sessions` |
| macOS | `~/Library/Preferences/com.cube-net.Cube Net.plist` | `~/Library/Application Support/cube_net/Cube Net/sessions` |

Every copy of the application uses the same settings: a run from the sources, a build, an installed release. The
date of the last automatic update check is among them (`last_check` under `[updates]` in the Linux file): delete it,
and the next start checks again.

A session log records what the user did, for reproducing a problem: `python -m cube_net.ui.session.snapshots LOG`
turns its project snapshots into `.cubenet` files.

## 2. Tests and checks

From the repository's root, with the virtual environment active:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

About 1700 tests, about two minutes. `QT_QPA_PLATFORM=offscreen` keeps their windows off the screen. Some useful
variants:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q tests/core
```
```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q tests/ui/test_main_window.py -k TestUpdates
```

The tests mirror the sources: `tests/core/test_version.py` tests `src/cube_net/core/version.py`, and so on. A few
of them check the project as a whole:

- `tests/ui/i18n/test_russian.py`: every text the user sees has a Russian translation (`src/cube_net/ui/i18n/russian.py`).
- `tests/test_license.py`: every Python file starts with the copyright and license lines.
- `tests/scripts/test_make_icon.py` and `tests/scripts/test_make_readme_animation.py`: the icon and the README's
  animation are up to date (see the scripts below).

Style and types:

```bash
python -m ruff check .
```
```bash
python -m ruff format --check .
```
```bash
python -m mypy
```

`ruff format .` (without `--check`) formats the code. mypy checks `src/cube_net/core` (`[tool.mypy]` in
`pyproject.toml`).

## 3. Scripts

| Script | What it does |
|---|---|
| `python scripts/make_icon.py` | Draws the application's icon (PNG, `.ico`, `.icns`). Run it if the default net or its default colours change. |
| `python scripts/make_readme_animation.py` | Records the README's animation (`docs/media/cube-net.png`) with the application itself, about 20 s. Run it if the default look changes: style, drawing, mouse pointers. |
| `python scripts/make_test_release.py PACKAGE VERSION` | Makes a fake release of a build's package, on the disk, for trying "Download and update" without publishing anything. It prints the `CUBE_NET_UPDATES_URL=...` to start the application with. |
| `python scripts/measure_code.py` | How much there is of everything: characters (without indentation, and without comments, separately) and lines of the app's source, the tests, developer scripts, build and release files, and docs, and the biggest files. It counts the files git tracks; a new kind of file it doesn't know is listed at the end, to be given a category in the script. |
| `python -m scripts.build` | Builds the application for this system, as the release workflow does (see below). Needs PyInstaller, and on Linux appimagetool (`$APPIMAGETOOL`), on Windows Inno Setup. |

## 4. Releasing

> [!IMPORTANT]
> **Release notes.** While working, write what's new under `## Unreleased` in `CHANGELOG.md`. That text becomes the
> release's notes, on GitHub and in the application's update window; `release.sh` refuses to release while it's
> empty.

> [!WARNING]
> **Generated pictures.** After changing how the application looks by default, make sure you also updated the icons
> (`src/cube_net/ui/icons/cube_net.png`, `packaging/icons/cube_net.ico` and `.icns`: they're the default net in the
> default face colours) with `python scripts/make_icon.py`, and the README's animation (`docs/media/cube-net.png`)
> with `python scripts/make_readme_animation.py`. Tests fail while they're out of date, so `release.sh` would stop
> at its tests.

A release is a version tag on `master`, pushed to GitHub: the workflow then builds it and makes a draft release.
`release.sh` does all of it, after checking that everything is in order.

```bash
./release.sh 1.2.0 --dry-run
```
```bash
./release.sh 1.2.0
```

`--dry-run-no-tests` is the same dry run without the tests, which take the longest (ruff still runs); it can't be
combined with `--dry-run`, and works with `--fix` too.

It runs `scripts/release.py` with the active virtual environment's Python (or `$PYTHON`). Versions are
`MAJOR.MINOR.PATCH` without leading zeros, optionally with `-alpha`, `-beta` or `-rc` and a number (`1.2.0-rc.2`):
a pre-release.

### What it checks, in order

It stops at the first problem, in red, saying what to do.

1. The version is a valid one (given without the `v`: the tag gets it).
2. packaging, pytest and ruff are in this Python.
3. The working tree is clean, and this is `master`.
4. It fetches the tags and pulls `master` (fast-forward only). A dry run doesn't pull: it says if it would.
5. The tag doesn't exist yet, and the version isn't lower than the highest release.
6. `## Unreleased` in `CHANGELOG.md` has something in it.
7. ruff finds nothing (`RUN_RUFF = False` at the top of `scripts/release.py` skips this), and the tests pass. While
   they run, one line shows how far they are (`Running the tests... 812 of 1706 (47%)`); pytest's own output is shown
   only if they fail.

> [!NOTE]
> On step 5 it compares with every tag that is a valid release version (`v` and a version), in the whole
> repository: on any branch, not only `master` (it fetched them all from GitHub on step 4). Other tags are ignored.
> Tags with a suffix (`-alpha`, `-beta`, `-rc…`) of the same version count as equal, and all of them are lower than
> that version without a suffix: `1.0.0-alpha` = `1.0.0-beta` < `1.0.0` < `1.0.1-rc`.

### What it does

After a summary (the version, the previous release, the commits since, the notes) and a `y`:

1. Writes the version and today's date into `src/cube_net/__init__.py` (`__version__`, `__version_date__`: About
   shows them). That's the only place of the version: `pyproject.toml` reads it.
2. Renames `## Unreleased` to `## 1.2.0 (2026-11-20)` and starts a new empty `## Unreleased` above it.
3. Commits both as "Release v1.2.0", tags it `v1.2.0` (an annotated tag, "Cube Net 1.2.0"), and pushes `master`
   and the tag together (both or neither).
4. Prints the links to the build (Actions) and the release (Releases).

Then the workflow runs (next section). When it's done, a **draft** release is on the Releases page: check it, then
**Edit → Publish release**. Only then is it public, and only then does the application's update check see it
(GitHub's "latest" is the newest published release that isn't a pre-release).

### If the workflow fails: `--fix`

Fix the problem in a new commit on `master`, then:

```bash
./release.sh 1.2.0 --fix --dry-run
```
```bash
./release.sh 1.2.0 --fix
```

It tags the same version again, on the fix. It checks first that the tag exists here and on GitHub, that
`release.sh` made it (annotated, on a "Release v1.2.0" commit), that it's in `master`'s history with something new
after it, that the package and the changelog still say this version, that no higher release exists, and that GitHub
has no published release of it (a published version is never tagged again: its fix is the next version). It sees
drafts too if `$GITHUB_TOKEN` holds a token that can; without one it reminds you to delete a leftover draft. Then
the usual ruff and tests, a summary and a `y`; it moves the tag (on GitHub only if it's still the one it checked)
and pushes, which starts the workflow again.

If the workflow failed for nothing in the code (GitHub's network, say), use **Re-run failed jobs** on its page
instead: nothing changes in git.

## 5. The release workflow on GitHub

`.github/workflows/release.yml`, on the **Actions** tab as **Release**. It has three stages:

1. **Check** (Ubuntu 22.04): the tag's checks (`python -m scripts.check_release`: the same rules as `release.sh`,
   for a tag pushed by hand too, plus a non-empty `## 1.2.0 (...)` section in the changelog, whose text it keeps for
   the notes), then ruff and the tests.
2. **Build**, one job per system, side by side (one failing doesn't stop the others): `python -m scripts.build`
   builds with PyInstaller, starts the program with `--smoke-test` (the launch test), and makes the package:
   - Linux (Ubuntu 22.04): `CubeNet-<name>-linux-x86_64.AppImage`, launch-tested again as an AppImage.
   - Windows (Windows Server 2025): `CubeNet-<name>-windows-x64-setup.exe`, an Inno Setup installer.
   - macOS (macOS 15, Apple silicon): `CubeNet-<name>-macos-arm64.dmg`.
3. **Draft release** (only for a tag): the three packages, `SHA256SUMS` with their checksums, the notes; marked as a
   pre-release for an `-alpha`, `-beta` or `-rc` version.

### Started by a pushed tag

`release.sh` (or `git push` of a `v*` tag): all of it, for all three systems. The packages are named by the
version: `CubeNet-1.2.0-linux-x86_64.AppImage`.

### Started by hand: Actions → Release → Run workflow

A **test build**. The form has:

| Option | What it does |
|---|---|
| **Use workflow from** | The branch (or tag) to build. A fix can be tried on its own branch before it's merged. |
| **Build for** | `all`, `Linux`, `Windows` or `macOS`: only the chosen system's build runs. |
| **Skip ruff and the tests** | No Check stage: a quicker build, while trying a packaging change. |

The packages are kept for 7 days under the run: its page, **Artifacts**, at the bottom (a zip each). They're named
by their commit, `CubeNet-abc1234-linux-x86_64.AppImage`, and after the version once a version has been released,
`CubeNet-1.2.0-abc1234-linux-x86_64.AppImage`. Nothing is released (but see the exception below).

From a terminal, with GitHub's `gh` (the run's number is in its page's address):

```bash
gh run download RUN_NUMBER -R Avorthoren/cube-net -n build-Linux
```

An AppImage comes out of the zip without its "executable" flag: `chmod +x` it.

> [!CAUTION]
> **The exception: a tag picked in "Use workflow from"** (under its **Tags** tab), with **Build for** `all` and the
> checks not skipped. That run is the same as pushing the tag: it checks the tag, builds all three systems and makes
> the draft release (if the tag fails its checks, nothing is built). It takes the tag itself being picked: a
> **branch** is always a test build, even if its newest commit has a release tag, because the workflow only knows
> which branch or tag was picked, not which tags its commit has. A tag picked with one system, or with the checks
> skipped, is a test build of that tag (named by its version), and releases nothing.

### How it differs from `release.sh`

`release.sh` makes the release commit and the tag, on your machine; the workflow builds what a tag points at. A
pushed tag is always checked again by the workflow (a tag can be pushed by hand), so the rules hold either way. A
manual run needs no tag and changes nothing in git; it releases nothing, except when a tag is picked for all systems
with the checks (the exception above).

## 6. Running a build from a terminal

Every build takes the same arguments as running from the sources: a project file to open, `--smoke-test`, Qt's
options (`-platform ...`), and the variables `QT_QPA_PLATFORM` and `CUBE_NET_UPDATES_URL`.

### Linux (AppImage)

```bash
./CubeNet-1.2.0-linux-x86_64.AppImage
```
```bash
./CubeNet-1.2.0-linux-x86_64.AppImage path/to/project.cubenet
```

The AppImage's own options (its runtime takes them, the application never sees them):

| Option | What it does |
|---|---|
| `--appimage-extract-and-run` | Unpacks into a temporary folder and runs from there: for a system without FUSE. `APPIMAGE_EXTRACT_AND_RUN=1` does the same. |
| `--appimage-extract` | Unpacks everything into `squashfs-root/`, to look inside. |
| `--appimage-help` | The runtime's other options. |

The application's output (Qt's messages, say) goes to the terminal.

### Windows (installed)

The installer puts it in the user's programs folder, `%LOCALAPPDATA%\Programs\Cube Net`:

```bat
"%LOCALAPPDATA%\Programs\Cube Net\Cube Net.exe" "C:\path\to\project.cubenet"
```

It's a windowed program: the command prompt doesn't wait for it, and it prints nothing. To wait for it (to see the
exit code of `--smoke-test`, say):

```bat
start /wait "" "%LOCALAPPDATA%\Programs\Cube Net\Cube Net.exe" --smoke-test
echo %ERRORLEVEL%
```

The installer itself takes Inno Setup's options: `/SILENT` (no questions, a progress window: the application's own
update uses it, and the new version then starts by itself) or `/VERYSILENT` (nothing at all), `/DIR="..."` (another
folder), `/LOG="file"`.

### macOS

```bash
open -a "Cube Net" path/to/project.cubenet
```

`open` starts it like Finder does (`--args ...` passes arguments to it). To run the program itself, with its output
in the terminal:

```bash
"/Applications/Cube Net.app/Contents/MacOS/Cube Net" path/to/project.cubenet
```

A double-clicked file doesn't come as an argument on macOS: the system sends it to the running application, which
opens it the same way.
