# Windows — status and open items

The Windows app was rewritten to follow the macOS design (parallel instances via `--user-data-dir`, Settings with profile CRUD, native-style UI). Items from the review of the original junction-based version:

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
| W-11 | Navy theme | ✅ Replaced by a light/dark Windows 11 style with the orange accent |
| W-12 | Monolith, no tests | ✅ Split into modules, unit tests added |
| W-13 | One Claude at a time | ✅ Parallel instances |
| W-19 | Old `config.json` (`{"profiles": {...}}`) crashed startup | ✅ Migrated to the SPEC §4 array on first run; original kept as `config.legacy.json` |

## Open

| # | Severity | Item |
|---|---|---|
| W-14 | High | **Verify on a real Windows machine**: UI rendering, tray icon, window focus, and that `claude.exe --user-data-dir=…` starts an independent instance. |
| W-15 | Low | Verified 2026-10-26 on the Store (MSIX) build: `Claude.exe --user-data-dir=…` from `WindowsApps` starts an independent instance and is detected as running. |
| W-16 | Low | ✅ Fixed 2026-10-26: Quit sends `WM_QUERYENDSESSION` + `WM_ENDSESSION` to Claude's app windows (hidden ones too), which Claude handles as a Windows `session-end` and quits in ~0.3 s. `WM_CLOSE` only hid it to the tray. The 10 s terminate fallback remains. |
| W-17 | Low | `pystray` is optional; without it, closing the window quits Claudou. |
| W-18 | Medium | The redesigned UI (rounded cards, pills, light/dark colors, hover highlight) and the **Launch at startup** registry write were only linted and signature-checked; they have never been rendered or run. Verify on Windows, including that a frozen exe registers and unregisters correctly. |
