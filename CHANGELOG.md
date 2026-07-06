# Changelog

## [0.3.3] - 2026-07-06

### Fixed
- `metadata.musicbrainz.user_agent` shipped a hardcoded default of `dj-trackfix/0.2.0 ( squelch303@soundstation.net )` — the maintainer's own contact address, silently sent to MusicBrainz on behalf of anyone who never touched their config. Replaced with `metadata.musicbrainz.contact_email`, which has no default: MusicBrainz lookups now refuse to run until the user sets their own email. Discogs and Beatport are unaffected and keep working off their own auth even if MusicBrainz isn't configured.
- Existing `config.yaml` files with the old `user_agent` key are migrated automatically on next load: a real (non-maintainer) email is carried over to `contact_email`; the maintainer's own address is replaced with the same placeholder used in `config.example.yaml` rather than being copied forward.
- The `dj-trackfix/0.2.0` string in the Beatport and Discogs User-Agent headers was hardcoded and had drifted from the actual released version (0.3.2). Both now build their User-Agent from `trackfix.__version__` at import time, so they can't go stale again. `metadata.py`'s Discogs client also now reuses `discogs_auth.USER_AGENT` instead of a second hardcoded copy.

## [0.3.2] - 2026-07-03

### Fixed
- The built exe reported `v0.2.2` regardless of the `pyproject.toml` version — `trackfix/__init__.py` (the actual source `__version__` is read from, shown in the GUI title bar and `--version`) had never been bumped alongside it. `pyproject.toml` now derives its version dynamically from `trackfix/__init__.py` (`dynamic = ["version"]`) instead of duplicating it, so there's one place to bump per release.
- "Authenticate Beatport…" / "Authenticate Discogs…" in the GUI just reopened another dj-trackfix window instead of authenticating. It relaunched `sys.executable -m trackfix.cli --auth-...`, but in the frozen exe `sys.executable` is `dj-trackfix-gui.exe` itself, not a Python interpreter. Replaced with native Tkinter dialogs that call `beatport.py`/`discogs_auth.py`'s auth functions directly — no console relaunch needed.

## [0.3.1] - 2026-07-03

### Fixed
- Packaged `dj-trackfix-gui.exe` crashed on launch with `ImportError: attempted relative import with no known parent package`. PyInstaller was pointed directly at `trackfix/gui.py`, which uses relative imports and breaks when frozen as `__main__`. Added `run_gui.py` (repo root) as the actual PyInstaller entry point instead — see `packaging/build_windows.bat` and `.github/workflows/release.yml`.

## [0.3.0] - 2026-07-03

### Added
- `trackfix-gui` — Tkinter GUI front end (folder picker, operation checkboxes, live log). No new dependencies — stdlib only.
- `packaging/` — PyInstaller build script and Inno Setup installer script for a standalone Windows `.exe` + installer. See `packaging/BUILD.md`.
- GUI config defaults to `%APPDATA%\dj-trackfix\config.yaml` so it works from a read-only install location (e.g. Program Files) without admin rights.
- `.github/workflows/release.yml` — pushing a `v*` tag builds the exe + installer on GitHub's Windows runners and publishes both to a GitHub Release. See `RELEASING.md`.

## [0.2.2] - 2026-06-06

### Added

#### `--ext EXT[,EXT]` — extension filter for `--meta`
Limit metadata scanning to specific file extensions. Accepts a comma-separated list; leading dots optional.
```
trackfix --meta --ext aiff
trackfix --meta --ext aiff,mp3
```

#### `--recursive` / `-R` — recursive subfolder scan for `--meta`
Descend into subfolders when scanning for audio files. Without this flag behaviour is unchanged (flat scan of the input directory).
```
trackfix --meta -R --input /path/to/collection
```

#### `--overwrite FIELD[,FIELD]` — selective tag overwrite for `--meta`
By default `--meta` skips any tag that already has a value. `--overwrite` lets you name specific fields to force-overwrite while leaving everything else protected. Designed for fixing garbage titles written by Rekordbox or download tools without clobbering MIK-set keys or BPM values.
```
trackfix --meta --overwrite title,artist --ext aiff -R --input /path
```
Valid field names: `title`, `artist`, `genre`, `year`, `bpm`, `key`.

#### `--in-place` — write converted files next to source
`--convert` normally writes output to the configured `output_dir`. With `--in-place`, each converted file is written to the same folder as its source. Works correctly when scanning recursively — each file stays in its own subfolder.
```
trackfix --convert --in-place --input /path/to/tracks
```

## [0.2.1] - 2026-06-01

### Fixed
- Key tags are now always normalised to Camelot notation before writing (e.g. `D Major` → `10B`, `Am` → `8A`). Applies to `--meta`, `--set`, and all metadata sources. Beatport already returns Camelot so those pass through unchanged.

## [0.2.0] - 2026-06-01

Initial toolkit release. Replaces the old `audio_converts/` and `audio_fix_scripts/` scripts.

### Added
- `--convert` — unified audio converter (WAV/M4A → AIFF via ffmpeg), replaces separate conv_wav2aiff and conv_m4a2aiff scripts
- `--fix` — filename fixes: brackets `[ ]` → `( )`, strip leading numbers, configurable character substitution (e.g. dots in artist names)
- `--sort` — sort files into subfolders by genre, artist, or year using mutagen (no MediaInfo binary needed)
- `--meta` — metadata lookup and tag writing
  - Sources: MusicBrainz (title/artist/year), Discogs (genre), Beatport (genre/year/BPM/key)
  - Filename fallback: seeds title and artist from filename if not found externally
  - Confidence check: rejects low-confidence MusicBrainz matches
  - BPM and Key from Beatport only written if not already set (MIK takes priority)
- `--info` — display current tags on files, read-only
- `--set field=value` — manually write tags, always overwrites
- `--all` — run everything in order: fix → convert → meta → sort
- `--dry-run`, `--verbose`, `--report` flags
- `--auth-beatport` — headless Beatport OAuth (username/password, client_id auto-scraped from docs)
- `--auth-discogs` — Discogs OAuth flow for app developers
- Config-first via `config.yaml` (gitignored, `config.example.yaml` provided)
- `pyproject.toml` — installable via `pip install -e .` or `uv run trackfix`

## [0.1.0] - 2024

Initial placeholder — audio conversion scripts only.
