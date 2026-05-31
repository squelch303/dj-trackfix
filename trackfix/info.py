"""
Display current metadata tags on audio files.
Read-only — never modifies files.
"""

from pathlib import Path

try:
    from mutagen.aiff import AIFF
    from mutagen.mp3 import MP3
    from mutagen import File as MutagenFile
except ImportError:
    AIFF = MP3 = MutagenFile = None

AUDIO_EXTENSIONS = {".aiff", ".aif", ".wav", ".mp3", ".m4a", ".flac"}

FIELDS_OF_INTEREST = {
    "TIT2": "Title",
    "TPE1": "Artist",
    "TCON": "Genre",
    "TDRC": "Year",
    "TBPM": "BPM",
    "TKEY": "Key",
}


def read_tags(filepath: Path) -> dict:
    """Read tags from an audio file. Returns dict of field: value."""
    ext = filepath.suffix.lower()
    tags = {}

    try:
        if ext in (".aiff", ".aif"):
            audio = AIFF(str(filepath))
            if audio.tags:
                for frame_id, label in FIELDS_OF_INTEREST.items():
                    frame = audio.tags.get(frame_id)
                    if frame:
                        tags[label] = str(frame)
        elif ext == ".mp3":
            audio = MP3(str(filepath))
            if audio.tags:
                for frame_id, label in FIELDS_OF_INTEREST.items():
                    frame = audio.tags.get(frame_id)
                    if frame:
                        tags[label] = str(frame)
        else:
            audio = MutagenFile(str(filepath), easy=True)
            if audio:
                easy_map = {
                    "title": "Title", "artist": "Artist",
                    "genre": "Genre", "date": "Year", "bpm": "BPM",
                }
                for easy_key, label in easy_map.items():
                    val = audio.get(easy_key)
                    if val:
                        tags[label] = str(val[0])
    except Exception as e:
        tags["_error"] = str(e)

    return tags


def get_audio_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in AUDIO_EXTENSIONS else []
    return sorted(
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def run_info(input_path: Path):
    """Print tag info for all audio files in input_path."""
    if MutagenFile is None:
        print("[info] Error: mutagen not installed")
        return

    files = get_audio_files(input_path)
    if not files:
        print("[info] No audio files found")
        return

    for f in files:
        print(f"\n  {f.name}")
        tags = read_tags(f)
        if not tags:
            print("    (no tags found)")
        elif "_error" in tags:
            print(f"    error: {tags['_error']}")
        else:
            for label, value in tags.items():
                print(f"    {label:<8} {value}")
