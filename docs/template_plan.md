# Cube Net: templates (other bodies) — implementation plan

This plan is based on the template idea, [`template_idea.txt`](template_idea.txt).
Like `plan.md` for `idea.txt`, it describes **how** and **in what order** to build the feature. If the two disagree,
the idea wins and this file gets fixed. What isn't decided yet is listed in §9.

---

## 1. Summary

- A **template** (`.nettemplate`) describes a body by one of its nets: a closed loop of labelled vertices, fold lines
  and face colours, drawn on a fixed 100×100 sheet. It's made in a new mode, *template creation* (File → New
  Template, Ctrl+T), and checked by *validation* (V).
- A **project** (`.cubenet`) is started from the cube, as now, or from a valid template (File → New asks which). A
  project started from a template keeps a copy of everything it needs from it, so later changes to the template file
  don't affect it.
- The cutting engine stays the same. It only has to stop assuming the cube: today the cube is hard-wired into the
  surface model (§2). Turning the cube into one **body** among others is the first and biggest step (§3).

---

## 2. Engine audit: where the cube is hard-wired

The geometry, the net (DCEL), cutting, splitting, rearranging, the overlap check, history and the editor's state
machine don't depend on the cube. What gets them their meaning (which points are "the same point of the body", which
cuts are counterparts) is the surface model, and that one *is* the cube. Nothing found makes the feature impossible,
but these places have to change:

| Where | What it assumes | What it becomes |
|---|---|---|
| `core/cube/topology.py` | The global `CUBE`: 6 faces, 8 vertices A–H, 12 edges, 3 faces per vertex, 2 per edge, faces are unit squares, transitions per *pair of faces* | `Body`: any number of polygon faces, named vertices, edges; transitions per *edge*, since templates the validation accepts can have two faces sharing several edges, or a face glued to itself (§2.1) |
| `core/cube/surface_point.py` | `SurfacePoint(face, local)` with `local` in `[0,1]²`; vertex/edge found by comparing with the square's corners and sides; canonical frame = lowest face containing the point | The same idea over a `Body`: local point inside the face *polygon*; vertex = a corner of the polygon, edge = a side of it; canonical = smallest `(face, local)` over all representations |
| `core/cube/dashes.py` | A segment is on a cube edge if its ends share 2 faces; dash anchor = alphabetically first vertex of the edge; `DASH_LENGTH = 1/20` so that a unit edge has 10 dashes | The edge is found geometrically (§3.3); the anchor is the edge's first end in the body's edge order; dash length stays 1/20 unit |
| `core/net/builder.py`, `core/net/surgery.py` | `len(a.faces & b.faces) == 2` means "this segment is on a cube edge" (FOLD vs SEAM) | `body.edge_between(a, b)` (§3.3). When two faces share several edges, two points on edges between f and g aren't necessarily on the same edge (§2.1) |
| `core/cutting/approve.py` (`is_straight_through`) | Colours of a perimeter piece = the faces its ends share | The face(s) of the piece itself: its region, or the body edge it lies on |
| `core/net/validate.py` | Total area 6; every one of the vertices A–H has an image | Total area = the project's area, a constant of the project: 6 for the cube, the template's area for a custom body; every body vertex has an image |
| `core/labels/point_labels.py` | Cube vertices are named A–H, and those are the first spreadsheet names, so new points continue from I | Body vertices are named by the template (any 1–2 letters, §6.4); a new point gets the next spreadsheet name that isn't taken |
| `core/net/default_net.py`, `core/project/project.py` | Every project starts from the cross | The starting net comes from the body (the cube's is the cross) |
| `core/project/codec.py`, `file.py` | Surface points are stored as `{face, local}` of the cube; the file is gzip from the first byte | The project stores its body (or says "cube"); the file starts with a type mark (§5) |
| `core/project_settings.py` | Area threshold at most 12.000; the instrument panel input goes from 0 to 20 | For every project, the cube's too: at most the template sheet's area, 100 × 100 = 10000, in the file and in the panel's input (§6.1) |
| `ui/palette.py`, `ui/style/style.py`, `net_painting.py` | Exactly 6 face colours, from the Style, keyed 1–6 | As many colours as the body has faces: a setting of the project, for every project, the cube's too (§7) |
| `ui/sheet/zoom.py`, `core/sheet.py` | The sheet is the net's box plus 5 units; zoom limits from the net's size | A fixed 100×100 sheet in template creation; zoom limits from the sheet there, since an empty sheet has no net |
| `ui/help/help_window.py` | "Area of the unit cube: 6" | Stays: the Help describes cube projects; template creation gets its own help later (as the idea says) |

### 2.1 When "the ends share 2 faces" stops meaning "on an edge"

On the cube, two faces share at most one edge, and no vertex outside it. So two points that both lie on faces f and g
are on that one edge, and the segment between them runs along it. Non-convex faces alone don't change that. What
does is that the validation checks only the gluing (names, directions, lengths), so it accepts templates where this
no longer holds:
- **Two faces sharing several edges: the pillow.** Two unit squares stacked on each other and joined along all four
  sides. Its template: P_1 (0,0), Q_1 (1,0), P_2 (2,0), S_2 (2,1), R_1 (1,1), S_1 (0,1), with the fold Q_1–R_1.
  Face f is the left square, face g the right one. Pairs: P_1–Q_1 with Q_1–P_2, S_2–R_1 with R_1–S_1, P_2–S_2 with
  S_1–P_1; all pass every check. f and g share the 4 edges PQ, QR, RS and SP. In a project from it, a cut from
  X = (0.5, 0) on P_1–Q_1 to Y = (0, 0.5) on S_1–P_1 runs across the inside of f. X is on edge PQ and Y on edge SP,
  so both are on faces f and g, and the test calls X–Y a body edge:
  - while the cut is being approved, X–Y is dashed in the colours of f and g, like an edge, instead of f's colour and
    white, like a cut;
  - once the halves are glued back along it, it becomes a fold instead of a seam, so cleanup doesn't remove it: a
    fake fold line stays across face f.
- **A face glued to itself.** A loop with no folds at all is one face whose sides are glued to each other, e.g. the
  pillow's template without its fold. Every edge has only that face, so the test never finds an edge: a gluing along
  one becomes a seam that cleanup dissolves, and edges are drawn like cuts. `Body` handles this case on purpose: an
  edge records both of its sides as (face, side), even when the face is the same, and a surface point's canonical
  form is the smallest of all its (face, local) forms, so a point of such an edge is still one point.

Whether such templates are bodies is up to the user, as the idea says. But the engine mustn't misbehave on them, and
an edge identity instead of a face pair costs little.

### 2.2 Gluing stays rational

What stays valid for every template the validation accepts: since glued cuts are parallel or perpendicular, every
gluing is a `Rigid90` (rotation by k·90° plus a translation), so coordinates stay rational and `Rigid90.from_segments`
still works. This needs one more condition the idea doesn't list, though: the two cuts of a pair must run in
**opposite directions** along the loop (§4.3, check 5). Otherwise the gluing needs a mirror image, and the
rearrangement would put the moved part on top of the other one instead of next to it.

---

## 3. Step 1: the body abstraction (no visible change)

A refactor first, done while the app still only knows the cube, so the 2000 existing tests prove it changes nothing.

### 3.1 `core/body/` (replaces `core/cube/`)
- `Body`: immutable, all checks once in `__init__` (raising `BodyError` with a readable message):
  - **faces**: `Face` ids `1..n`, each a counter-clockwise polygon in its own local frame (for a template body,
    the template's sheet coordinates, so a face's placement in the template's net is the identity);
  - **vertices**: names (`"A"`, `"CT"`); each face corner is a body vertex;
  - **edges**: each one is two face sides glued together: `(face f, side i)` and `(face g, side j)`, plus the
    `Rigid90` taking f's frame to g's across it (identity for a fold of the template, the gluing map for a pair of
    perimeter cuts);
  - its **net**: where each face starts on the sheet (placements), from which `starting_net(body)` builds the first
    net with `build_net`;
  - its **area** (6 for the cube, the template's area for a custom body: a constant of the project, saved with it)
    and its default **colours** (§3.4).
- Queries the engine needs: `vertex_faces`, `edge_faces`, `transition(edge)`, `corner_local`, `area`, and two new ones
  in place of the "2 common faces" test: `edge_containing(face, local)` and `edge_between(p, q)`.
- `CUBE` becomes `cube_body()`: the same tables as now (faces 1–6 as unit squares, A–H, the cross), turned into a
  `Body`. The cube checks that exist now (12 edges, 3 faces per vertex, orientation, the default net) stay as tests
  of the cube tables.

### 3.2 `SurfacePoint` knows its body
- `SurfacePoint(body, face, local)`; equality and hash stay `(face, local)` (points of different bodies are never
  compared). `faces`, `vertex` and `edge` are derived as now, through the body.
- `Net` gets a `body` attribute; everything that creates surface points (`builder`, `split`, `pieces`, the codec)
  takes the body from the net. That's the only plumbing: about 6 call sites.

### 3.3 Edges found geometrically
`edge_between(p, q)` = the body edge both points lie on (as an end or inside it), checked in one face's frame. It
replaces `len(a.point.faces & b.point.faces) == 2` in `builder.py`, `surgery.py`, `dashes.py` and `approve.py`. For
the cube both answers are always equal, which the existing tests and one new property test confirm.

### 3.4 Colours belong to the body
`palette.FACE_COLORS` holds the open project's face colours, one per face of its body (§7). The vertex circles already paint any number of faces as sectors, so 4 or more
faces at a vertex need nothing new.

### 3.5 Labels
`PointLabels(body)`: the body's vertex names first; a new point gets the first spreadsheet name not taken yet (A, B,
..., Z, AA, ...), so a body with vertices `A`, `B` and `D` names its first new point `C`. For the cube, that's `I`,
as now.

---

## 4. Step 2: templates in the core (`core/template/`)

### 4.1 Data
- `Template`: immutable, snapshot-friendly, like `Net`:
  - `loop`: the vertices of the loop, each with an id, a position and an optional label `(name, index)`. Kept
    counter-clockwise, as the engine needs: a loop drawn clockwise is reversed when it closes (the user doesn't see
    the direction);
  - `folds`: pairs of loop vertex ids;
  - `colours`: one per face, white by default. Faces are the parts the folds divide the loop into (each fold is a
    chord, so it always divides one face into two). A colour is kept on a face under the face's *key*, which survives
    moving and inserting vertices: the set of fold ids around it, plus the loop vertex where the face starts.
  - `closed`: whether the loop is closed yet.
- `TemplateEditor`: the state machine, history (the same `History`, 1000 actions) and rules, Qt-free like `Editor`.
  States: `INITIAL` (empty sheet), `LOOPING` (open loop), `FINALIZATION` (closed loop).

### 4.2 Rules (each action returns a `Rejection` like the cut editor's, so the UI can flash what's wrong)
- **INITIAL**: a click anywhere on the sheet puts the first vertex → `LOOPING`.
- **LOOPING**: like a cut line, but a segment may not touch any other segment or vertex, except the last
  segment ending exactly at the first vertex, which closes the loop → `FINALIZATION`. Only the first vertex is active
  (snapping, hitbox), and only once there are at least 3 vertices, so a closed loop has at least 3 segments; closing
  it earlier is refused. Place a vertex, Set slope and
  Move the origin work as in a cut line.
- **FINALIZATION**: drag a vertex, insert one at the middle of a segment, Ctrl+click deletes one. The loop must stay
  simple (no crossing, no touching) and folds must stay valid: a drag that would break either is refused, and the
  point goes back, as with a cut line's point. A deletion that leaves fewer than 6 vertices is refused with a
  warning. Deleting a vertex a fold ends at deletes that fold too, in the same action (one undo brings both back).
- **Fold lines**: from a loop vertex to another, straight, no inner points. Its inside must be strictly inside the
  loop, and it may meet other folds only at loop vertices. Not along a loop segment, not between neighbours on the
  loop. Ctrl+click on a fold deletes it. The merged face takes the colour of the face to the left of the fold, looking
  from the vertex it was started at to the one it ended at.
- **Face colours**: a click inside a face opens the colour picker (the one from the Style tab, without the native
  dialog) with the face's colour. A fold splitting a face gives both parts its colour.
- **Labels**: right click on a vertex → Assign the vertex (§6.4).
- Undoable actions: add/delete a vertex, move a vertex, add/delete a fold, set a face colour, set a label (the five in
  the idea). Moving the origin is undoable too, as in projects.

### 4.3 Validation (`core/template/validation.py`)
Pure, ordered checks, as in the idea's Validation section; each returns the problem with what to list, and the UI
words it (§6.5). The first failing check stops the rest.
1. Every loop vertex has a label.
2. No loop segment or fold joins two vertices with the same name (A_1–A_3).
3. Each loop segment has exactly one counterpart: another loop segment with the same two names (indices ignored).
4. Counterparts are parallel or perpendicular.
5. Counterparts have the same length (compared squared, so everything stays rational).
6. Counterparts run in opposite directions along the loop (`A→CT` on one, `CT→A` on the other). Without it the pair
   can't be glued without turning one side over (§2.2).
7. No fold has the same two names as a pair of loop segments.
8. No two folds have the same two names (`Body` refuses them: 4 face sides would join the same two vertices).
9. All instances of each name are glued together. Two instances are glued directly when one name is adjacent to both
   along the loop (loop segments only: folds glue nothing); the direct gluings must connect all of a name's instances
   into one group (union-find). Pairwise direct gluing would be too strict: a vertex with 4 instances has them glued
   in a ring, M_1–M_2–M_3–M_4–M_1, and M_1, M_3 share no neighbour.
10. The net has at least 4 faces.
11. Indices of each name are `1..k` with no gaps; on failure offer to reindex (Yes/No), keeping the order.

No Euler characteristic check: a torus is allowed.

The 4-face minimum rejects the pillows of §2.1 as templates. The engine still handles them (and a face glued to
itself, which a template with 4 faces can still have), and they stay test bodies in T2, built by hand.

### 4.4 From a valid template to a body
`body_from_template(template)`: faces = the fold-divided polygons in template coordinates; vertices = names; edges =
folds (identity) plus the pairs of loop segments (`Rigid90.from_segments`); colours = face colours; the starting net
= the template's own net: the loop, with the folds as fold edges and every face placed by the identity. The vertex
ids follow the template's indices, so `A_2` in the template is `A_2` in the project. `Body.__init__` re-checks
everything, so a template that passes validation but breaks the engine is a bug caught here, never a broken project.

### 4.5 Area
`template_area(template)`: the loop's area (exact `Fraction`, shoelace). It's the "Net area" in template creation.

---

## 5. Step 3: files

The kind of file is marked by a field in the JSON: `"kind": "project"` or `"template"`. The file stays gzipped JSON,
as now; a gzip file is binary from its first byte, so it has no first line to put a mark on. Version 1.2.0 opening a
new file says it was saved by a newer version of Cube Net.
- A file without the field is read as the current `.cubenet` format (format versions 1 and 2), so every existing
  project still opens.
- Projects get `format_version` 3: `body` is `"cube"` or the full body (faces, vertices, edges, area), plus the
  project's face colours (§7). Surface points stay `{face, local}`.
- Templates have their own `format_version` 1: the template plus its history and redo stack (like projects), so undo
  survives reopening.
- Opening goes by the field, not by the extension; Open… shows both extensions. Save in template creation suggests
  `.nettemplate`.
- The area threshold may be up to 10000 when read (§6.1); older files are always within that.

---

## 6. Step 4: the template creation UI

### 6.1 Mode
- The main window gets a *mode*, project or template, chosen by what's open. The template mode swaps:
  - the sheet item and the tool (`TemplateTool` next to `CutTool`, sharing the hint, cursor and context-menu code);
  - the instrument panel: no bounding-rectangle controls; instead **Net area** with the value as a float, its hint
    with the exact value, and Ctrl+C copying it (the same code as the area hint now);
  - Settings: no "Show vertex labels" (labels are always shown), no "Faces colors" section;
  - Edit → Approve cut is disabled; a new item **Validate (V)**.
- The sheet is 100×100 units, fixed: no auto-resizing, zoom limits from the sheet. The two numbers are constants
  (`TEMPLATE_SHEET_WIDTH`, `TEMPLATE_SHEET_HEIGHT`), and their product is the largest target area of **every**
  project, the cube's included: the panel's input goes from 0 to 10000 (it gets wide enough for 5 digits and 3
  decimals), and so does the threshold in the file (`MAX_AREA_THRESHOLD`, today 12).
- No template-specific entries in Help → Hotkeys (the idea leaves that help page for later).

### 6.2 File menu
- **New Template (Ctrl+T)**, right below New: asks to save unsaved changes like New, then opens an empty template
  with no file, so Ctrl+S asks where to save.
- Open… opens either kind; Save/Save As keep the kind of what's open.

### 6.3 Drawing and editing
- `INITIAL` and `LOOPING`: a regular cursor; a click adds a vertex; only the first vertex has a hitbox and snaps;
  Escape/Undo as in cutting. A rejected point flashes the offending segments black, as for cuts.
- `FINALIZATION`: vertices are active (drag; a click starts a fold, which ends at the vertex released on); midpoint
  circles insert vertices; Ctrl+click deletes a vertex or a fold; a click inside a face opens the colour picker. The
  cursors reuse the cut tool's.
- Fold lines are drawn like folds in projects; the loop like the perimeter; faces filled with their colours.
- Hatching appears once the loop is closed (a white face shows it only once it's given a colour). It's always the
  same, vertical, tied to the grid: as if the whole sheet were hatched and only the faces showed it. So the Style's
  "Faces tiling" now means *per unit* (for the cube, a face is a unit, so nothing changes there). A project from the
  template keeps that hatching on each face, moved along with it.

### 6.4 Assign the vertex
- Context menu item, enabled on a vertex. The window `AssignVertexWindow` (a `SmallWindow`, like Place a vertex):
  "Name (1–2 Latin letters) and index (1–99):" (Russian: латинские буквы), two fields, Cancel/Assign, the title-bar
  cross acts as Cancel.
- The name field accepts 1–2 letters and turns them into capitals; the index field 1–99. New: name
  empty, index 1. Existing: current values. An empty name removes the label.
- A taken label: a second window "Such label already exists. Assign first free index?" Yes → the smallest free index
  for that name, both windows close; No → back to the first window.

### 6.5 Validation messages
The idea's texts, with lists like "A-CT, AS-QC and Z-R" (Russian: "A-CT, AS-QC и Z-R") and singular/plural forms per
language (Russian needs its own forms, not just English ones translated). Reindexing: Yes/No; then "Vertices
automatically reindexed. / No other problems found." No problems: "No problems found." Every text goes through
`tr` with a Russian entry.

---

## 7. Step 5: new projects from templates

- **File → New** opens a window: a dropdown (Cube / Custom), and below it a file field with Browse… for a
  `.nettemplate`, disabled for Cube. OK/Cancel.
- A custom template is validated quietly. Not valid: "Template is not valid. Open template?" Yes → the template opens
  for editing (after the unsaved-changes question, if not asked already); No → back to the New window.
- Valid: `body_from_template` → a new project with that body, its starting net, its area and its colours; nothing
  refers to the template file afterwards.
- In such a project, everything works as for the cube; what differs comes from the body: the vertex names and the
  area. The target area's limit (10000) is the same for all projects.
- **Face colours** are a setting of the project, for every project (the cube's too), since another project may have
  other faces. They stay in Settings → Style → Faces colors, one row per face of the body, next to the Style's other
  sections, which are app settings:
  - they're saved in the project; a change marks it unsaved (not an undoable action, like the Style today);
  - a new project gets the body's colours: the cube's default colours, or the template's; "Restore defaults" brings
    those back;
  - the app setting that holds the face colours today is never written again, but still read: a project saved before
    this change (format 1 or 2, no colours) opens with those colours, as it looked before; a new cube project starts
    with them too. Without that setting (a new user), the cube's default colours;
  - the Style tab gets a vertical scroll bar, for bodies with many faces.

---

## 8. Milestones

Each one ends with the app working and all tests green.

| # | What | Visible |
|---|---|---|
| T1 | `Body`, `SurfacePoint(body, …)`, `edge_between`, labels, area and validation through the body; the cube as a body | Nothing (refactor) |
| T2 | Hand-written test bodies built through `Body` and run through the whole engine (cuts, rearrangement, overlap, approval, cleanup, save/load in tests): a 1×1×2 box, an L-shaped prism, the pillow and the fold-less pillow from §2.1 | Nothing |
| T3 | The `kind` field, project format 3 with a body and face colours, template files; the target area's limit raised to 10000; face colours as a project setting | Old projects still open |
| T4 | `Template`, `TemplateEditor`, its rules and history, `template_area` | Nothing |
| T5 | Template validation, `body_from_template` | Nothing |
| T6 | Template creation mode: File → New Template, the sheet, drawing, editing, folds, colours, hatching, Assign the vertex, Validate, Net area, settings hidden; session logs record template creation from the first version you can try | The new mode |
| T7 | File → New with Cube/Custom, projects from templates, the Style tab scrolling | The feature complete |
| T8 | `idea.txt`/`plan.md` updated (once this plan is done), Russian texts | |

Done in T1 beyond the table above: `Net.body_edge_of` / `Net.segment_faces` (a half-edge's body edge and colours,
found in its region's frame) replace every "the ends share 2 faces" test; `PointLabels(body)`; `starting_net(body)`
(`default_net()` is the cube's); dashes on an edge are still measured from its alphabetically first vertex, so the
cube looks exactly as before.

Done in T2:
- Test bodies (`tests/core/conftest.py`): a 1x1x2 box, an L-shaped prism (a reflex face corner, 450-degree vertices),
  the pinwheel 2x2x1 box (a 4-face vertex with 4 images, flat vertices), the pillow and the fold-less pillow. Random
  chains of cuts and cuts along folds run on all of them (`tests/core/cutting/test_approve.py`).
- A cut's counterpart is looked up by the segment of the body it is an image of (its ends in its face's frame, or in
  its edge's), not by its two end points: in the pillow, Q and S are joined by a diagonal of each face.
- A vertex of the body with exactly 360 degrees around it (`Body.vertex_angle`) can end up inside the net: approval
  keeps it, validation allows it, and a cut line passing through it uses it. Templates have such vertices whenever a
  labelled loop vertex lies where the body is flat. The sheet paints vertex circles only on the perimeter, so such a
  vertex shows only its label for now (to decide in T6/T7).
- Saving and loading a project of another body waits for T3 (the file has no body yet).

Done in T3:
- Project files are format 3: `"kind": "project"`, `"body"` (`"cube"`, or the faces, starting net and default colours
  of another body), and `settings.face_colors`. Formats 1 and 2 still load: the cube, no colours. A file of format 3
  with another kind is "not a Cube Net project" until T4 reads templates.
- The target area goes up to `TEMPLATE_SHEET_WIDTH * TEMPLATE_SHEET_HEIGHT` = 10000 (core/sheet.py), for every project.
- Face colours are a project setting (`ProjectSettings.face_colors`): Settings -> Style -> Faces colors shows one row
  per face of the open project's body, a change marks the project unsaved, Restore default brings back the body's
  colours. The application's style no longer has them; the colours 1.2.0 kept there (`AppSettings.legacy_face_colors`)
  are only read: a project without colours opens with them, a new cube project starts with them.
Done in T4 (`core/template/`):
- `Template` (immutable): the loop's vertices with optional labels, folds (as drawn: from `start` to `end`), and the
  faces with their colours, kept up to date by every change instead of being worked out again: a fold divides its face
  (both parts in its colour), deleting one merges the two (in the colour of the face on its left, seen from where it
  starts), a vertex inserted or deleted goes into or out of its face, and deleting a vertex deletes its folds.
- `rules.check`: segments meet only at a shared vertex; the loop stays counter-clockwise; folds stay strictly inside;
  everything on the 100 x 100 sheet. A rejection says what's wrong and which segments to flash.
- `TemplateEditor`: INITIAL / LOOPING / FINALIZATION, every action in the history (new `ActionKind`s), the origin as
  in projects. A loop drawn clockwise is turned round when it closes.
- Saving templates waits for T5 (with their validation and `body_from_template`), so it's all there at once.

Done in T5:
- `template/validation.py`: the 11 checks of template_idea.txt in order; a failure says what to list (names, name
  pairs, segments, or groups for 7 and 8), the UI words it. `reindexed` closes the gaps in indices, keeping the order.
- `template/template_body.py`: `body_from_template` (faces in the template's order and frame, the starting net in
  place). `Body.vertex_order` numbers the starting net's vertices so that each name's images keep the template's
  indices: the cross drawn as a template gives exactly the cube's default net, A_1 where A_1 is.
- Template files: `project/template_codec.py` (the template, its origin and its history; kind "template", format 1),
  read and written by `project/file.py` like projects; `load_document` gives whichever the file holds, by its kind.

Done in T6 (`ui/template/`):
- `TemplateMode`: the template's own sheet view (fixed 100 x 100), editor, tool, cursor and right click menu, file and
  validation. The main window keeps one stack of two views and shows the project's or the template's
  (`in_template_mode`); New, New Template (Ctrl+T), Open, Save, Save As, Undo, Redo, Escape and Ctrl+C go to the
  one shown. Open reads either kind (by the file's "kind").
- `TemplateTool`: a click draws the loop (the usual arrow; SHIFT and a locked slope as for cuts); the first vertex closes
  it. Then: a vertex dragged moves; a vertex clicked (no drag) starts a fold, a click on another vertex ends it (anywhere
  else, or Escape, gives it up); a middle circle inserts a vertex; Ctrl+click deletes a vertex (with its folds) or a
  fold; a click in a face opens the colour picker. Refusals flash in black.
- `TemplateItem`: faces hatched in their colour, tied to the grid (`tiled_hatch`, per unit), folds dashed, the loop
  solid, all labels always.
- The right click menu (shared with projects) has Assign the vertex too (`AssignVertexWindow`, the "label taken"
  question). Validate (V) words the 11 checks (`validation_messages.py`), and offers to reindex.
- The instrument panel shows Net area (with its exact value in the hint; Ctrl+C copies it) instead of the bounding
  controls; the ruler, Approve and the labels' switch are hidden; so is Faces colors in Settings -> Style.
- Session logs: template actions ("template add 10.000,10.000", "close", "move", "fold", "label", "color",
  "validate", ...) and snapshots of the template (`snapshots.py` extracts them as .nettemplate files).
- Not in template mode for now: the ruler. Ctrl+T and V are left out of Help's hotkeys (a page of their own later).

- Still to do for other bodies: Help's animation of the cube paints with the open project's colours (it must use the
  cube's, T7); the Style tab's scroll bar (T7).

T2 is where any cube assumption I've missed would show up: the test bodies aren't cubes, have faces that aren't
squares (and one that isn't convex), vertices with 4 faces, and two faces sharing several edges.

---

## 9. Not decided yet

- Marking templates saved without validation: not for now, maybe later.

---

## 10. Extras (after the main plan)

### 10.1 Templates and nets with holes
To consider: a template whose net isn't a disk, but has holes: an outer loop and inner loops inside it, each hole's
sides glued like the outer loop's (to sides of the same hole, of another hole, or of the outer loop). Nets with holes
would also be what cutting can make in a project (today a cut must keep the net in one piece without holes).

What it would touch, as far as known now:
- Template: several loops (one outer, counter-clockwise; holes clockwise), drawn one after another; the rules for
  loops and folds (`rules.py`) apply to every loop, and no loop may touch another; faces may then have holes too, or
  folds must cut them so that every face stays a simple polygon (to decide).
- Validation: counterparts may be on different loops; directions are counted along each loop's own way round.
- The engine: the DCEL already allows several perimeter cycles, but a finished net is checked to have exactly one
  (`validate_net`), and cutting, rearranging and the overlap check assume one; the "halves" after a cut may not be two
  then. The bounding rectangle and the area are fine as they are (holes don't count in the area).
- The UI: drawing a second loop, and which loop a click is about.

### 10.2 Coarser hatching for large faces
Settings -> Style -> Faces tiling is the number of hatch cells per unit (columns x rows), at least 1 each. A template
drawn large (the cube's net with faces of 4 x 4 units, say) is looked at zoomed out, and at least one cell per unit
is a mess there. To consider: tiling below 1 per unit, so that one cell spans several units (e.g. 1/4: a cell 4 units
wide). Hatching is tied to the grid (`tiled_hatch`), so a cell of k units would start at multiples of k.

What it would touch, as far as known now:
- The setting's values and its fields: fractions or "one cell per N units" (whichever reads better), and the range
  (`TILING_RANGE`, saved styles still valid).
- `tiled_hatch` and `hatch_path` (projects: a face's local frame), and the cache of hatch paths.
- Whether it's one setting for everything, or the template's / the project's own (a large template wants it, a cube
  project doesn't).
