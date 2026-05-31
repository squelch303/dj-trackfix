"""
Sort audio files into subfolders based on metadata tags (genre, artist, year).
Uses mutagen to read tags — no external binaries needed.
"""

import shutil
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

AUDIO_EXTENSIONS = {".aiff", ".aif", ".wav", ".mp3", ".m4a", ".flac"}


def get_audio_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in AUDIO_EXTENSIONS else []
    return sorted(f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS)


def read_tag(filepath: Path, tag: str) -> str | None:
    """Read a single tag from an audio file using mutagen."""
    if MutagenFile is None:
        return None
    try:
        audio = MutagenFile(str(filepath), easy=True)
        if audio is None:
            return None
        values = audio.get(tag)
        if values:
            return str(values[0]).strip()
    except Exception:
        pass
    return None


def get_sort_key(filepath: Path, sort_by: str) -> str | None:
    """Get the value to sort by from the file's tags."""
    tag_map = {
        "genre": "genre",
        "artist": "artist",
        "year": "date",
    }
    tag = tag_map.get(sort_by, "genre")
    value = read_tag(filepath, tag)
    if value and sort_by == "year":
        # Normalise to 4-digit year
        value = value[:4]
    return value


def sort_file(
    src: Path,
    base_dir: Path,
    sort_by: str,
    fallback_folder: str,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """Move a file into its sort subfolder."""
    result = {"src": src, "out": None, "status": None, "error": None}

    key = get_sort_key(src, sort_by)
    folder_name = key if key else fallback_folder
    # Sanitise folder name
    folder_name = folder_name.replace("/", "-").replace("\\", "-").strip()

    dest_dir = base_dir / folder_name
    dest = dest_dir / src.name
    result["out"] = dest

    if verbose or dry_run:
        print(f"  [sort]    {src.name} → {folder_name}/")

    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        result["status"] = "sorted"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  [error]   {src.name}: {e}")

    return result


def run_sort(input_path: Path, config: dict, dry_run: bool, verbose: bool) -> list[dict]:
    """Sort all audio files in input_path. Returns list of result dicts."""
    if MutagenFile is None:
        print("[sort] Error: mutagen is not installed. Run: pip install mutagen")
        return []

    cfg = config["sort"]
    sort_by = cfg.get("by", "genre")
    fallback_folder = cfg.get("fallback_folder", "Other")
    base_dir = input_path if input_path.is_dir() else input_path.parent

    files = get_audio_files(input_path)
    if not files:
        print("[sort] No audio files found")
        return []

    print(f"[sort] {len(files)} file(s) — sorting by {sort_by}")
    return [sort_file(f, base_dir, sort_by, fallback_folder, dry_run, verbose) for f in files]
