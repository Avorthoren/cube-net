# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""How much there is of everything: `python scripts/measure_code.py` (from anywhere in the project).

It counts the characters of the files git tracks, sorted into the application's source, the tests, developer scripts,
build and release, and docs (media, binaries, LICENSE and .gitignore aren't counted; a text file that fits none of
them is listed at the end, to be given a place here). How it counts:
- the whitespace at the start and at the end of every line isn't counted, nor the whitespace between code and a
  comment;
- a comment's delimiters (`#`, a docstring's quotes, `<!--` and `-->`...) aren't counted, nor the whitespace next to
  them;
- every line's newline counts, an empty line's too: as code, unless the line has a comment and no code; the newlines
  inside a comment count as comment (all but those next to its delimiters).
Comments are Python's `#` comments and docstrings, `#` comments in shell, YAML, TOML and .desktop files, `;` in Inno
Setup's, `<!-- -->` in XML and Markdown. In the docs, "code" is the text without comments.
"""

import ast
import io
import re
import subprocess
import sys
import tokenize
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The suffixes of bigger and bigger numbers (each a thousand times the one before).
SUFFIXES = "kMGT"

# How many of the biggest files the report shows.
BIGGEST_COUNT = 5

# Tracked files that aren't counted at all.
SKIPPED = frozenset({"LICENSE", ".gitignore"})

# Developer scripts: what helps in development, in manual testing and in making releases.
DEV_FILES = frozenset(
    {
        "main.py",
        "release.sh",
        "scripts/make_icon.py",
        "scripts/make_readme_animation.py",
        "scripts/make_test_release.py",
        "scripts/measure_code.py",
        "scripts/pytest_progress.py",
        "scripts/release.py",
    }
)

# What the builds and the release workflow need: these files, and everything in BUILD_FOLDERS.
BUILD_FILES = frozenset({"pyproject.toml", "scripts/build.py", "scripts/check_release.py"})
BUILD_FOLDERS = (".github/", "packaging/")

# The docs: these files, and everything in DOCS_FOLDER.
DOCS_FILES = frozenset({"CHANGELOG.md", "DEV_README.md", "README.md", "notes.txt"})
DOCS_FOLDER = "docs/"

SOURCE_FOLDER = "src/cube_net/"
TESTS_FOLDER = "tests/"


def short(number: int) -> str:
    """`number` in at most 3 digits: 85, 437, 43.7k, 994k, 1.10M (k, M, G, T: thousands, millions...)."""
    if number < 1000:
        return str(number)
    for power, suffix in enumerate(SUFFIXES, start=1):
        value = number / 1000**power
        for decimals in (2, 1, 0):
            text = f"{value:.{decimals}f}"
            if len(text.replace(".", "")) == 3:
                return text + suffix
        # It rounds to 1000 of these: the next suffix's 1.00 then.
    return f"{number / 1000 ** len(SUFFIXES):.0f}{SUFFIXES[-1]}"


@dataclass(frozen=True)
class Comment:
    # Where the comment is in the text, with its delimiters (`end`: just after it).
    start: int
    end: int

    # Where its own text is, without the delimiters.
    text_start: int
    text_end: int


@dataclass(frozen=True)
class Counted:
    # All the characters counted.
    total: int

    # Those that aren't comments.
    code: int


def count(text: str, comments: Iterable[Comment]) -> Counted:
    """The characters of `text` that count (see the module's docstring), with `comments` in it."""
    code = commented = 0
    line_has_code = line_has_comment = False

    def take_code(part: str) -> None:
        nonlocal code, commented, line_has_code, line_has_comment
        for number, piece in enumerate(part.split("\n")):
            if number > 0:  # the line before ended here
                if line_has_code or not line_has_comment:
                    code += 1
                else:
                    commented += 1
                line_has_code = line_has_comment = False
            length = len(piece.strip())
            code += length
            line_has_code = line_has_code or length > 0

    position = 0
    for comment in sorted(comments, key=lambda comment: comment.start):
        take_code(text[position : comment.start])
        lines = text[comment.text_start : comment.text_end].strip().split("\n")
        commented += len("\n".join(line.strip() for line in lines))
        if "\n" in text[comment.start : comment.end]:
            line_has_code = False  # the comment ends on another line, where there's no code before it
        line_has_comment = True
        position = comment.end
    take_code(text[position:])
    return Counted(code + commented, code)


def python_comments(text: str) -> list[Comment]:
    """`#` comments, and the docstrings of the module, its classes and functions."""
    lines = text.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    found = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            start = starts[token.start[0] - 1] + token.start[1]
            end = starts[token.end[0] - 1] + token.end[1]
            found.append(Comment(start, end, start + 1, end))

    def offset(line: int, byte_column: int) -> int:
        """`ast` gives columns in UTF-8 bytes."""
        return starts[line - 1] + len(lines[line - 1].encode()[:byte_column].decode())

    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                string = first.value
                assert string.end_lineno is not None and string.end_col_offset is not None
                start = offset(string.lineno, string.col_offset)
                end = offset(string.end_lineno, string.end_col_offset)
                found.append(_string_comment(text, start, end))
    return found


def _string_comment(text: str, start: int, end: int) -> Comment:
    literal = text[start:end]
    prefix = len(literal) - len(literal.lstrip("rRuU"))
    quotes = 3 if literal[prefix : prefix + 3] in ('"""', "'''") else 1
    return Comment(start, end, start + prefix + quotes, end - quotes)


def line_comments(text: str, marker: str, after_code: bool) -> list[Comment]:
    """Comments from `marker` to the end of the line: anywhere outside quotes after whitespace (`after_code`), or only
    as the whole line."""
    found = []
    position = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        column = _marker_column(content, marker) if after_code else None
        if not after_code and content.lstrip().startswith(marker):
            column = len(content) - len(content.lstrip())
        if column is not None:
            start, end = position + column, position + len(content)
            found.append(Comment(start, end, start + len(marker), end))
        position += len(line)
    return found


def _marker_column(line: str, marker: str) -> int | None:
    """Where a comment starts in the line: the marker outside quotes, at the start or after whitespace."""
    quote = None
    escaped = False
    for column, character in enumerate(line):
        if escaped:
            escaped = False
        elif quote is not None:
            if character == "\\" and quote == '"':
                escaped = True
            elif character == quote:
                quote = None
        elif character in "\"'":
            quote = character
        elif line.startswith(marker, column) and (column == 0 or line[column - 1].isspace()):
            return column
    return None


def html_comments(text: str) -> list[Comment]:
    return [
        Comment(found.start(), found.end(), found.start(1), found.end(1))
        for found in re.finditer(r"<!--(.*?)-->", text, re.DOTALL)
    ]


def comments_in(path: Path, text: str) -> list[Comment]:
    """The comments of a file, by its kind (a kind without comments: none)."""
    if path.suffix in (".py", ".spec"):
        return python_comments(text)
    if path.suffix in (".sh", ".yml", ".yaml", ".toml") or path.name == "AppRun":
        return line_comments(text, "#", after_code=True)
    if path.suffix == ".desktop":
        return line_comments(text, "#", after_code=False)
    if path.suffix == ".iss":
        return line_comments(text, ";", after_code=False)
    if path.suffix in (".md", ".xml"):
        return html_comments(text)
    return []


class Category(Enum):
    SOURCE = "App source"
    TESTS = "Tests"
    DEV = "Developer scripts"
    BUILD = "Build and release"
    DOCS = "Docs"


# The parts each category is shown in (in this order), if it has any.
PARTS = {Category.SOURCE: ("core", "ui"), Category.TESTS: ("core", "ui", "scripts", "other")}


@dataclass(frozen=True)
class Place:
    category: Category

    # Its part of the category (see PARTS), if it has parts.
    part: str | None = None


def place_of(path: str) -> Place | None:
    """Where a tracked file (its path from the root, with "/") is counted; None: nowhere yet."""
    if path in DEV_FILES:
        return Place(Category.DEV)
    if path in BUILD_FILES or path.startswith(BUILD_FOLDERS):
        return Place(Category.BUILD)
    if path in DOCS_FILES or path.startswith(DOCS_FOLDER):
        return Place(Category.DOCS)
    if path.startswith(SOURCE_FOLDER):
        inside = path.removeprefix(SOURCE_FOLDER)
        if inside.startswith("ui/"):
            return Place(Category.SOURCE, "ui")
        if inside.startswith("core/") or "/" not in inside:  # the package's own files (app.py) are its core's
            return Place(Category.SOURCE, "core")
        return None
    if path.startswith(TESTS_FOLDER):
        inside = path.removeprefix(TESTS_FOLDER)
        for part in ("core", "ui", "scripts"):
            if inside.startswith(f"{part}/"):
                return Place(Category.TESTS, part)
        if inside == "conftest.py":
            return Place(Category.TESTS, "core")
        return Place(Category.TESTS, "other") if "/" not in inside else None
    return None


@dataclass
class Measure:
    files: int = 0
    lines: int = 0
    total: int = 0
    code: int = 0

    def add(self, other: Measure) -> None:
        self.files += other.files
        self.lines += other.lines
        self.total += other.total
        self.code += other.code


@dataclass(frozen=True)
class Measured:
    path: str
    measure: Measure


@dataclass
class Report:
    categories: dict[Category, Measure] = field(default_factory=lambda: {category: Measure() for category in Category})
    parts: dict[tuple[Category, str], Measure] = field(default_factory=dict)
    files: list[Measured] = field(default_factory=list)

    # Text files that no category claims.
    unclaimed: list[str] = field(default_factory=list)


def measure_file(path: Path) -> Measure | None:
    """None: a binary file (media, icons)."""
    data = path.read_bytes()
    if b"\0" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    counted = count(text, comments_in(path, text))
    return Measure(1, len(text.splitlines()), counted.total, counted.code)


def measure(root: Path, paths: Iterable[str]) -> Report:
    report = Report()
    for path in paths:
        if path in SKIPPED or not (root / path).is_file():
            continue
        measured = measure_file(root / path)
        if measured is None:
            continue
        place = place_of(path)
        if place is None:
            report.unclaimed.append(path)
            continue
        report.categories[place.category].add(measured)
        if place.part is not None:
            report.parts.setdefault((place.category, place.part), Measure()).add(measured)
        report.files.append(Measured(path, measured))
    return report


def tracked_files(root: Path) -> list[str]:
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
    return sorted(path for path in listed.decode().split("\0") if path)


def _row(name: str, measure: Measure) -> str:
    has_comments = measure.code < measure.total
    code = short(measure.code) if has_comments else ""
    share = f"{100 * measure.code // measure.total}%" if has_comments else ""  # 100% only without comments
    return (
        f"{name:<20}{measure.files:>6}{short(measure.lines):>8}{short(measure.total):>8}{code:>8}{share:>8}"
    ).rstrip()


def report_lines(report: Report) -> list[str]:
    header = f"{'':<20}{'files':>6}{'lines':>8}{'total':>8}{'code':>8}{'code %':>8}"
    lines = [header, "=" * len(header)]
    everything = Measure()
    for i, category in enumerate(Category):
        if i:
            lines.append("-" * len(header))
        measure = report.categories[category]
        everything.add(measure)
        lines.append(_row(category.value, measure))
        for part in PARTS.get(category, ()):
            if (category, part) in report.parts:
                lines.append(_row(f"  {part}", report.parts[category, part]))
    lines += ["=" * len(header), _row("All", everything), ""]
    lines.append('"total" and "code" count characters, without indentation,')
    lines.append("trailing whitespace and comment delimiters.")
    biggest = sorted(report.files, key=lambda measured: measured.measure.total, reverse=True)[:BIGGEST_COUNT]
    if biggest:
        lines += ["", "Biggest files:"]
        width = max(len(measured.path) for measured in biggest)
        for measured in biggest:
            counts = f"{short(measured.measure.total)} total"
            if measured.measure.code < measured.measure.total:
                counts += f" ({short(measured.measure.code)} code)"
            lines.append(f"  {measured.path:<{width}}  {counts}")
    if report.unclaimed:
        lines += ["", "Not counted: no category for them yet (scripts/measure_code.py, place_of):"]
        lines += [f"  {path}" for path in report.unclaimed]
    return lines


def main() -> int:
    print("\n".join(report_lines(measure(ROOT, tracked_files(ROOT)))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
