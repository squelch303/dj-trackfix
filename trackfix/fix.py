"""
Filename fix operations.
- brackets: replace [ ] with ( ) in filenames
- leading_numbers: strip leading numbers from filenames
"""

import re
from pathlib import Path

AUDIO_EXTENSIONS = {".aiff", ".aif", ".wav", ".mp3", ".m4a", ".flac"}


def get_audio_files(input_path: Path) -> list[Path]:
    """Return all audio files in input_path."""
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in AUDIO_EXTENSIONS else []
    return sorted(f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS)


def fix_brackets(name: str) -> str:
    """Replace [ ] with ( ) in filename stem."""
    return name.replace("[", "(").replace("]", ")")


def fix_leading_numbers(name: str) -> str:
    """Strip leading numbers (and separators) from filename stem."""
    cleaned = re.sub(r"^\d+[\s_\-\.]+", "", name)
    return cleaned if cleaned else name


def fix_char_replace(name: str, replacements: dict) -> str:
    """Apply configurable character substitutions to filename stem."""
    for find, replace in replacements.items():
        name = name.replace(find, replace)
    return name


def apply_fixes(src: Path, cfg: dict, dry_run: bool, verbose: bool) -> dict:
    """Apply configured fixes to a single file. Returns result dict."""
    stem = src.stem
    original_stem = stem

    if cfg.get("brackets"):
        stem = fix_brackets(stem)

    if cfg.get("leading_numbers"):
        stem = fix_leading_numbers(stem)

    char_replacements = cfg.get("char_replace", {})
    if char_replacements:
        stem = fix_char_replace(stem, char_replacements)

    result = {"src": src, "out": None, "status": None, "error": None}

    if stem == original_stem:
        result["status"] = "unchanged"
        if verbose:
            print(f"  [fix]     {src.name} — no changes needed")
        return result

    new_path = src.with_name(stem + src.suffix)
    result["out"] = new_path

    if verbose or dry_run:
        print(f"  [fix]     {src.name} → {new_path.name}")

    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        src.rename(new_path)
        result["status"] = "fixed"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  [error]   {src.name}: {e}")

    return result


def run_fix(input_path: Path, config: dict, dry_run: bool, verbose: bool) -> list[dict]:
    """Run filename fixes on all audio files. Returns list of result dicts."""
    cfg = config["fix"]
    files = get_audio_files(input_path)

    if not files:
        print("[fix] No audio files found")
        return []

    print(f"[fix] {len(files)} file(s) to check")
    return [apply_fixes(f, cfg, dry_run, verbose) for f in files]
