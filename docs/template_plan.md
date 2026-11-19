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
9. All instances of each name are glued together (instances at the same point count as glued: the net touches itself
   there). Two instances are glued directly when one name is adjacent to both
   along the loop (loop segments only: folds glue nothing); the direct gluings must connect all of a name's instances
   into one group (union-find). Pairwise direct gluing would be too strict: a vertex with 4 instances has them glued
   in a ring, M_1–M_2–M_3–M_4–M_1, and M_1, M_3 share no neighbour.
10. The net has at least 4 faces.
11. No face touches itself (T6a: a slit or a pinch point must lie between faces).
12. Indices of each name are `1..k` with no gaps; on failure offer to reindex (Yes/No), keeping the order.

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
| T6a | Loops that touch themselves (§8.1) | Slits, loops meeting at a point |
| T6b | Faces in pieces, one face by colour; faces and nets with holes; validation status; tiling across pieces (§8.2) | The torus's purple pieces glue into one ring |
| T6c | The whole Style belongs to the template or the project, with the origin (§8.3) | Style per document |
| T7 | File → New with Cube / Cube with a hole / Custom, projects from templates, the Style tab scrolling (§8.3) | The feature complete |
| T8 | Russian texts checked (`idea.txt` and `plan.md` stay as they are: they're history now) | |

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

- Done later for other bodies: Help's animation of the cube paints with the cube's colours (T7); the Style tab
  scrolls when the window is small (checked by the user on 2026-11-18).

T2 is where any cube assumption I've missed would show up: the test bodies aren't cubes, have faces that aren't
squares (and one that isn't convex), vertices with 4 faces, and two faces sharing several edges.

### 8.1 T6a: loops that touch themselves
A template's loop (and so its net) may touch itself, even along a segment (a slit), as a rearranged net in a project
may: never crossing itself, the area it encloses never overlapping (the overlap check's test around each contact
point, `geometry/sectors.py`, instead of "segments meet only at their shared vertex").
- The net builder tells vertices at one position apart by which point of the body they are, and lets the perimeter
  pass one position more than once.
- A face can't have a slit inside itself (refused, with a message): a slit lies between two faces.
- **The mouse:** any number of vertices may share a position, and each one must be selectable. Each occupies the
  sector of the net between its two loop sides (they can't overlap: that's the rule above), so the direction from the
  point to the mouse picks one: the vertex circle's hitbox is split into those sectors, the part outside the net
  belongs to none. The highlight shows the chosen one's sector. The same for the middle circles of two sides on top of
  each other: the side of the line the mouse is on.
- **Drawing (as for cuts in projects):** a loop side is drawn strictly inside the net, on its own side of the line, and
  its hitbox too, so two sides touching along a segment never share their drawing or their hitbox. Labels of vertices
  at one position go each into its own sector's direction.

Done (T6a):
- `template/loop_geometry.py`: rays of the loop at a point, the gaps between them and the loop's winding number just
  inside each (1: the net, 0: outside, anything else: it overlaps itself). No pairing of rays into passes: at a slit's
  tip on a point the loop passes again, that pairing is ambiguous, the winding number isn't.
- `rules.py`: while the loop is open, crossings, sides of no length and sides along each other the same way are
  refused; once it's closed, every point where it touches itself must have gaps of 0 or 1 only. A fold leaves each end
  into a gap of the net that one of its vertex's sides bounds, and touches nothing but its ends.
- The net builder keeps vertices at one point apart by the point of the body (one vertex if it's the same one), and
  links the perimeter by angle where it passes a vertex twice. A slit whose two sides are one edge of the body is a fold
  in the net (as gluing would make it).
- One piece of paper (`loop_geometry.pieces`): the loop's sides, cut where it touches itself, make a plane graph; each
  bounded face the loop goes round with the net on its left is a piece. A closed loop must be exactly one: parts
  meeting only at points, or a slit from edge to edge, are refused at once (a hole touching the edge, or a slit with a
  free end, are fine).
- Validation: check 9 counts instances at one point as glued; new check 11, a face may not touch itself (a pinch point
  or a slit must lie between faces; a face hanging on by a point can't be a template). `Body.vertex_order` is by
  position and name.
- UI (`ui/template/corners.py`): at a point shared by several vertices, each owns the parts of the gaps next to its
  rays (to the middle when the other ray is another vertex's); the direction to the mouse picks one, the highlight
  rings only its parts, its label goes along the middle of them. Sides of a closed loop are drawn inside the net; of
  two middle circles on each other, the side the mouse is on wins.

### 8.2a Before T6b: faces start without a colour
(Asked for on 2026-11-17.)
- A template's face has no colour until it's given one (`TemplateFace.color` is None; saved as `null`); a fold divides
  it into two without a colour. Such a face is a chessboard of white and light grey (`palette.UNCOLORED_FACE`): every
  rectangle of the hatch halved across its longer side (`hatch.tiled_chessboard`). White is a colour like any other; a
  colour can't be taken away. Templates saved before keep their colours (white ones stay white).
- Validation's new check 1: every face has a colour ("You have a face without a color. Double-click on the face to
  assign its color."); the others move one down (check 13 is reindexing).
- The colour picker opens on a double click in a face (`SheetView.left_double_clicked`); a single click there drags the
  sheet.

### 8.2 T6b: faces in pieces, faces with holes, nets with holes
(Discussed on 2026-11-18; it replaces the earlier sketch of a face as a group of separate polygons.)

Templates still have one loop (drawing inner loops stays in §10.1). But a project made from the torus template must
let the user glue the two purple pieces together, and the result must be one purple face, as on the cube, where a
face can be in several pieces of the net and cuts through them follow the rules the cube already has.

**Faces (one colour, one face).**
- Template faces of one colour are pieces of one face of the body, strictly: two faces that only look alike need
  colours that differ (by one bit of RGB, if need be). Pieces of one colour that aren't joined are refused (below).
- The body's face is the pieces glued together into one shape, in one frame: the frame of the face's *basis* piece
  (below), every other piece placed by the gluing (a multiple of 90 degrees and a shift, as every gluing is). That
  shape may be a ring (the torus's purple, glued along N-T and L-R). Its sides glued to each other aren't sides of the
  body: they're inside the face, no edge, no fold.
- So in a project nothing new happens inside a face: the starting net has the face in several pieces, like the cube's
  net with half of face 5 moved onto face 1, and a cut along a side between the pieces (the torus's N2-T2 and N1-T1) is
  a cut inside a face: dashes of the face's colour and white (today it shows the face's colour twice: two faces of one
  colour). A cut crossing such a side gets no point there.
- Template mode draws all of it as today: a side between pieces of one face is drawn like any other side of the loop.
- A fold separates two faces, by definition: it can't have exactly the same colour on both sides (refused by
  validation, below). Colours that only look alike are the user's choice.
- A labelled vertex with only pieces of one face around it is a point inside that face in the project: no circle, no
  label, removed from the perimeter like any redundant point.
- The engine: a face of the body is no longer always a simple polygon (`Body` checks that now); it may have holes, so
  its boundary is several loops. To work out when it's built: point location in a face, the face's sides and corners,
  dashes measured along its sides, its area, and the hatch's cells.

**Validation.** New checks before reindexing (which stays the last):
- *No fold has one colour on both sides*: the folds are listed, like the other checks list sides.
- *Pieces of one colour are joined*: through glued pairs of loop sides, every piece of a colour reaches every other.
  Otherwise the colours are listed as squares.
- *A face glued from its pieces doesn't intersect itself*: each face on its own, other faces ignored (after gluing, the
  whole net may overlap itself, and that's fine: the torus can be flattened, though it doesn't look like it). The
  pieces may not overlap in the face's frame, and the face must be one piece of paper. "This face self-intersects after
  gluing: [square]" / "Some faces self-intersect after gluing: [square], [square] and [square]". Today's check "no
  face touches itself" (T6a) becomes part of this one, for the glued face instead of the piece. Touching: none except
  where it's glued (no slit inside it, no point where it meets itself), since a point of a face must be one point of
  the body; to be widened if testing shows it's not enough.

**Tiling across pieces.** On the template, pieces of one face are hatched independently, each tied to the grid, so
in a project their hatches wouldn't match once glued. So:
- A counter starts with the template; every time the user gives a face a colour (even the one it has), the face gets
  the counter's value, the counter goes up, and that face's hatch goes back to the default (tied to the grid).
- The face's basis piece is the one with the smallest number: coloured least recently (to make another piece the
  basis, colour the current basis again). An explicit Validate that passes
  works out, for every face in several pieces, where each piece lies in the basis piece's frame, and from then on
  hatches each piece as the basis piece's hatch would continue over it: turned by a multiple of 90 degrees, shifted,
  no longer tied to the grid. The template keeps those hatches (until a piece is coloured again).
- The template file saves the counter, each face's number and hatch, and the status. A template saved before opens
  Undefined, its faces numbered in their order, hatched by default.
- Starting a project from a template validates it anyway (even if it's Validated) and starts the project the same way,
  without changing the template.

**Validation status.** A template is Undefined at first; an explicit Validate makes it Valid or Invalid; any change to
the template itself (not Settings -> Style) makes it Undefined again.
- Below Net area on the instrument panel, after a separator: a square button nearly as wide as the panel. Hint:
  "Hotkey: V".
  - Undefined: active, two lines, "Validate" and "template".
  - Valid: inactive, "Validated" in its middle.
  - Invalid: active (to validate again and see the message), "Invalid" in its middle.
  - Inactive while the loop isn't closed.
- Undo and Redo make it Undefined too (the user accepted always; as built, going back to the very template last
  validated brings its status back).

**Cuts in nets with holes.** Gluing the purple pieces along both of their sides makes a net with a hole, so projects
must allow nets with holes, for every body (a cube's net can have holes too then).
- The cut rule changes: a cut line divides the net in two. Its points may be anywhere, outside the net or in a hole;
  what cuts is the part of the line on or inside the net, and the app works out its real points (where the line enters
  and leaves the net). The cut ends as soon as the net falls apart into at least two pieces, and it's valid if they're
  exactly two. Cutting the purple ring in half: from its outer side down across the hole to its outer side again (two
  real pieces of cut, through the hole between them).
- Approving glues every pair of counterpart cuts that lie on each other, not only those it reaches from the chosen
  cut along the perimeter (reported on 2026-11-18: the torus's purple pieces glued along L-R kept N-T apart, a slit
  with two sets of vertices, because gluing it too makes a hole).
- Everything that assumes one perimeter cycle: validation of the net (`validate_net`), splitting, the halves,
  rearranging and the overlap check, approval, drawing, save and load. Areas and the bounding rectangle don't change
  (a hole isn't area).

**Steps (each ends with the app working):**
1. The validation status and its button.
2. Faces glued from pieces: the body's faces with holes, the two new checks, the cut inside a face coloured as one.
3. Tiling across pieces: the counter, the basis piece, the hatches.
4. Nets with holes in projects, and the new cut rule.

Done (step 1):
- `core/template/validation_status.py`: `ValidationStatus` (Undefined, Valid, Invalid), saved in the template's file as
  `"validation"` (a file without it: Undefined). `TemplateMode` keeps the template the last Validate was about and
  what it said: any other template is Undefined (so the origin, Settings -> Style, and undoing back to that very
  template don't change it). Validating changes the status, so the template has changes to save. Closing gaps in
  indices (the last check) makes it Valid. V and Edit -> Validate are disabled while it's Valid.
- `ui/template/validate_button.py`: the square button below Net area (after a separator), as wide as the panel.
- Session logs: "state validation ...".

Done (step 2):
- `core/body/body.py`: a `BodyFace` may have holes: its corners are loop after loop (`loop_bounds`; the outer one
  counter-clockwise, holes clockwise), `next_corner` / `previous_corner` go along a loop, `contains` knows the holes
  (`geometry.loops_contain`). The starting net is `StartPiece`s: a face whole, or in pieces (their corners in the
  face's frame); a face with holes must be in pieces. Project files: a face's `"holes"` and a piece's `"corners"`,
  written only when there are any, so files saved before read as they are.
- `core/template/glued_faces.py`: `glue_faces` puts each colour's pieces into the frame of its basis piece (for now
  the first one in the template's order; step 3 brings the counter) through the pairs of loop sides between them
  (seams), and finds the glued face's loops. `body_from_template` makes the body's faces of them: the torus has 10
  faces, the purple and the green rings. A vertex with only one face's pieces around it would be a point inside that
  face (`starting_net` numbers such points last).
- Validation: 11 no fold with one colour on both sides; 12 the pieces of a colour are glued together; 13 at least 4
  faces counts colours; 14 a piece touching itself (as before); 15 a glued face is one flat piece of paper (every seam
  falls onto its other side, no overlap, no touching but at seams); 16 reindexing. Faces are listed as squares of
  their colours (`color_square`: an image in the rich text of the message).
- The cut between pieces of one face (the torus's T2-N2 and N1-T1) is inside that face: its colour and white. The
  cube with half of face 5 moved onto face 1 gives the cube (with flat vertices at the middles of the cut's sides).

Done (step 3):
- `TemplateFace.number` and `Template.next_number` (the counter): `with_face_color` numbers the face (even with the
  colour it has: Set face color is always an action now) and ties its hatch to the grid again. A fold's two sides keep
  the face's number and hatch; a merged face keeps the left one's.
- `TemplateFace.hatch`: the template sheet -> the frame its hatch is tied to the grid in. `glued_faces.basis_piece`:
  the smallest number (faces without one, coloured before the counter was kept, first, in the template's order).
  `aligned_hatches` gives every piece its face's frame; a Validate that passes does it as one action ("align
  hatches", undoable), then the template is Valid. `TemplateItem` paints a face in its hatch's frame.
- A project's faces are in their basis pieces' frames, so its hatches match across pieces whatever the template shows.
- Template files: a face's `"number"` and `"hatch"` (only if it has them), the template's `"next_number"`; files
  without them read as before.

Done (after step 3: no vertices where the line is smooth; decided with the user on 2026-11-19):
- A labelled vertex of the template that, the faces glued from their pieces, lies in the middle of a straight edge
  (two corners, both going straight on, between the same two vertices: 360 degrees) is no vertex of the body: its two
  sides become one in each face (`template_body._drop_straight_vertices`). The half-moved cube's X and Y go; so do the
  torus's R, S, T and U. Not if that would make two edges of one name, a side from a vertex to itself, or a loop of
  fewer than 3 corners. The template itself doesn't change.
- The starting net still has those points where they're corners of its pieces, under the template's names
  (`PointLabels.named`); one inside the net (between two folds) goes, as approving removes such points. Gluing makes
  them straight perimeter points, which approving removes too: no ghost is left.

Done (step 4, first part: nets with holes):
- `validate_net`: any number of perimeter cycles (a hole: one more), as long as the net is one piece (its regions
  hang together, by a point at least). A seam may stay in a finished net if it has one region on both sides: without
  it that region would be a ring (`Net.inner_seams`); it isn't drawn.
- Approving glues, after the chosen cut and what follows from its ends, every other pair of counterpart cuts lying on
  each other (the torus's N-T after gluing R-L), going on from their ends too.
- Splitting stops at such a seam where the line crosses it (`pieces(..., at_seams=True)`; no point is shown there).
  `surgery.corner` picks, of a region's corners at one vertex, the one whose angle holds the new edge.
- Rearranging checks the overlap on every perimeter cycle of each half (holes too).
- (Until the second part, a cut line's ends had to be on one perimeter cycle.)

Done (step 4, second part: the cut rule):
- Decided with the user (2026-11-18): a line starts on the perimeter only; when it divides the net it ends where it
  leaves the net (a point clicked beyond is dropped); while cutting, a click off the net adds a point there and a
  drag there pans; off the net the line is thin, dashed and grey, its points small hollow circles.
- `cutting/real_cut.py`: the line's stops (its points and where its segments cross cuts, rounded onto them) and its
  pieces on the net; the first piece whose ends are already joined around the net (one perimeter cycle, or cycles
  earlier pieces joined) divides it. `cutting/perimeter.py`: `segment_crossings` (a segment may cross cuts, not touch
  the perimeter otherwise, nor cross a slit) and `project_onto`.
- Rules: points may be anywhere but on the perimeter (unless put on a cut); at a point on the perimeter the line goes
  into the net or out of it; the first part goes into it. The editor's state comes from the net: CUT_EDITING once
  the line divides it exactly at its end; edits that would make it divide earlier, or not at its end, are refused.
- `split_net` cuts along the pieces in turn, each in the net the earlier ones cut (its ends found again there).
- UI: `SheetView.pan_clicked` (a press that would pan, released without moving); `CutLineItem` draws the parts off
  the net grey and the points where the line crosses cuts like endpoints, with their counterpart images; typed points
  may be off the net (Problem.OUTSIDE_NET is gone). Labels preview only a line that keeps the rules.

### 8.4 Fold lines of several segments
(Asked for on 2026-11-19.) A fold line is drawn like a cut line in a project: from a vertex, through points inside a
face, to a vertex.
- **Vertices:** a fold line's inner points are vertices of the template too, *fold vertices* (inside the loop, not on
  it), with labels like the loop's: Assign the vertex works on them, and validation's check 2 covers them. One that
  goes straight on between two segments is no vertex of the body (§8.2's straight vertices); one where the line bends
  is a vertex of the body with 360 degrees around it.
- **Folds are segments** between any two vertices (of the loop or fold vertices). A fold line starts and ends at any
  vertex (a loop vertex, or a fold vertex of another line), not in the middle of a segment (insert a vertex there
  first), and divides the face it goes through in two, as a one-segment fold does.
- **Editing:** a middle circle on a fold segment inserts a fold vertex there; a fold vertex is dragged like a loop
  vertex; Ctrl+click deletes a fold vertex or a fold segment.
- **Deleting:** a loop vertex: its two sides become one (as now). A fold vertex: the segments at it go. A segment: it
  goes. Then, each time, every segment left hanging (an end at a fold vertex that no other segment reaches) goes too,
  and so on; fold vertices without segments go. The faces a deleted segment divided merge, in the colour of the face on
  its left (seen from where it was drawn), as now.
- **File:** template files get the fold vertices (`"fold_vertices"`); folds stay pairs of vertex ids. Templates saved
  before open as they are; ones saved after can't be opened by older versions (agreed).

Done (§8.4):
- `Template.fold_vertices` (with `all_vertices`, `is_fold_vertex`); `with_fold_line` (the face divided along the line),
  `with_fold_vertex_inserted`, and deleting (`without_fold`, `without_vertex`) followed by `_without_hanging`: hanging
  segments go one after another (their spikes out of the face), then fold vertices without segments.
- Rules: a fold vertex strictly inside the net (winding number 1, on no side of the loop), alone at its point; a
  segment meets others only at its own ends. `TemplateEditor.add_fold_line` / `fold_line_problem` (also for a line not
  finished yet), `insert_fold_vertex`; `delete_vertex` and `move_vertex` take fold vertices too.
- Validation and the body see every vertex (labels, gluing, indices); a bent fold vertex is a vertex of the body with
  360 degrees around it, inside the starting net; a straight one isn't (§8.2's straight vertices).
- Template files: `"fold_vertices"` (only if there are any); a fold vertex must be between 2 segments at least.
- `TemplateTool`: while a fold line is drawn, a click inside a face is its next point (refused, flashing, where the
  line would break the rules), a vertex ends it, a click outside the net gives it up; the middle circles of fold
  segments insert fold vertices; `TemplateItem` draws fold vertices like the loop's, and the line being drawn.
- Deleting a loop vertex may leave a face with nothing (two corners: its fold lies on the loop's new side): that face
  goes, with its fold (2026-11-19, weird_cube.nettemplate's X2 then Y2).
- In a project, the body's vertices inside the net (with 360 degrees around them: where a fold line bends) have
  vertex circles too, as the user chose on 2026-11-19 (`NetItem`); before, only their labels showed.

### 8.5 Holes in templates (inner loops)
(Asked for on 2026-11-19; it does §10.1.)
- **Draw hole** (Hotkey: H): a square button like Validate, above it, with its text only (the icon first asked for, a
  square with a square hole, was dropped on 2026-11-19). Active when nothing else is being drawn or dragged. Then clicks
  draw the hole's loop as the outer loop is drawn (every point an action, undone one by one; its first vertex closes
  it), with Place vertex and Set slope.
- **Where:** a hole's vertices lie on the net (inside the outer loop, not in another hole, on no side, fold or vertex);
  its sides touch no other loop (not the outer one, not another hole) and not themselves. No hole in a hole, and a hole
  may not go round another.
- **Folds:** a hole's sides may cross fold segments. When it's closed, each crossing becomes a vertex of the hole and
  the end of what's left of the fold; the folds' parts inside the hole go, with their fold vertices. The new vertices
  need labels like any other. A hole inside a face that crosses no fold makes that face a ring.
- **After:** a hole's vertices are dragged, inserted (middle circles) and deleted as the loop's; a vertex dragged so
  that its sides cross folds cuts them, as drawing the hole there would have (asked for on 2026-11-19). Deleting a vertex of a hole with 3 deletes the hole: the faces round it
  close up (what was cut off the folds doesn't come back).
- **Its sides** are glued like the outer loop's (counterparts on any loop); a hole runs clockwise (the net on the left
  of every loop).
- **Projects:** a template with holes has a starting net with holes; a face with a hole is one region with a hidden
  seam to its hole (as rings are after gluing, §8.2).

Done (§8.5):
- `Template.holes` (`Hole`: its vertices, closed or not; the last may be being drawn), `TemplateFace.holes` (rings),
  `all_loop_sides` (the outer loop's, then the closed holes'), `complete`, `hole_of`; `template_area` leaves holes out.
- `core/template/holes.py`: `with_hole_point`, `closed_hole` (clockwise; folds cut at the crossings, their parts and
  fold vertices inside gone), `without_hole_vertex` (the hole goes with its third-last vertex), and `faces_from_graph`:
  once there are holes, faces are worked out again from the segments after every change of folds or holes, keeping the
  colour of the face a point inside them was in (the left one's where a deleted fold merges two).
- Rules: a hole's vertices on the net, its sides touching no loop, crossing folds only while it's drawn, not round
  another hole; folds may end at a hole's vertices, not into the hole. `TemplateEditor.add_hole_point` (every point an
  action; the first vertex closes it); deleting a vertex of a hole being drawn is refused (Undo takes it back).
- Validation, gluing and the body see every loop; a ring's piece is one region of the starting net with a hidden seam
  to its hole (`template_body._bridged`); `build_net` takes nets with holes.
- Template files: `"holes"` (only if there are any), a face's `"holes"`.
- UI: `DrawHoleButton` above Validate (just its text, in its middle), Edit -> Draw hole (H);
  `TemplateTool` draws a hole as the loop (SHIFT, a locked slope, Place a vertex), Escape gives up a hole without
  points; its sides have middle circles like the loop's. H is left out of Help's hotkeys with Ctrl+T and V.

### 8.6 Restoring a damaged file
(Asked for on 2026-11-19, after a hole drawn in the torus template left it unreadable.)
- A project or template file that can't be opened, but has actions in its undo list: the message adds "Try to
  restore the last valid state?". Yes: actions are undone one after another (`core/project/restore.py`: the state
  before the last action, then the one before that...) until a state opens; it's shown, with the actions before it
  still to undo and nothing to redo, as unsaved changes (never saved by itself), and "State N actions ago was
  restored." says how far back. None opens: "Unable to restore the file. Open another?" (at start: the usual New
  project / Open... question, saying it couldn't be restored).
- A file that can't be read at all, or has nothing to undo: the message as before.
- Only what the state and its undo list need is read: the file's tables are cut down to it first, so that a broken
  entry nothing refers to any more doesn't stand in the way.
- Russian texts with a number take its form (`RUSSIAN_PLURALS`: 1 действие, 2 действия, 5 действий).

### 8.3 T6c and T7: style per document, built-in templates
(Asked for on 2026-11-17; it replaces the parts of §7 it contradicts.)
- **File -> New** offers three: Cube, Cube with a hole (the torus template, once it's finished), and Custom (a
  `.nettemplate` file). The first two are built into the application, as the cube is now: their templates (or bodies),
  styles and origins are part of the app.
- **The whole of Settings -> Style belongs to the document**, no longer to the application (the face colours already
  do, T3):
  - a new template starts with the default style (the one in the style files);
  - changes made while a template is open are saved in that template, and opening it brings its style back;
  - a new project copies its template's style (a built-in one's for Cube and Cube with a hole); from then on the
    project's style is its own: changes are saved in the project, the template doesn't change;
  - **files saved before this** have no style: they open with the style an older version kept in the application's
    settings (read, never written, as `legacy_face_colors` is now), or the default if there's none, so nothing made
    so far becomes useless (the torus template included).
- **The origin too:** a new project starts with its template's origin (moved or not).
- What to settle when it's built: whether Settings -> Style's "Restore default" brings back the style files' defaults
  or the template's; how the Style tab says that it's the document's (the Settings button's tooltip says "of the
  application").

Done (T6c and T7):
- `core/style.py`: `Style` (its values and ranges) moved to the core; `ui/style` keeps the style files' defaults
  (`DEFAULT_STYLE`) and the least vertex radius (`fitted`). `ProjectSettings.style` and `TemplateDocument.style` are
  saved in the file as `"style"` (projects under `settings`); a file without it (saved before) opens with
  `AppSettings.legacy_style`, what Settings -> Style was then (read, never written), or the defaults. Filled in, it's
  not a change. No format version changes: format 3 was never released, and a template without a style is still read.
- A change in Settings -> Style is the open document's: it marks it unsaved (not undoable, like the face colours) and
  is saved with it. A new template and a new Cube start with the style files' style. "Restore default" brings back the
  style files' values (and the body's colours for Faces colors). The Settings button's tooltip says that Style is the
  open project's or template's.
- `core/project/from_template.py`: `project_from_template` — the body, its starting net where the template has it,
  the template's colours, style and origin.
- Built-in templates: `core/project/builtin/cube_with_a_hole.nettemplate`, read by `builtin_templates.py`, made from
  the author's projects/torus.nettemplate by `python -m scripts.embed_template projects/torus.nettemplate` (only the
  template, its origin and its style; it must be valid and have a style). Tests check the built-in one is valid.
- File -> New (`NewProjectWindow`): Cube / Cube with a hole / Custom template, the file field and Browse... for
  Custom. A custom template that can't be read or is a project is said so; one that isn't valid (or not closed) asks
  "Template is not valid. Open template?". The window comes first, then the unsaved-changes question.
- Help's cube is painted in the cube's colours while a project of another body is open (`palette.face_color`).
- The net builder: at the tip of a slit whose sides have different lengths (the torus's O2), the perimeter goes back
  down the slit (two half-edges leaving the same way).
- Still as before: faces in pieces are separate faces of the body until T6b (the torus's two purple pieces are two
  faces, with the fold between them).

---

## 9. Not decided yet

- Marking templates saved without validation: not for now, maybe later.

---

## 10. Extras (after the main plan)

### 10.1 Templates and nets with holes
To consider: a template whose net isn't a disk, but has holes: an outer loop and inner loops inside it, each hole's
sides glued like the outer loop's (to sides of the same hole, of another hole, or of the outer loop). Nets with holes
in projects, and faces with holes, come in T6b (§8.2); what's left here is drawing inner loops in templates.

What it would touch, as far as known now:
- Template: several loops (one outer, counter-clockwise; holes clockwise), drawn one after another; the rules for
  loops and folds (`rules.py`) apply to every loop, and no loop may touch another; faces may then have holes too, or
  folds must cut them so that every face stays a simple polygon (to decide).
- Validation: counterparts may be on different loops; directions are counted along each loop's own way round.
- The engine: nets with holes come in T6b; a template's starting net with holes is what's new.
- The UI: drawing a second loop, and which loop a click is about.

### 10.2 Coarser hatching for large faces
Done (2026-11-17): Faces tiling takes any positive number with 2 decimals (`TILING_RANGE` from 0.01), so a rectangle
may span several units; the hatch stays tied to the grid (`hatch._indices`), one setting per document (the Style is
the document's, §8.3). What follows is the idea as it was.

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
