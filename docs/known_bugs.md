# Known bugs

Bugs found and not fixed yet. Coordinates are the ones the app shows (the origin where a new project or template has
it), vertices by their names. Remove an entry once its fix is in.

## Crashes

- **A saved last view far off the sheet crashes the start.** With `project/last_view` in the settings holding a
  sheet point outside what a scroll bar can reach (x or y beyond about ±2·10⁹ pixels at that zoom: `30000000 0 1`,
  `1e300 1e300 1`), reopening the last project raises OverflowError in `SheetView.pan_by` (from `show_place`). Only a
  damaged or hand-edited settings file has such a value, but `AppSettings.last_view` promises that anything wrong
  with what's stored gives None.

## Smaller issues

None known.
