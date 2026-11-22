# Additional template checks: ideas

Ideas for checks that would reject templates which pass today's validation but aren't the net of any body. Nothing
here is implemented. Written on 2026-11-22.

## The requirement

Validation must never reject a template that really is a body's net (no false positives), with one exception imposed
by the app's design: counterparts are parallel or perpendicular. So a new check may reject a template only when it has
**proved** that no body exists; whenever it can't decide, it accepts.

## The example that slips through now

Cube with a hole, with P₂, N₂, L₂, I₂ and P₃ moved the same distance to the right (or left). The editor takes every
move, and the template keeps all the rules and passes Validate (checked for shifts of 1/2, 1 and 2 to the right and
1/2 and 1 to the left).

Today's checks are about the gluing: every boundary segment has one counterpart of the same length, running the other
way, parallel or perpendicular; pieces of one colour glue into one flat face; and so on. The example keeps all of
that. What it breaks is **closure in 3D**: the faces can't be placed in space so that glued edges meet.

The cube's edge there is 4. The strip from x = 5 to x = 9 holds the four walls of the tunnel, and its width along x is
the tunnel's length. Moving its right side by d makes the walls 4 + d long, while the front and back faces, where the
tunnel starts and ends, are still exactly 4 apart.

## The checks, cheapest first

### 1. No shortcuts (the triangle inequality)
Within a face, the distance between two of its points is their true 3D distance, and a straight line in 3D is never
longer than any path over the surface. So every such distance must equal the shortest path between the two points in
the graph of all co-face distances (no chain of other known distances may be shorter).

- No 3D model is needed: a face is a flat piece of the body, an exact copy of its picture in the template, so two
  points of one face are as far apart in 3D as in the template's plane (even where the segment between them leaves a
  non-convex face). A face of several pieces of one colour: their coordinates in the flat face that validation already
  glues them into.
- Sound, cheap (a shortest-path search over a few dozen points).
- **Exactness:** not with fractions. The distances are square roots of rational numbers, and comparing sums of them
  exactly is possible (repeated squaring) but gets expensive as the sums grow. In practice: high-precision interval
  arithmetic, rejecting only when the whole interval excludes equality.
- Catches only gross stretching: walls longer than the way round over the front, a side and the back. The example's
  small shifts pass.

### 2. Every corner must exist
At a body vertex where faces with angles a₁, …, aₙ meet (n ≥ 3), the angles form a closed chain of arcs on a small
sphere round the vertex, so each arc's ends are joined by the chain of all the others too:

  min(aₖ, 2π − aₖ) ≤ Σ aᵢ (i ≠ k), for every k.

- The left side is the distance across arc k: a face's angle may be reflex (an L-shaped face, or the front face of
  Cube with a hole at a corner of the hole: 270°), and then it's 2π − aₖ, not aₖ.
- **No upper limit on the total.** Σ aᵢ ≤ 2π holds only at convex corners; at a saddle-like corner the angles add up
  to more. Cube with a hole, valid as it is, has such corners: at each corner of the hole on the front face, the
  front face's 270° and two walls of 90° make 450°.
- Any number of faces: n = 3 is special only for check 3 (a three-face corner is rigid), not here.
- Sound. Equality means a flat, degenerate corner: accept it rather than risk a false rejection.
- **Exactness: exact, with fractions.** An angle is never computed as a number. The angle between two rational
  vectors u and v is kept as the complex number z = conj(u)·v (rational parts; its direction is the angle, its length
  doesn't matter) together with a count of full turns. Adding angles multiplies these numbers (still rational) and
  carries a full turn when the sum passes 2π; comparing two angles compares full turns, then which half of the circle
  each direction is in, then the sign of a cross product. π is −1, 2π a full turn, and 2π − a is the conjugate with
  the turns adjusted. The numbers grow with each product, but a corner has only a handful of faces.
- Catches corners that can't be built at all; not the example.

### 3. Rigidity propagation (catches the example)
- A three-face corner is rigid: its face angles fix the dihedral angles of its three edges (the spherical law of
  cosines).
- An edge whose dihedral angle is known joins its two faces into one rigid cluster. Two clusters sharing three body
  points that aren't on one line merge too.
- At a vertex with n faces, once n − 3 of its dihedral angles are known, the remaining three follow.
- Repeat until nothing changes. Wherever a rigid cluster determines the distance between two points, and a face (or
  another way through the clusters) gives a different one: reject.

On the example: the cube's eight outer corners are three-face corners with 90° angles, so every outer dihedral angle
is 90° and the outer shell becomes one rigid cluster. The front and back corners of the hole are then 4 apart, but the
walls say 4 + d: rejected. A shift to the left the same way.

Making it sound:
- **Exactness: not with fractions.** Cosines of angles between rational vectors involve square roots, and so do the
  dihedral angles and the distances they force. Use interval arithmetic at high precision (or exact algebraic
  numbers, at a much higher cost) and reject only when the whole interval excludes equality. A real mismatch smaller
  than the precision is accepted: a miss, never a false rejection.
- **No 3D model** either: it works with face angles and dihedral angles, and only asks what distance a rigid cluster
  forces between two points.
- **Mirror images.** A hinge with a known angle D can bend either way (±D). Where a cluster is reached along different
  routes, every combination of those choices has to be tried, and rejection is allowed only if all of them conflict.
  Clusters are small and conflicts show early, so the branching stays manageable.
- **Undecided.** Where propagation stops (no three-face corners, or a body that really is flexible: flexible
  polyhedra exist), nothing is asserted and the template is accepted.

### 4. Self-intersection, when the body is pinned down (optional)
If propagation determines the whole body (up to a mirror image), its shape is known, and a test can reject one whose
faces pass through each other: shapes that "close" only by crossing themselves. This is the only check that builds the
body in 3D; its coordinates involve square roots, so it needs the same interval arithmetic as check 3.

## What would still get through

- Bodies without three-face corners (say, one with four faces at every vertex, like an octahedron): propagation never
  starts, so a wrong closure there stays unnoticed. Catching those needs global arguments, such as Cauchy's rigidity
  of convex shells, which can be proved for convex bodies but not in general.
- A numeric search for a 3D realisation could say "no body found", but not finding one isn't a proof: it could only be
  a hint that doesn't block anything, never a rejection.

## Effort and risks

- Checks 1 and 2 are small. Check 3 is the real work: the body's faces, corners and hinges (from `body_from_template`),
  the propagation, interval arithmetic and the mirror branching. Probably about the size of today's validation module.
- The main risk is a soundness bug that rejects a real body. Guard against it with tests that every known valid body
  still passes: the 11 cube nets in every turn and scale, the T2 test bodies (the 1×1×2 box, the L-shaped prism, the
  pillows), Cube with a hole, the templates in `projects/`. And tests that the shifted Cube with a hole and its
  relatives (walls stretched or shrunk, a hole moved on one face only) are rejected.
- The message could name the conflict, like: "the walls between P₂ and P₃ would have to be 4 long, but they're 5".
