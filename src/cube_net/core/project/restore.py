# Copyright (C) 2026 Viktor Podust
# SPDX-License-Identifier: GPL-3.0-or-later

"""Restoring a damaged file from its own history: undoing actions, one after another, until a state opens.

A project or template file keeps the history of its actions (every state the undo list can go back to). When the
state it was saved in can't be read (a bug made it so), the states before it may still be fine. `restore` tries the
one before the last action, then the one before that, and so on: the first that opens is the document, with the
actions before it still in its undo list, and nothing to redo (what came after is what was broken).

Only what that state and its undo list need is kept: the file's tables (templates; nets and rearrangements) are cut
down to it, so that a broken entry nothing refers to any more doesn't stand in the way. A file that can't be read at
all, or has no actions to undo, can't be restored.
"""

from __future__ import annotations

import copy
from typing import Any

from cube_net.core.project.codec import decode_project
from cube_net.core.project.project import Project, ProjectFileError
from cube_net.core.project.template_codec import TEMPLATE_KIND, TemplateDocument, decode_template


def can_restore(data: object) -> bool:
    """Is there anything to try: a file's data with actions in its undo list?"""
    try:
        return isinstance(data, dict) and len(data["history"]["done"]) > 0
    except KeyError, TypeError:
        return False


def restore(data: object) -> tuple[Project | TemplateDocument, int] | None:
    """The document as it was the fewest actions ago that it opens, and how many actions ago that was (at least 1);
    None if no state of its undo list opens."""
    if not can_restore(data):
        return None
    assert isinstance(data, dict)
    done = data["history"]["done"]
    for undone in range(1, len(done) + 1):
        kept = len(done) - undone
        try:
            candidate = _cut_down(data, done[kept]["before"], done[:kept])
            document = decode_template(candidate) if data.get("kind") == TEMPLATE_KIND else decode_project(candidate)
        except ProjectFileError, KeyError, IndexError, TypeError, ValueError, AttributeError:
            continue
        return document, undone
    return None


def _cut_down(data: dict[str, Any], state: int, done: list[dict[str, Any]]) -> dict[str, Any]:
    """The file's data as if it had been saved in state `state` with the undo list `done` and nothing to redo: only
    what they refer to kept, renumbered."""
    result = copy.copy(data)
    used = sorted({state, *(e["before"] for e in done), *(e["after"] for e in done)})
    states = {old: new for new, old in enumerate(used)}
    picked = [copy.copy(data["states"][i]) for i in used]
    if data.get("kind") == TEMPLATE_KIND:
        templates = {old: new for new, old in enumerate(sorted({s["template"] for s in picked}))}
        for s in picked:
            s["template"] = templates[s["template"]]
        result["templates"] = [data["templates"][i] for i in sorted(templates)]
    else:
        rearranged_used = sorted({s["rearranged"] for s in picked if s["rearranged"] is not None})
        rearranged = {old: new for new, old in enumerate(rearranged_used)}
        nets_used = {s["net"] for s in picked} | {data["rearranged"][i]["net"] for i in rearranged_used}
        nets = {old: new for new, old in enumerate(sorted(nets_used))}
        for s in picked:
            s["net"] = nets[s["net"]]
            if s["rearranged"] is not None:
                s["rearranged"] = rearranged[s["rearranged"]]
        result["rearranged"] = [
            {**data["rearranged"][i], "net": nets[data["rearranged"][i]["net"]]} for i in rearranged_used
        ]
        result["nets"] = [data["nets"][i] for i in sorted(nets)]
    result["states"] = picked
    result["state"] = states[state]
    result["history"] = {
        "done": [{**e, "before": states[e["before"]], "after": states[e["after"]]} for e in done],
        "undone": [],
    }
    return result
