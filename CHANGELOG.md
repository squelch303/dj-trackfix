# Changelog

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
