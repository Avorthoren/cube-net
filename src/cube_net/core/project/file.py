# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Project and template files: gzipped JSON whose "kind" says which (docs/plan.md, section 5.3)."""

import gzip
import json
import os
import shutil
import tempfile
import zlib
from pathlib import Path

from cube_net.core.project.codec import decode_project, encode_project
from cube_net.core.project.project import Project, ProjectFileError
from cube_net.core.project.template_codec import TEMPLATE_KIND, TemplateDocument, decode_template, encode_template

# The usual ending of a project file's name.
PROJECT_SUFFIX = ".cubenet"

# The usual ending of a template file's name.
TEMPLATE_SUFFIX = ".nettemplate"

# The permissions of a newly created project file (temporary files get private ones).
NEW_FILE_MODE = 0o644


def project_to_bytes(project: Project) -> bytes:
    """What's in a project file. The same project gives the same bytes."""
    return _to_bytes(encode_project(project))


def template_to_bytes(document: TemplateDocument) -> bytes:
    """What's in a template file."""
    return _to_bytes(encode_template(document))


def project_from_bytes(content: bytes) -> Project:
    """The project from what's in a project file. Raises `ProjectFileError` if there's anything wrong with it."""
    return decode_project(_data(content))


def document_from_bytes(content: bytes) -> Project | TemplateDocument:
    """A project or a template, whichever the file holds (its "kind" says; a file without one is a project of an
    older version). Raises `ProjectFileError` if there's anything wrong with it."""
    data = _data(content)
    if isinstance(data, dict) and data.get("kind") == TEMPLATE_KIND:
        return decode_template(data)
    return decode_project(data)


def _to_bytes(data: object) -> bytes:
    return gzip.compress(json.dumps(data, separators=(",", ":")).encode("utf-8"), mtime=0)


def _data(content: bytes) -> object:
    try:
        return json.loads(gzip.decompress(content))
    except gzip.BadGzipFile as e:
        raise ProjectFileError("It isn't a Cube Net project.") from e
    except (EOFError, zlib.error, ValueError) as e:  # a cut off file; bad JSON or text are ValueErrors
        raise ProjectFileError("It is damaged.") from e


def save_project(project: Project, path: Path) -> None:
    """Write the project to `path`, in one go: a failure leaves whatever was there as it was. Raises `ProjectFileError`
    if it can't be saved."""
    _save(project_to_bytes(project), path)


def save_template(document: TemplateDocument, path: Path) -> None:
    """Write the template to `path`, like `save_project`."""
    _save(template_to_bytes(document), path)


def _save(content: bytes, path: Path) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as out:
            temporary = Path(out.name)
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        if path.exists():
            shutil.copymode(path, temporary)
        else:
            temporary.chmod(NEW_FILE_MODE)
        temporary.replace(path)
    except OSError as e:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ProjectFileError("Can't save {path}: {reason}.", path=path, reason=e.strerror or e) from e


def load_project(path: Path) -> Project:
    """Read the project from `path`. Raises `ProjectFileError` if it can't be loaded (a template can't either)."""
    document = load_document(path)
    if not isinstance(document, Project):
        raise ProjectFileError(
            "Can't open {path}. {problem}", path=path, problem=ProjectFileError("It's a template, not a project.")
        )
    return document


def load_document(path: Path) -> Project | TemplateDocument:
    """Read the project or the template from `path`. Raises `ProjectFileError` if it can't be loaded."""
    try:
        content = path.read_bytes()
    except OSError as e:
        raise ProjectFileError("Can't open {path}: {reason}.", path=path, reason=e.strerror or e) from e
    try:
        return document_from_bytes(content)
    except ProjectFileError as e:
        raise ProjectFileError("Can't open {path}. {problem}", path=path, problem=e) from e
