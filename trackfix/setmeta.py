"""
Manually set metadata tags on audio files.
Usage: trackfix --set genre="Hard Trance" --set year=2001 --input track.aiff
"""

from pathlib import Path
from .metadata import write_tags, read_existing_tags

AUDIO_EXTENSIONS = {".aiff", ".aif", ".wav", ".mp3", ".m4a", ".flac"}
VALID_FIELDS = {"title", "artist", "genre", "year"}


def parse_set_args(set_args: list[str]) -> dict:
    """Parse ['genre=Hard Trance', 'year=2001'] into {'genre': 'Hard Trance', 'year': '2001'}."""
    tags = {}
    for arg in set_args:
        if "=" not in arg:
            print(f"  [set] Ignoring invalid argument: {arg!r} (expected field=value)")
            continue
        field, _, value = arg.partition("=")
        field = field.strip().lower()
        value = value.strip()
        if field not in VALID_FIELDS:
            print(f"  [set] Unknown field {field!r} — valid fields: {', '.join(sorted(VALID_FIELDS))}")
            continue
        tags[field] = value
    return tags


def get_audio_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in AUDIO_EXTENSIONS else []
    return sorted(
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def run_set(input_path: Path, set_args: list[str], dry_run: bool, verbose: bool) -> list[dict]:
    """Write specified tags to all audio files in input_path."""
    tags = parse_set_args(set_args)
    if not tags:
        print("[set] No valid tags to write")
        return []

    files = get_audio_files(input_path)
    if not files:
        print("[set] No audio files found")
        return []

    # All fields enabled since user explicitly requested them
    fields_cfg = {f: True for f in VALID_FIELDS}

    print(f"[set] Writing {list(tags.keys())} to {len(files)} file(s)")
    return [write_tags(f, tags, fields_cfg, dry_run, verbose, force=True) for f in files]
