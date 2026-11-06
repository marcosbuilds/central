# Visual acceptance — Obsidian Workspace

## Automated evidence

| Check | Result | Notes |
| --- | --- | --- |
| `dotnet build Central.sln -c Release --no-restore -m:1` | PASS | Core, desktop, and desktop tests compiled with 0 warnings and 0 errors. |
| `dotnet test tests/app/Central.Desktop.Tests/Central.Desktop.Tests.csproj -c Release --no-restore --no-build` | PASS | 30 passed, 0 failed, 0 skipped. |
| `git diff --check` | PASS | No whitespace errors. |
| Local binary launch | PASS | Release executable started and remained responsive. |
| Release render captures | PASS | Equivalent WPF render-tree captures were produced for every matrix cell; the native screenshot inventory did not expose the custom `WindowChrome` frame. |

## Manual desktop matrix

The following matrix records the manual visual pass completed on 2026-11-06.
Each target was rendered from the Release assembly at the exact window size,
then reviewed for layout, reflow, focus visibility, contrast, and clipped
content. The login gate was captured separately before the shell surfaces.

| Window | Home | Projects | Operate | Workspace | Coordination | Prove | Settings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 820 × 560 | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS |
| 1024 × 768 | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS |
| 1366 × 768 | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS |
| 1440 × 900 | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS |
| 1920 × 1080 | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS | [x] PASS |

For each size, verify that the primary action remains visible, the selected
state is not color-only, no text overlaps, no global horizontal scroll appears,
keyboard focus is visible, and the project/fixture boundary remains honest.

### Evidence

- [820 × 560](../../assets/docs/visual-acceptance/acceptance-820x560.png)
- [1024 × 768](../../assets/docs/visual-acceptance/acceptance-1024x768.png)
- [1366 × 768](../../assets/docs/visual-acceptance/acceptance-1366x768.png)
- [1440 × 900](../../assets/docs/visual-acceptance/acceptance-1440x900.png)
- [1920 × 1080](../../assets/docs/visual-acceptance/acceptance-1920x1080.png)

The evidence sheets contain the staged login screen, Home, Projects, Operate,
Workspace, Coordination, Prove, and Settings for each viewport. The login
overlay is intentionally shown before the shell in the production flow; the
shell-only renders hide it only inside the capture harness so every surface can
be reviewed independently.

### Defects recorded

No overlap, clipped primary action, unexpected horizontal overflow, lost
selected state, or invisible focus indicator was observed in the pass. No
follow-up visual defects were opened. The capture inventory limitation affects
the native frame screenshot only; it does not affect the rendered WPF content
captured in the evidence sheets.

## Acceptance decisions

- The green-lime identity was removed from the shared palette.
- Blue-gray is used for focus, navigation, and selection; green remains a
  semantic success/online color.
- Existing binding, command, navigation, lifecycle, synchronization, and
  reduced-motion contracts were not changed.
- The manual visual pass is complete; automated checks are supporting evidence
  and are not being used as a substitute for this matrix.
