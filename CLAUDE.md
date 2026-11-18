# Cube Net: rules for Claude sessions

## The task list (the desktop app's list under the latest message)
The user follows the work on that list, not by reading the messages, so it must always show where the work is:
- The first tool call of every request that edits files or runs more than one command goes out together with
  `update_plan` and the whole plan, the first step "in_progress".
- The tool call that starts a step goes out together with `update_plan` `{"advance": true}`. Never do the work of the
  next step (a read, an edit, a test run) before that call has gone out.
- When the steps are done out of order, say so at once (`{"done": [...], "start": n}`); when the plan changes, send the
  new whole list.
- Before `wrap_up`, check: the step shown "in_progress" is the one actually being finished.

## Russian texts
Translate what the English says, faithfully: no paraphrasing into something shorter or "nicer" that changes its
meaning. When unsure of a wording, ask.
