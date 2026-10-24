# Claudou — agent instructions

Native multi-account launcher for Claude Desktop: `macOS/` (Swift), `window/` (Python), `linux/` (planned). **No shared code; shared behavior.**

## Mandatory workflow for any feature or behavior change

1. Read `docs/SPEC.md` and `docs/CONTRIBUTING.md`.
2. Edit `docs/SPEC.md` first (rules, UI, schema) and keep the §7 parity matrix truthful.
3. Implement the change in **every** platform (macOS, Windows, Linux when it exists). If one is skipped, mark it ⏳ in the matrix — don't leave it implicit.
4. Keep shared literals identical across platforms: UI strings (English), brand color hex, `config.json` keys, launch-command shape.
5. Update READMEs if usage changes; bump `VERSION` only when releasing.
6. Verify: `cd window && python -m unittest discover -s tests`; `cd macOS/Claudou && swift build`.

## Hard rules

- English only (code, UI, docs, commits). Orange accent; each platform follows its native look (macOS 26 system colors/vibrancy, Windows light/dark) with shared brand colors (SPEC §5).
- Never move, copy or delete Claude's own data folder; only delete Claudou-owned profile folders, with confirmation (SPEC B-7).
- Profiles run in parallel via `--user-data-dir`; never quit other profiles to open one.
- Windows UI can't be run on macOS; say so when reporting, and rely on unit tests for logic.
