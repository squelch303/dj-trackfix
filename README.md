# dj-trackfix

DJ audio file toolkit — convert, fix, sort, and tag your tracks.

Built for the workflow of receiving files directly from producers and getting them into shape for rekordbox.

## What it does

| Flag | Operation |
|------|-----------|
| `--convert` | Convert WAV/M4A → AIFF (or configured target format) |
| `--fix` | Fix filenames — replace `[ ]` with `( )`, strip leading numbers, custom char substitution |
| `--meta` | Look up and write metadata via MusicBrainz, Discogs, and Beatport |
| `--sort` | Sort files into subfolders by genre, artist, or year |
| `--set field=value` | Manually set a tag on all matching files |
| `--info` | Display current tags on files (read-only) |
| `--all` | Run everything in order: fix → convert → meta → sort |

Add `--dry-run` to preview all changes without touching files.
Add `--verbose` to see every action.
Add `--report` for a summary at the end.

## Metadata sources

`--meta` looks up Title, Artist, Genre, Year, BPM, and Key from three sources in priority order:

1. **MusicBrainz** — title, artist, year (free, no account needed)
2. **Discogs** — genre/style (free personal token)
3. **Beatport** — genre, year, BPM, key (best taxonomy for electronic music)

Rules:
- Title and artist are seeded from the filename if not found externally
- BPM and Key from Beatport are only written if not already set (MIK takes priority)
- Low-confidence MusicBrainz matches are skipped rather than written

## Install

Requires Python 3.10+ and [ffmpeg](https://ffmpeg.org/) in your PATH.

### With uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg (uv handles Python deps, but ffmpeg is a system binary)
# macOS:   brew install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# Windows: winget install ffmpeg

# Clone and run — uv handles the venv and Python dependencies automatically
git clone https://github.com/squelch303/dj-trackfix
cd dj-trackfix
uv run trackfix --help
```

After the first `uv run`, subsequent runs are instant — no activation needed:

```bash
uv run trackfix --all --input /path/to/tracks --dry-run
```

### With pip

```bash
pip install -e .
trackfix --help
```

## Usage

```bash
# See what would happen without changing anything
trackfix --all --input /path/to/tracks --dry-run

# Fix filenames and convert to AIFF
trackfix --fix --convert --input /path/to/tracks

# Full run with report
trackfix --all --input /path/to/tracks --report

# Look up and write metadata for all files in a folder
trackfix --meta --input /path/to/tracks --verbose

# Show current tags on files
trackfix --info --input /path/to/tracks

# Manually set tags (always overwrites)
trackfix --set "genre=Hard Trance" --set "year=2001" --input /path/to/tracks

# Single file
trackfix --meta --input "Artist - Track.aiff" --verbose
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and edit:

```bash
cp config.example.yaml config.yaml
```

`config.yaml` is gitignored — never committed.

Key settings:
- `convert.source_formats` — which formats to convert from
- `convert.target_format` — target format (default: `aiff`)
- `fix.char_replace` — custom character substitutions (e.g. `.` → `_` for dotted artist names)
- `sort.by` — sort by `genre`, `artist`, or `year`
- `metadata.use_filename` — seed title/artist from filename if not found externally (default: true)

### Discogs (recommended — personal token)

Takes 10 seconds:

1. Go to https://www.discogs.com/settings/developers
2. Click **Generate new token**
3. Add to `config.yaml`:

```yaml
metadata:
  discogs:
    enabled: true
    token: "your_token_here"
```

### Discogs (OAuth — for app developers)

If you've registered your own Discogs app:

```bash
trackfix --auth-discogs
```

Prompts for Consumer Key/Secret, handles the OAuth flow, and saves tokens to `config.yaml`.

### Beatport

Beatport has the most accurate genre taxonomy for electronic music. Authenticate once:

```bash
trackfix --auth-beatport
```

Prompts for your Beatport username and password. Tokens are saved to `config.yaml`. Then set `metadata.beatport.enabled: true` in your config.

Note: Beatport's search API has inconsistent coverage for smaller/older releases. Use `--set` to fill in genre manually for tracks it can't find.

## Filename format

`--meta` parses artist and title from the filename. Supported formats:

```
Artist - Title.aiff
Artist - Title (Extended Mix).aiff
BPM - Key - Artist - Title.aiff
Artist-Title.aiff
```

Underscores are treated as spaces. Leading BPM and Camelot key parts are stripped automatically.

## Requirements

- Python 3.10+
- ffmpeg binary in PATH
- `ffmpeg-python`, `mutagen`, `musicbrainzngs`, `discogs-client`, `pyyaml`, `requests`

## Part of squelch303

https://soundstation.net · https://github.com/squelch303
