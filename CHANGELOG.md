# Changelog

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
