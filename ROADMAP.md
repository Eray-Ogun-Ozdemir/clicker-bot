# Clicker Bot roadmap

These are proposed improvements, ordered by the value they bring to recording, editing and debugging browser workflows.

| Priority | Feature | First usable version | Status |
| --- | --- | --- | --- |
| 1 | Recording inspector | Open a recording and see each step's action, target and value. Highlight the current step during playback and keep the failed step selected. | Done |
| 2 | Step editor | Edit, reorder or remove recorded steps and save a copy. Open existing JSON recordings with their original step order and viewport. | Done |
| 3 | Manual workflow builder | Enable the manual preparation option. Create a workflow from a starting URL and add click, fill and Enter steps through the same editor. | Planned |
| 4 | Waits and playback controls | Add a wait for an element to become visible, a configurable timeout and a stop button that closes the playback browser. | Done |
| 5 | Assertions and failure details | Check expected text or a destination URL. Show expected and actual results alongside the failed step, with an optional local screenshot. | Done |
| 6 | Recording collections | Group saved workflows by project in the sidebar and reopen a recording by name. | Planned |
| 7 | Test data variables | Supply different input values at playback time so one recording can cover multiple test cases. | Planned |
| 8 | Additional browser interactions | Extend recording and playback to dropdown selections, checkboxes and new tabs, with a round-trip test for each interaction. | Dropdowns, holds and drag and drop are recorded; scroll, hover, double-click, right-click and key presses can be added in the inspector; checkboxes and new tabs open |

## Suggested first milestone

Start with the recording inspector. Given a saved flow that clicks a button and fills a field, opening the file should display both steps in order. During replay, the highlight should follow execution. If the field disappears, the inspector should identify the failed step and show the error. This same view can later support editing and manual entry.
