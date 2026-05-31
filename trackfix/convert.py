"""
Audio file conversion.
Converts wav/m4a (and other configured formats) to aiff using ffmpeg.
"""

from pathlib import Path

try:
    import ffmpeg
except ImportError:
    ffmpeg = None


def get_source_files(input_path: Path, source_formats: list[str]) -> list[Path]:
    """Return all files matching source formats in input_path."""
    files = []
    if input_path.is_file():
        if input_path.suffix.lstrip(".").lower() in source_formats:
            files.append(input_path)
    else:
        for fmt in source_formats:
            files.extend(input_path.glob(f"*.{fmt}"))
            files.extend(input_path.glob(f"*.{fmt.upper()}"))
    return sorted(set(files))


def convert_file(
    src: Path,
    output_dir: Path,
    target_format: str,
    keep_originals: bool,
    dry_run: bool,
    verbose: bool,
) -> dict:
    """
    Convert a single file to target format.
    Returns a result dict with status and details.
    """
    out_file = output_dir / (src.stem + f".{target_format}")
    result = {"src": src, "out": out_file, "status": None, "error": None}

    if out_file.exists():
        result["status"] = "skipped"
        if verbose:
            print(f"  [skip]    {src.name} → already exists")
        return result

    if verbose or dry_run:
        print(f"  [convert] {src.name} → {out_file.name}")

    if dry_run:
        result["status"] = "dry_run"
        return result

    if ffmpeg is None:
        result["status"] = "error"
        result["error"] = "ffmpeg-python not installed"
        return result

    try:
        ffmpeg.input(str(src)).output(
            str(out_file), map_metadata=0, write_id3v2=1
        ).global_args("-loglevel", "error").run(overwrite_output=True)

        if keep_originals:
            converted_name = src.with_suffix(src.suffix + "_converted")
            src.rename(converted_name)
            if verbose:
                print(f"  [rename]  {src.name} → {converted_name.name}")
        else:
            src.unlink()
            if verbose:
                print(f"  [delete]  {src.name}")

        result["status"] = "converted"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  [error]   {src.name}: {e}")

    return result


def run_convert(input_path: Path, config: dict, dry_run: bool, verbose: bool) -> list[dict]:
    """Run conversion on all matching files. Returns list of result dicts."""
    cfg = config["convert"]
    source_formats = cfg["source_formats"]
    target_format = cfg["target_format"]
    output_dir = Path(config["output_dir"])
    keep_originals = config["keep_originals"]

    output_dir.mkdir(parents=True, exist_ok=True)

    files = get_source_files(input_path, source_formats)
    if not files:
        print(f"[convert] No files found matching: {source_formats}")
        return []

    print(f"[convert] {len(files)} file(s) to convert → {target_format.upper()}")
    results = []
    for f in files:
        results.append(convert_file(f, output_dir, target_format, keep_originals, dry_run, verbose))

    return results
