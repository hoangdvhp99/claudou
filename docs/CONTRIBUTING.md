# Contributing — keep all platforms in sync

Claudou has **one implementation per OS** and **no shared code**. What is shared is the *behavior*, defined in [SPEC.md](SPEC.md). These rules keep the three apps from drifting apart.

## The rules

1. **Spec first.** A user-visible change starts as an edit to `docs/SPEC.md` (behavior rule, UI section, or schema). Code follows the spec, never the other way round.
2. **All platforms in the same change.** A feature PR must update **macOS, Windows and Linux** (once Linux exists). If a platform can't be done now, set its cell in the SPEC §7 parity matrix to ⏳ and open a tracking issue — never leave the matrix stale or silently skip a platform.
3. **Shared literals stay identical.** Change these everywhere or nowhere:
   - UI strings (English, exact wording — grep the old string in all three trees),
   - brand color hex values and profile colors (`Theme.swift` ↔ `window/claudou/theme.py` ↔ Linux CSS); surfaces follow each platform's own look (SPEC §5.1),
   - `config.json` keys and the launch-command shape.
4. **Platform idioms are fine, behavior is not negotiable.** Presentation may differ where SPEC §5/§6 says so (popover vs. tray menu). Anything else that must differ is documented under SPEC §6 in the same PR.
5. **Never touch the user's Claude data.** No moving, copying or deleting the Default profile folder; deleting only Claudou-owned folders (SPEC B-6/B-7).
6. **Single version.** Bump `VERSION` only; build scripts read it.
7. **English only** in code, UI, comments, docs and commit messages.
8. **Tested before merge.** Windows/Linux: `python -m unittest discover -s tests`. macOS: `swift build` and launch the built `.app`. Add or adapt a test whenever B-rules or the config schema change.

## Checklist for a feature change

- [ ] `docs/SPEC.md` updated (rules / UI / schema) and parity matrix reflects reality
- [ ] macOS implemented (`macOS/Claudou`)
- [ ] Windows implemented (`window/claudou`) + tests
- [ ] Linux implemented — or tracked as ⏳ with an issue
- [ ] UI strings / colors / schema identical across platforms
- [ ] READMEs touched if usage or setup changed
- [ ] `VERSION` bumped if releasing

## Where things live

| Concern | macOS | Windows |
|---|---|---|
| Model + persistence | `ProfileStore.swift` | `claudou/store.py` |
| Claude process / command | `Launcher.swift` | `claudou/launcher.py` |
| Launcher UI | `MenuView.swift` | `claudou/ui.py` (`App`) |
| Settings + CRUD | `SettingsView.swift` | `claudou/ui.py` (`SettingsWindow`) |
| Profile editor | `EditorView.swift` | `claudou/ui.py` (`EditorWindow`) |
| Palette | `Theme.swift` (brand colors only) | `claudou/theme.py` (brand colors + light/dark surfaces) |
| Launch at startup | `SettingsView.swift` (`SMAppService`) | `claudou/startup.py` |
