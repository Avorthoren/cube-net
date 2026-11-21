# Known bugs

Bugs found and not fixed yet. Coordinates are the ones the app shows (the origin where a new project or template has
it), vertices by their names. Remove an entry once its fix is in.

## Crashes

Each one ends in the crash report window, and the app closes (unsaved work is lost).

### Approving some cuts from the hole's corner (Cube with a hole)

1. File → New → Cube with a hole.
2. Click vertex I₁ (−1, 11), then the boundary point (5, 3.5), on the cut O₂–Q₂.
3. Click the cut from U₂ (7, 8) to O₁ (7, 9), near U₂: the halves are rearranged (valid).
4. Approve.

`ValueError: NetVertex… has 3 edges, expected 2`, in `net/surgery.py` `dissolve_vertex` (from `approve` →
`_remove_inner_vertices`). Cuts from P₁ (−1, 9) to the same point, and from L₁ (−3, 11) to (4, 15.5) on S₁–B₁, fail
the same way. Found 2026-11-22.

### Dragging a hole's vertex past a fold line (template)

1. Open the Cube with a hole template.
2. Drag vertex N₁ (−3, 9), a corner of the hole, to (1, 9). (0.5, 9) and (1.5, 8.5) crash too; (0, 9) is refused
   properly, as a crossing.

`ValueError: min() iterable argument is empty`, in `template/holes.py` `faces_from_graph` (from `recut`, via
`move_problem`). Found 2026-11-21.

### Closing a hole whose last side crosses another of its sides (template)

1. Open [known_bugs/hole_closing_crash.nettemplate](known_bugs/hole_closing_crash.nettemplate): the Cube with a hole
   template as a random session left it, a second hole being drawn: (7.466, 3.247), (2.5, 1.5), (2.5, 7.19),
   (2.093, 1.256), (2.093, 9.718), (2, 3.5).
2. Click its first point, (7.466, 3.247), to close it.

Closing it should be refused (the closing side crosses one of the hole's sides); instead
`ValueError: min() iterable argument is empty`, in `template/holes.py` `faces_from_graph` (from `add_hole_point` →
`closed_hole`). The same points on the unchanged template are refused properly, so it takes that template's other
changes too. Found 2026-11-21.

## Smaller issues

### A misleading message for a point far off the net

On the cube, with a cut started at A₁, typing (−5, −5) in Place a vertex says the line "would touch the perimeter, or
touch or cross itself": the point isn't on the net at all. Found 2026-11-21.
