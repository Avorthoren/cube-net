# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Make a template built into the application from a template file: `python -m scripts.embed_template <file>`.

The built-in Cube with a hole (File -> New) is the author's own template (projects/torus.nettemplate). After changing
that one in Cube Net (and saving it), run this to copy it into the application:

    python -m scripts.embed_template projects/torus.nettemplate

It writes `src/cube_net/core/project/builtin/cube_with_a_hole.nettemplate` with only what a new project takes from a
template: the template, its origin and its style (no history). The template must be valid (Validate in Cube Net finds
no problem) and have a style (saved by a version that keeps one with the template: open and save it again if not).
`--to <name>` writes another built-in file of that folder instead.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from cube_net.core.history import History
from cube_net.core.project import ProjectFileError, TemplateDocument, load_document, template_to_bytes
from cube_net.core.project.builtin_templates import CUBE_WITH_A_HOLE_FILE
from cube_net.core.template import validate

ROOT = Path(__file__).resolve().parent.parent
BUILTIN = ROOT / "src/cube_net/core/project/builtin"


class EmbedError(Exception):
    pass


def embedded(document: TemplateDocument) -> TemplateDocument:
    """What goes into the application: the template as it is now, without its history. Raises `EmbedError` if it's
    not valid or has no style."""
    if not document.state.template.closed:
        raise EmbedError("the template isn't valid (its loop isn't closed)")
    failure = validate(document.state.template)
    if failure is not None:
        names = ", ".join(failure.names)
        raise EmbedError(f"the template isn't valid ({failure.problem.value}{': ' + names if names else ''})")
    if document.style is None:
        raise EmbedError("the template has no style: open it in Cube Net and save it, then run this again")
    return TemplateDocument(document.state, History(), document.style)


def embed(source: Path, target: Path) -> None:
    try:
        document = load_document(source)
    except ProjectFileError as e:
        raise EmbedError(str(e)) from e
    if not isinstance(document, TemplateDocument):
        raise EmbedError(f"{source} is a project, not a template")
    target.write_bytes(template_to_bytes(embedded(document)))


def main(argv: Sequence[str] | None = None, builtin: Path = BUILTIN) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    name = CUBE_WITH_A_HOLE_FILE
    if "--to" in args:
        i = args.index("--to")
        if i + 1 >= len(args):
            print("--to needs a file name", file=sys.stderr)
            return 2
        name = args.pop(i + 1)
        args.pop(i)
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    target = builtin / name
    try:
        embed(Path(args[0]), target)
    except EmbedError as e:
        print(f"Not embedded: {e}", file=sys.stderr)
        return 1
    print(f"Written {target}. Run the tests: they check the built-in templates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
