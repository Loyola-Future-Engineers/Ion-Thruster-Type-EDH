# Progress log

Read this first when resuming. Newest entries at the top of each section.

## Status
- Session started 2026-10-28. The Claude Code session was **not** running inside tmux/screen, so it will not survive an SSH/terminal disconnect.
- No GitHub remote is configured. All commits are local. Pushing needs a remote (for example `gh repo create`), which the owner has not authorised yet.

## Completed milestones
1. Repository framework, isolated Python environment, environment record (`docs/environment.md`).
2. Axisymmetric charge-simulation electrostatic solver (`src/ehd/csm.py`) with verification tests.
3. Reduced-order multi-stage device model (`src/ehd/device.py`).

## Current work
- Physics documentation and literature review.

## Validation status
- Verified (code against exact/classical results): ring-charge field, torus and disc capacitance, Peek reference value, Townsend scaling, energy bound.
- **Not validated against experiment.** No physical measurements exist for this project.

## Known problems
- Space charge is neglected in the field and ion-path calculation.

## Remaining tasks
See the milestone list in the README.
