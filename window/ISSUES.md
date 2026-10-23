# Windows — status and open items

The Windows app was rewritten to follow the macOS design (parallel instances via `--user-data-dir`, Settings with profile CRUD, square dark-orange UI). Items from the review of the original junction-based version:

| # | Original issue | Status |
|---|---|---|
| W-1 | `rmtree` of the real data folder when a backup existed | ✅ Gone — no junction, original data is never touched |
| W-2 | Hard kill with `TerminateProcess` | ✅ `WM_CLOSE` first, terminate only after 10 s |
| W-3 | Launch fallback never ran, errors swallowed | ✅ Errors are raised and shown |
| W-4 | Hard-coded MSIX package/AUMID | 🟡 Executable auto-detected (Store, per-user, Program Files) and configurable |
| W-5 | Junction removal errors swallowed | ✅ No junctions |
| W-6/W-7 | Fixed sleeps, double kill, UI-thread blocking | ✅ Worker threads, polling |
| W-8 | Forced admin elevation | ✅ Not required |
| W-9/W-10 | Deleting active profile / no active indicator | ✅ Running profiles can't be deleted; RUNNING shown per profile |
| W-11 | Navy theme | ✅ Dark-orange palette |
| W-12 | Monolith, no tests | ✅ Split into modules, unit tests added |
| W-13 | One Claude at a time | ✅ Parallel instances |

## Open

| # | Severity | Item |
|---|---|---|
| W-14 | High | **Verify on a real Windows machine**: UI rendering, tray icon, window focus, and that `claude.exe --user-data-dir=…` starts an independent instance. |
| W-15 | Medium | The Store (MSIX) build may refuse to start `claude.exe` directly from `WindowsApps` (package identity). If so, add a fallback or document using the per-user installer. |
| W-16 | Medium | Claude may minimize to the tray on window close, so `WM_CLOSE` might not exit it; the 10 s fallback then terminates the process tree. Confirm behavior and consider a gentler quit. |
| W-17 | Low | `pystray` is optional; without it, closing the window quits Claudou. |
