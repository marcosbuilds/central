# Visual acceptance — Obsidian Workspace

## Automated evidence

| Check | Result | Notes |
| --- | --- | --- |
| `dotnet build Central.sln -c Release --no-restore -m:1` | PASS | Core, desktop, and desktop tests compiled with 0 warnings and 0 errors. |
| `dotnet test tests/app/Central.Desktop.Tests/Central.Desktop.Tests.csproj -c Release --no-restore --no-build` | PASS | 30 passed, 0 failed, 0 skipped. |
| `git diff --check` | PASS | No whitespace errors. |
| Local binary launch | PASS | Release executable started and remained responsive. |
| UI Automation screenshot | LIMITED | The capture helper did not expose the locally built custom-`WindowChrome` window. |

## Manual desktop matrix

The following matrix is the required human pass before merging. It is included
here so the visual contract remains explicit rather than inferred from a build.

| Window | Home | Projects | Operate | Workspace | Coordination | Prove | Settings |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 820 × 560 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 1024 × 768 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 1366 × 768 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 1440 × 900 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 1920 × 1080 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

For each size, verify that the primary action remains visible, the selected
state is not color-only, no text overlaps, no global horizontal scroll appears,
keyboard focus is visible, and the project/fixture boundary remains honest.

## Acceptance decisions

- The green-lime identity was removed from the shared palette.
- Blue-gray is used for focus, navigation, and selection; green remains a
  semantic success/online color.
- Existing binding, command, navigation, lifecycle, synchronization, and
  reduced-motion contracts were not changed.
- A live pixel comparison is still a manual follow-up because the local binary
  could not be captured by the available Windows screenshot inventory.
