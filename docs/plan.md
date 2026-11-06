# Cube Net: implementation roadmap

This roadmap is based on [`idea.txt`](idea.txt), the specification and the source of truth for behaviour.
This file describes **how** and **in what order** to build it. If the two disagree, `idea.txt` wins and this file
gets fixed.

---

## 1. Guiding principles

1. **Keep the core separate from the UI.** All geometry, topology, cutting, gluing, validity checks, history and
   serialization live in a pure-Python package (`cube_net.core`) that never imports Qt. The Qt layer (`cube_net.ui`)
   only draws the state and turns mouse/keyboard input into core calls. The hard part of the project is the core, and
   that's what makes it testable without a GUI.
2. **Use exact arithmetic everywhere in the core.** Coordinates are `fractions.Fraction`. Every rearrangement is a
   rotation by k·90° plus a translation, so coordinates stay rational forever. Tests like "touches", "is collinear" and
   "lies on the perimeter" then need no tolerance. Floats are used only for drawing (and for the bounding-rectangle
   *display*, though see §4.7: even its area is rational).
3. **One entry point for user input.** Every point that comes from the mouse goes through one `quantize()` function
   (sheet floats → `Fraction`). For now it rounds each coordinate to 1/1000 unit, which keeps fractions small and
   readable. Snapping will go there later without touching anything else.
4. **A serializable, snapshot-friendly state.** The whole editor state (net, cut line in progress, state machine state)
   can be turned into plain data (dicts/lists) and restored exactly. Undo/redo and save/load are built on that.
5. **Invariants are checked in code.** A `validate_net()` function asserts every structural invariant (§3.4). Tests
   call it after every operation, and debug builds call it after every action.
6. **Test-first for the core.** pytest for unit and scenario tests, hypothesis for property tests (random valid cuts
   must keep every invariant), pytest-qt with `QT_QPA_PLATFORM=offscreen` for UI smoke tests.
7. **See it early.** Logic and its UI are built together, in small steps, so every feature can be tried in the
   app as soon as possible (§7).
8. **Small modules.** Only very close relatives share a source file: a class and its tiny helpers. Anything else gets
   its own module. When an area grows to several modules, it becomes a package, like `core/geometry/`. Tests mirror
   the source layout (`tests/core/geometry/test_vec.py` tests `core/geometry/vec.py`).

---

## 2. Tech stack and project setup

| Item          | Choice                                                                          |
|---------------|---------------------------------------------------------------------------------|
| Python        | 3.14.10 (venv `cube_net_3.14.10`)                                               |
| GUI           | PyQt6 6.12 (`QGraphicsView`-based sheet)                                        |
| Tests         | pytest, pytest-qt, hypothesis                                                   |
| Lint / format | ruff (lint + format), mypy in non-strict mode for `core`                        |
| Packaging     | `pyproject.toml` (setuptools); PyInstaller → `.deb` / AppImage later (§7, M11)  |
| App settings  | `QSettings` (face colours, last project path, recent projects)                  |
| Project file  | single file `*.cubenet`: gzip-compressed JSON with a `format_version` field     |

**Dependencies** are declared only in `pyproject.toml`; there is no `requirements.txt`:
- runtime dependencies go in `[project] dependencies` (PyQt6);
- dev tools go in `[project.optional-dependencies] dev` (pytest, pytest-qt, hypothesis, ruff, mypy).

Install or update everything in the venv with `pip install -e ".[dev]"`, run from the project root. The `-e`
(editable) install also makes `cube_net` importable from `src/`, so `python main.py` works from the IDE.

Dropped from the old `requirements.txt`:
- numpy and shapely: they work in floats, and we need exact predicates.
- pyyaml and python-json-logger: we use JSON and the standard `logging` module.

**Layout:**

```
cube_net/
├── pyproject.toml
├── main.py                      # thin launcher: from cube_net.app import main
├── docs/
│   ├── idea.txt
│   └── plan.md
├── src/cube_net/
│   ├── app.py                   # QApplication bootstrap, startup logic
│   ├── core/
│   │   ├── geometry/            # one module per closely related group of definitions
│   │   │   ├── vec.py           # Vec, to_fraction
│   │   │   ├── rigid90.py       # Rigid90: rotation k*90° + translation, compose/invert
│   │   │   ├── predicates.py    # orient, segment classification
│   │   │   └── quantize.py      # quantize(): UI floats -> Fraction (1/1000 for now)
│   │   ├── cube/
│   │   │   ├── topology.py      # CubeTopology: faces, vertices, edges, frame transitions
│   │   │   └── surface_point.py # SurfacePoint: canonical point on the cube surface
│   │   ├── net.py               # net model (DCEL), default net, queries
│   │   ├── invariants.py        # validate_net()
│   │   ├── cutline.py           # cut line in progress + validation rules
│   │   ├── split.py             # inserting the cut line into the net, halves
│   │   ├── rearrange.py         # gluing transform, overlap check, approve + auto-glue
│   │   ├── cleanup.py           # removal of redundant points
│   │   ├── bounding.py          # convex hull + minimum-area rectangle
│   │   ├── editor.py            # state machine (DEFAULT/CUTTING/CUT_EDITING/CUT_APPROVING)
│   │   ├── history.py           # undo/redo deque + redo stack with special rules
│   │   └── project.py           # project = editor state + settings + history; (de)serialization
│   └── ui/
│       ├── main_window.py       # menus, instrument panel, status bar
│       ├── sheet_view.py        # QGraphicsView: zoom, pan, scrollbars, coordinate mapping
│       ├── items/               # QGraphicsItems: sheet+grid, net, cut line, overlays
│       ├── painter/             # hatching, dashed edges, vertex circles, styles
│       ├── controllers/         # input handling per state; ruler tool
│       ├── dialogs.py           # project settings, error/unsaved dialogs
│       └── palette.py           # face colours, highlight variants, UI colours
└── tests/
    ├── core/ ...
    └── ui/ ...
```

---

## 3. Core data model

### 3.1 Numbers and geometry (`geometry/` package)
- `Vec(x: Fraction, y: Fraction)`, immutable and hashable.
- `orient(a, b, c) -> -1 | 0 | 1`, computed exactly.
- `classify_segments(p1, p2, q1, q2)` returns a `SegmentIntersection`: `DISJOINT`, `CROSSING` (one point strictly
  inside both), `TOUCH` (one common point that is an endpoint of at least one segment: shared endpoint, T-shape,
  collinear end-to-end) or `OVERLAP` (a common sub-segment of positive length). Every validity rule is built on this
  one function, so it gets the most thorough tests. `orient` doesn't tell 0° from 180°; `classify_segments` does.
- `quantize(x, y)`: UI floats → exact `Vec` rounded to 1/1000 unit (`QUANTUM`).
- `Rigid90(k, t)`: maps `p ↦ R^k·p + t`. It can compose, invert, act on points and segments, and be serialized.
  `Rigid90.from_segments(src, dst)` finds the transform that sends segment `src` onto `dst` with matching endpoints. It
  asserts that the rotation is a multiple of 90°; that assertion doubles as an invariant check.

### 3.2 Cube surface (`cube/` package)
- Six faces, numbered 1–6 as in `idea.txt`. Each face has a local frame `(u, v) ∈ [0,1]²`, chosen so that in the
  default net every face's placement is a pure translation. Example: face 2 local (0,0) ↦ sheet (11,12).
- **`CubeTopology`** (`cube/topology.py`, instance `CUBE`): the only hand-written data is the default net itself:
  the vertex labels at each face's 4 corners, plus each face's sheet origin in the default net. Everything else is
  derived and self-checked: vertex → 3 faces, 12 edges → 2 faces each, adjacency, opposite faces, and
  `transition(f, g)`, the `Rigid90` that unfolds face `f` across the shared edge into `g`'s frame. Labels A..H are
  internal ids; they're never shown to the user.
- **`SurfacePoint`** (`cube/surface_point.py`): a point on the cube surface in **canonical form**: `(face, local)`
  in the frame of the lowest-numbered face that contains it. It can be created from any containing face, and it
  also carries the derived `faces` (1, 2 or 3), `vertex` label (for cube vertices) and `edge` (for points inside an
  edge). `local_in(face)` gives its coordinates in any other containing face.

  Two `SurfacePoint`s are equal exactly when they are the same point of the cube. This is what makes "counterparts"
  and "matching" in `idea.txt` well-defined: a perimeter segment is identified by its pair of `SurfacePoint`s.
- `faces(p)` returns the face set (1, 2 or 3 faces). This drives vertex colours. A segment's colours are the
  *intersection* of its endpoints' face sets: 2 faces means a cube edge, 1 face means face colour plus white.

### 3.3 Net (`net.py`): a DCEL over the sheet plane
- **Vertex** (an *image*): its sheet position (`Vec`) and its `SurfacePoint`. Several vertices can share one
  `SurfacePoint`, like A_1, A_2 and A_3.
- **Half-edge**: origin vertex, twin, next, prev, region, and a `kind`:
  - `FOLD`: a cube edge inside the net, always drawn;
  - `SEAM`: an inner glued user cut, never drawn;
  - `BOUNDARY`: a perimeter cut.

  Boundary half-edges have no twin inside the net; their **counterpart** is found by `SurfacePoint` pair.
- **Region**: a polygon that lies in exactly one cube face. It stores the face id and a `Rigid90` placement
  (face-local → sheet), which the hatching and colour code use. Regions can be non-convex.
- **Perimeter**: the single boundary cycle of half-edges. Touching parts of the net mean the same sheet position can
  appear more than once in the cycle; that's allowed.
- Lookup indices: `SurfacePoint → [vertex images]` and `(SurfacePoint, SurfacePoint) → [boundary half-edges]`.
  They're rebuilt after each structural operation, which is cheap at this size.
- `default_net()` builds the cross with 6 regions, 5 fold edges, 14 boundary segments and 14 boundary vertices,
  using the coordinates from `idea.txt`.

### 3.4 Invariants (`invariants.py`)

`validate_net(net)` checks:
1. The DCEL is consistent: next/prev/twin are mutual, and every cycle closes.
2. The total area of all regions is exactly 6.
3. Every region's vertices share exactly one common face, and it equals the region's face id.
4. Each boundary segment has **exactly one** counterpart, which is a different boundary half-edge.
5. Counterparts have **identical subdivisions**: every split point on one exists on the other.
6. Every cube vertex appears only on the perimeter.
7. No region interiors overlap (§4.5); touching is allowed.
8. Every region's placement is consistent with its vertices' local coordinates (`placement(local) == position`).
9. In DEFAULT state: no `SEAM` edges, no inner vertices and no redundant perimeter points (§4.6).

---

## 4. Core algorithms

### 4.1 Hit-testing and nearest-point (core, in sheet units)
- `nearest_boundary_segment(p, max_dist, side="inside")`: the "hitbox inside the face" rule. A boundary segment is a
  hit only if `p` lies on the region's side of it within `max_dist`. `max_dist` comes from the UI and is converted
  from pixels to units. When two parts touch, each side reaches only its own segment.
- `project_onto_segment(p, seg)` gives the closest point, clamped to the closed segment (endpoints included).
- `point_in_net(p)`: point location in regions.

### 4.2 The cut line in progress (`cutline.py`)
- Data: an ordered list of 2 to 51 points. The first and last points are attached to a boundary half-edge and a
  parameter along it; inner points are free sheet positions. The data also includes the counterpart images
  inserted for each endpoint (the z_3 rule).
- Validation functions return either OK or the offending segments, so the UI knows what to flash black:
  - `can_add_point(p)`: the new segment last→p is strictly inside the net. It doesn't touch the perimeter except
    at p, when p is an endpoint on the boundary, and it doesn't touch the other cut-line segments except at the
    shared endpoint. A collinear back-track counts as a violation.
  - `can_delete_point(i)`: the segment P(i-1)→P(i+1) follows the same rule.
  - `can_move_point(i, p)`: same rule for the 1 or 2 moved segments.
  - Endpoint rules: the two endpoints can't be the same net point. They *may* be two images of one `SurfacePoint`.
    A direct first segment along the start's own boundary segment is rejected.
- Counterpart image insertion: an endpoint at `SurfacePoint s` on boundary segment `X_i–Y_j` inserts a vertex for
  `s` into the counterpart `X_k–Y_m` right away. Moving the endpoint moves that image too; removing the endpoint
  removes it.

### 4.3 Splitting the net along the cut line (`split.py`)
- Insert the cut line into the DCEL. Break each cut-line segment at every crossing with a `FOLD` edge (a cube edge),
  so each piece lies in a single region (`idea.txt` note 3). There are no inner vertices or seams in DEFAULT state
  (§4.6), so a fold crossing is the only kind of break. New crossing
  points get `SurfacePoint`s computed from the region placement.
- The new edges become two boundary half-edges (one per side) that coincide geometrically. They're counterparts.
- Compute the **two halves** with a flood fill over regions that doesn't cross the cut line.
- This happens when entering CUT_APPROVING. While editing, the cut line is an overlay and the net is untouched,
  apart from the endpoint counterpart images.

### 4.4 Rearrangement (`rearrange.py`)
- Clicked boundary segment `S` in half H1; its counterpart `S'`:
  - if `S'` is in H1, reject (flash black);
  - if the click is on the cut line itself, ignore it.
- `T = Rigid90.from_segments(S', S)` with matching `SurfacePoint`s. Apply `T` to every vertex of the half that
  contains `S'`, and compose `T` into those regions' placements.
- The result is a *candidate* net. It is **not glued yet**: `S` and `S'` coincide but stay separate boundary
  half-edges until approval. Store the candidate together with which segment pair is meant to be glued.

### 4.5 Overlap check: what "self-intersection" means
The criterion: region interiors must not overlap. Implementation, in O(n²) over boundary segments, which is fine
at this size:
1. **Proper crossings** of two boundary segments are a violation. Mark both segments.
2. **Collinear overlaps**: compare which side the net lies on for each segment. Opposite sides means touching (OK);
   the same side means a violation.
3. **Coincident points**, i.e. all vertex images and T-touch points at the same sheet position: build the angular
   *wedges* the net occupies around that point, one per incident corner. If any two wedges overlap in a positive
   angle, it's a violation. This one rule covers "vertex pokes through a segment", point-touching (OK) and corner
   cases at reflex vertices.
4. Covering only, with no boundary crossings, is impossible here, because both halves meet along `S`. So 1–3 are
   enough. The proof sketch goes into the module docstring, and a test guards it.

Output: OK, or the set of boundary half-edges to draw in black.

### 4.6 Approval: glue, auto-glue, cleanup (`rearrange.py`, `cleanup.py`)
1. Glue `S` with `S'`: merge their endpoint vertices and make the pair twins with kind `SEAM`, or `FOLD` if the
   segment lies on a cube edge.
2. **Auto-glue** (`idea.txt` note 5): from each end of `S`, walk along the perimeter on both sides in step. The next
   pair is glued while it is made of the same two `SurfacePoint`s *and* now coincides point-by-point. Stop at the
   first pair that fails.
3. **Cleanup** (note 6):
   - Dissolve every `SEAM`: an inner glued user cut carries no information. That merges the two regions of the same
     face it separated.
   - Remove every vertex that is now inside the net: it's never a cube vertex (§3.4 item 6). If it lies on a cube
     edge, the two `FOLD` pieces it separated are merged into one.
   - Remove perimeter points that aren't cube vertices or branching points, where every image has the perimeter
     passing straight through and both adjacent cuts have the same colours. Merge those adjacent cuts in *all*
     images.
   - So the net in DEFAULT state never has inner `SEAM` edges or inner vertices. `SEAM` exists only transiently.
4. Run `validate_net()`.

### 4.7 Bounding rectangle (`bounding.py`)
- Exact convex hull (Andrew's monotone chain) over all boundary vertex positions.
- For each hull edge `e = (dx, dy)`, the area of the edge-aligned rectangle is
  `(max·e − min·e) · (max e×p − min e×p) / |e|²`. This is **rational**, so the minimum area is exact and the
  `< threshold` comparison is exact too. Rectangle corners are only needed as floats, for drawing.
- It works on any candidate net, including invalid ones.
- Test values: the default cross gives 12, and other known hexomino nets give known areas.

### 4.8 Sheet bounds
The bounding box of the net plus 5 units on each side, recomputed whenever the net changes, including while in
CUT_APPROVING.

---

## 5. Editor state machine and history

### 5.1 `Editor` (`editor.py`)

| State         | Data                                            | Allowed user actions                                        |
|---------------|-------------------------------------------------|-------------------------------------------------------------|
| DEFAULT       | net                                             | click a boundary segment → #1 (first point) → CUTTING      |
| CUTTING       | net, cut line (open)                            | click inside → #1; click on boundary → #1 → CUT_EDITING    |
| CUT_EDITING   | net, cut line (closed), endpoint images         | midpoint circle → #1; Shift+click → #2; drag → #3; click a boundary segment → #4 → CUT_APPROVING |
| CUT_APPROVING | candidate net, glue pair, validity result       | Ctrl+Enter / ✓ (only if valid) → #5 → DEFAULT             |

Undo and redo are available in every state. Each public method either performs one action, or returns a
`Rejection` describing what to flash (segments, and the 200 ms "black" hint). The editor never touches Qt.

### 5.2 History (`history.py`)
- `done: deque[Entry]` with `maxlen=1000`, plus `undone: list[Entry]`.
- `Entry = (type, payload_before, payload_after)`:
  - #1–#3: just the cut-line data before and after (small);
  - #4: the cut-line/net state before, and the candidate after;
  - #5: the candidate before, and the glued net after.

  Net snapshots are plain dicts, and gzip keeps the file small.
- Rules from `idea.txt`:
  - a new action clears `undone`;
  - undoing #5 also undoes the #4 before it, if that #4 is still in `done`;
  - redo always redoes **exactly one** entry;
  - undoing a #4 that produced an invalid candidate drops it, so it isn't pushed to `undone`;
  - the redo stack is saved into the project.
- Tests: table-driven scenarios, including trimming at 1000 entries when the oldest entry is a #5 or a #4.

### 5.3 Project (`project.py`)
- `Project = {format_version, editor_state, settings: {area_threshold: "7.100"}, history}`.
- The threshold is stored as a decimal string, validated as positive, at most 3 decimals and at most 12.000.
- Saving writes to a temp file, then renames it, so a crash can't corrupt the project.
- Loading validates the version and structure and runs `validate_net`. Any failure is reported to the user
  (startup flow, §6.6).

---

## 6. UI layer

### 6.1 Main window
- **Menu:**
  - File: New, Open…, Save (Ctrl+S), Save As…, Project settings…, Quit;
  - Edit: Undo (Ctrl+Z), Redo (Ctrl+Y).
- **Instrument panel:**
  - Ruler toggle;
  - bounding-rectangle toggle with the area label (3 decimals);
  - approve ✓ button (Ctrl+Enter), enabled only for a valid candidate.
- **Status bar:** mouse coordinates in sheet units with 3 decimals, plus the current state name. The state name helps while
  developing and may stay.

### 6.2 Sheet view (`sheet_view.py`)
- A `QGraphicsView` with scrollbars. Scene units are cube units with Y flipped (`scale(s, -s)`), so the core's
  coordinates are used as-is.
- **Zoom:**
  - mouse wheel, only while the cursor is over the sheet rectangle;
  - the point under the cursor stays fixed;
  - the provisional limits from `idea.txt` are implemented as one replaceable function.
- **Initial zoom:** the default net (4 units tall) takes 50% of the *screen* height, using the screen the window is
  on.
- **Pan:**
  - left-drag on empty space outside the net, when the click means nothing else (never while the ruler is active);
  - scrollbars.
- When the sheet bounds change, the net stays at the same screen position: the view is adjusted, not the net.

### 6.3 Items and painting
A few custom items with hand-written `paint()` methods, not thousands of small items:
- `SheetItem`: white background and the light-grey 1×1 grid.
- `NetItem`, painted bottom to top:
  1. Hatch fill, per region: clip to the region polygon, apply the region placement, then draw the 10×5 cells, each
     split into a white lower triangle and a coloured upper triangle in face-local coordinates. Cache one
     `QPainterPath` per face pattern. The fill hides the grid.
  2. `FOLD` edges: two-colour dashes, centred on the line.
  3. Boundary cuts: dashes drawn **inside** the region, offset inward by half the line width. Dash length is 1/20
     unit, with the phase anchored to the position along the cube segment, so both counterparts look identical.
     Colours: 2 faces, or face colour plus white.
  4. Vertex circles, centred on the true position, with equal sectors for now (1, 2 or 3 colours).
- `CutLineItem`: the cut line in progress, in "highlighted" colour variants. It shows hollow midpoint circles in
  CUT_EDITING and the rubber-band segment in CUTTING (hidden while the ruler is active).
- `OverlayItem`:
  - hover highlight;
  - black flashes (a `QTimer`, 200 ms);
  - the segment chosen for gluing in CUT_APPROVING;
  - black overlap segments;
  - the bounding rectangle: thin black, or green under the threshold.
- `RulerItem`: points, lines, coordinate labels and distance labels, all with 3 decimals.
- Line widths, hitbox widths and circle radii are in **pixels**, constant on screen at any zoom, as decided. They're
  converted to units for hit-testing at the current zoom. If the user zooms far out, lines can be wider than faces;
  that's accepted.

### 6.4 Controllers (`controllers/`)
- One controller per editor state, which translates Qt events into editor calls. Precedence:
  1. ruler active → ruler;
  2. otherwise the state controller;
  3. otherwise, outside the net, panning.
- Hover: the nearest boundary segment within the inside-hitbox is highlighted, in DEFAULT, CUTTING (when about to
  end) and CUT_EDITING.
- Dragging cut-line points shows the live position; the result is validated on release (§4.2).

### 6.5 Blinking and colours (`palette.py`)
- Face colours come from `QSettings`, with the defaults from `idea.txt`. Each colour also has a derived
  "highlighted" variant.
- The bounding-rectangle button blinks at 6 changes per second (a 167 ms `QTimer`) while area < threshold. The area
  label and the rectangle turn green.
- The "success" green is a separate palette entry that must be clearly different from face 3's #008A4B. Start with
  a bright lime such as #39D353 and tune it in M4 by looking at it next to face 3.

### 6.6 Startup and files
- On start, open the last *saved* project path from `QSettings`:
  - no path: start a new untitled project with the default net;
  - loading fails: show the error and offer to create a new project (or Open…).
- New/Open/Quit when there are unsaved changes: ask "Save changes?" with Save / Don't save / Cancel. A dirty flag is
  set by every history action and cleared on save. Closing the window counts as Quit.

---

## 7. Milestones

**Vertical slices.** Every milestone delivers a feature end to end: core logic, its UI, and tests. Inside a
milestone, work goes one class/module at a time, and **as soon as some logic can be shown or used in the app, its UI
part is built right away**, before more logic is added. Every step marked 👁 ends with something you can try in
`python main.py`. Tests stay green after every step.

| #   | Milestone                         | Steps (👁 = you can try it in the app afterwards)                                                                                   | Done when |
|-----|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|-----------|
| M0  | Project setup                     | `pyproject.toml`, package layout, ruff, mypy, pytest/pytest-qt/hypothesis, thin `main.py`                                           | **Done.** |
| M1  | Geometry kernel                   | `Vec`, `orient`, `classify_segments`, `Rigid90`, `quantize`                                                                         | **Done.** |
| M2  | Sheet and the static default net  | 1. `CubeTopology`, `SurfacePoint` (**done**). 2. 👁 (**done**) Sheet view: white sheet with the 1×1 grid, Y-up coordinates (H_1 = (11,12)), mouse coordinates with 3 decimals in the status bar, initial zoom (net = 50% of screen height), mouse-wheel zoom around the cursor with the provisional limits, scrollbars, left-drag panning outside the net. The sheet bounds come from the 6 default face squares for now. 3. Net model (DCEL) with `default_net()`: regions, fold edges, boundary segments, vertex images. 4. 👁 Net painting: hatch per face, two-colour dashed fold edges and cuts (drawn inside the faces), vertex circles. 5. 👁 Hover highlight of cuts (needs hit-testing, §4.1). | The cross looks and behaves as specified |
| M3  | Ruler                             | 1. Ruler model (points, segment lengths; no history). 2. 👁 Ruler toggle on the instrument panel, points, lines, coordinate and distance labels, panning disabled while active. | Behaviour as specified |
| M4  | Bounding rectangle                | 1. `bounding.py` (exact hull + minimum-area rectangle). 2. 👁 Area label, toggle button, rectangle drawing, green colouring and blinking below the threshold (fixed 7.100 until M9). | 12.000 for the cross |
| M5  | Cut line                          | 1. Cut-line model and validation rules (§4.2). 2. 👁 DEFAULT → CUTTING → CUT_EDITING in the app: start on a cut, add points, rubber band, black flashes on rejection. 3. Endpoint counterpart images (z_3). 4. 👁 Midpoint circles, Shift+click delete, dragging points (endpoints along their segment). | Every CUTTING/CUT_EDITING rule from `idea.txt` is covered by core tests and usable in the app |
| M6  | Rearrange and the overlap check   | 1. Splitting the net along the cut line, the two halves (§4.3). 2. Rearrangement (§4.4). 3. 👁 Clicking a segment moves the other half (CUT_APPROVING), the glued segment is shown, a counterpart in the same half flashes black. 4. Overlap check (§4.5). 5. 👁 Overlapping segments in black, ✓ button enabled only when valid. Bounding rectangle follows the candidate. | The corner-cut example from `idea.txt` reproduces exactly in the app |
| M7  | Approve                           | 1. Gluing, auto-glue walk, cleanup (§4.6), `validate_net()` (§3.4). 2. 👁 ✓ button and Ctrl+Enter accept the cut; you can keep cutting the new net. | All **11 hexomino nets** are reachable from the cross (core scenario test) and in the app |
| M8  | Undo / redo                       | 1. `history.py` with every special rule (§5.2). 2. 👁 Ctrl+Z / Ctrl+Y and Edit menu items, in every state.                         | Table-driven history tests pass; works in the app |
| M9  | Projects                          | 1. Serialization of the editor state and history. 2. 👁 File menu: New/Open/Save/Save As (Ctrl+S), unsaved-changes prompt, startup flow (reopen last saved project). 3. 👁 Project settings dialog (area threshold). | Save → restart → identical state with full undo/redo |
| M10 | Polish                            | Colour variants for the new cut line, cursor shapes, performance check at about 50 cuts, anything found while trying the app      | Smooth interaction with a heavily cut net |
| M11 | Packaging                         | PyInstaller one-folder build → `.deb` and/or AppImage for Ubuntu 24; later macOS (`.app`/`.dmg`) and Windows                       | Install on a clean Ubuntu VM and run |

M7's "all 11 nets" scenario is the main acceptance test for the whole topology engine. It's written against the
core API with exact coordinates, so it doesn't need snapping.

---

## 8. Open questions and deferred topics

Deferred on purpose (per `idea.txt`):
- **Snapping** of points to vertices, edges and the grid. It plugs into `quantize()` and the hit-testing.
- **Vertex circle sectors**: their orientation towards net faces, and possibly unequal sizes.
- **Zoom limits**: revisit the provisional rules.
- **Editing face colours** in app settings.
- **Distinguishing** several user-made vertices that sit on the same cube face.

Resolved:
- "Save changes?" prompt on New/Open/Quit: yes (§6.6).
- Line widths, hitbox widths and vertex radii: constant in pixels (§6.3).
- Mouse input is rounded to 1/1000 unit until snapping exists (§1, `quantize()`).
- The success green differs from face 3's green (§6.5).
- Coordinates are shown with 3 decimals (§6.1, §6.3).

No open questions remain right now. New ones will be added here as milestones uncover them.
