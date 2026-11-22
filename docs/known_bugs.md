# Known bugs

Bugs found and not fixed yet. Coordinates are the ones the app shows (the origin where a new project or template has
it), vertices by their names. Remove an entry once its fix is in.

## Crashes

- **Dragging a cut line's inner point onto its first or last point crashes (labels shown).** In a new Cube: a line
  from A1 (11, 14) through (23/2, 27/2) to the cut at (12, 27/2), finished. Dragging (23/2, 27/2) onto (11, 14) or
  onto (12, 27/2) raises AssertionError (`real_cut.cycle_of`: `point.edge is not None`) while the drag is shown:
  `Workspace.show_labels` names the points of the line as drawn, the dragged point is a point of no cut that lies on
  the perimeter, and `real_cut` takes it for where a piece starts. With the vertex labels hidden (L) it doesn't
  happen; dragging it onto another point of the perimeter, (11, 13), doesn't either.
- **A saved last view far off the sheet crashes the start.** With `project/last_view` in the settings holding a
  sheet point outside what a scroll bar can reach (x or y beyond about ±2·10⁹ pixels at that zoom: `30000000 0 1`,
  `1e300 1e300 1`), reopening the last project raises OverflowError in `SheetView.pan_by` (from `show_place`). Only a
  damaged or hand-edited settings file has such a value, but `AppSettings.last_view` promises that anything wrong
  with what's stored gives None.

## Smaller issues

None known.
