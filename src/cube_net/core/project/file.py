"""A project file: gzipped JSON (docs/plan.md, section 5.3)."""

import gzip
import json
import os
import shutil
import tempfile
import zlib
from pathlib import Path

from cube_net.core.project.codec import decode_project, encode_project
from cube_net.core.project.project import Project, ProjectFileError

# The usual ending of a project file's name.
PROJECT_SUFFIX = ".cubenet"

# The permissions of a newly created project file (temporary files get private ones).
NEW_FILE_MODE = 0o644


def project_to_bytes(project: Project) -> bytes:
    """What's in a project file. The same project gives the same bytes."""
    content = json.dumps(encode_project(project), separators=(",", ":")).encode("utf-8")
    return gzip.compress(content, mtime=0)


def project_from_bytes(content: bytes) -> Project:
    """The project from what's in a project file. Raises `ProjectFileError` if there's anything wrong with it."""
    try:
        data = json.loads(gzip.decompress(content))
    except gzip.BadGzipFile as e:
        raise ProjectFileError("It isn't a Cube Net project.") from e
    except (EOFError, zlib.error, ValueError) as e:  # a cut off file; bad JSON or text are ValueErrors
        raise ProjectFileError("It is damaged.") from e
    return decode_project(data)


def save_project(project: Project, path: Path) -> None:
    """Write the project to `path`, in one go: a failure leaves whatever was there as it was. Raises `ProjectFileError`
    if it can't be saved."""
    content = project_to_bytes(project)
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
    """Read the project from `path`. Raises `ProjectFileError` if it can't be loaded."""
    try:
        content = path.read_bytes()
    except OSError as e:
        raise ProjectFileError("Can't open {path}: {reason}.", path=path, reason=e.strerror or e) from e
    try:
        return project_from_bytes(content)
    except ProjectFileError as e:
        raise ProjectFileError("Can't open {path}. {problem}", path=path, problem=e) from e
