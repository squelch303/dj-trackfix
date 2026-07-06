"""
Metadata lookup and writing.
Looks up Title, Artist, Genre, Year from MusicBrainz and/or Discogs.
Writes tags to AIFF (and other formats) using mutagen.
"""

from pathlib import Path

try:
    import musicbrainzngs as mb
except ImportError:
    mb = None

try:
    import discogs_client
    import discogs_client.exceptions as discogs_exc
except ImportError:
    discogs_client = None
    discogs_exc = None

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

from . import __version__
from .beatport import search_beatport, get_valid_token
from .config import UNCONFIGURED_EMAIL
from .discogs_auth import USER_AGENT as DISCOGS_USER_AGENT

# ---------------------------------------------------------------------------
# Key normalisation — always write Camelot notation
# ---------------------------------------------------------------------------

KEY_MAP = {
    "abm": "1A", "g#m": "1A", "ab minor": "1A", "g# minor": "1A",
    "ebm": "2A", "d#m": "2A", "eb minor": "2A", "d# minor": "2A",
    "bbm": "3A", "a#m": "3A", "bb minor": "3A", "a# minor": "3A",
    "fm":  "4A",              "f minor":  "4A",
    "cm":  "5A",              "c minor":  "5A",
    "gm":  "6A",              "g minor":  "6A",
    "dm":  "7A",              "d minor":  "7A",
    "am":  "8A",              "a minor":  "8A",
    "em":  "9A",              "e minor":  "9A",
    "bm":  "10A",             "b minor":  "10A",
    "f#m": "11A", "gbm": "11A", "f# minor": "11A", "gb minor": "11A",
    "c#m": "12A", "dbm": "12A", "c# minor": "12A", "db minor": "12A",
    "b":   "1B",              "b major":  "1B",
    "f#":  "2B",  "gb":  "2B", "f# major": "2B", "gb major": "2B",
    "db":  "3B",  "c#":  "3B", "db major": "3B", "c# major": "3B",
    "ab":  "4B",  "g#":  "4B", "ab major": "4B", "g# major": "4B",
    "eb":  "5B",  "d#":  "5B", "eb major": "5B", "d# major": "5B",
    "bb":  "6B",  "a#":  "6B", "bb major": "6B", "a# major": "6B",
    "f":   "7B",              "f major":  "7B",
    "c":   "8B",              "c major":  "8B",
    "g":   "9B",              "g major":  "9B",
    "d":   "10B",             "d major":  "10B",
    "a":   "11B",             "a major":  "11B",
    "e":   "12B",             "e major":  "12B",
}

CAMELOT_VALUES = {f"{n}{s}" for n in range(1, 13) for s in ("A", "B")}


def to_camelot(key: str) -> str:
    """Normalise any key string to Camelot notation. Returns original if already Camelot or unknown."""
    if not key:
        return key
    stripped = key.strip()
    if stripped in CAMELOT_VALUES:
        return stripped
    normalised = stripped.lower().replace("♭", "b").replace("♯", "#")
    return KEY_MAP.get(normalised, stripped)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def setup_musicbrainz(contact_email: str):
    if mb is None:
        return False
    mb.set_useragent("dj-trackfix", __version__, contact_email)
    return True


def check_musicbrainz_config(cfg: dict) -> None:
    """Check MusicBrainz-specific settings only.
    Raises ValueError with a user-facing message if contact_email is missing.
    Does NOT validate Discogs/Beatport — those have their own auth and must
    keep working independently of MusicBrainz's configuration state."""
    mb_cfg = cfg.get("musicbrainz", {})
    if mb_cfg.get("enabled"):
        email = (mb_cfg.get("contact_email") or "").strip()
        if not email or email.lower() == UNCONFIGURED_EMAIL:
            raise ValueError(
                "MusicBrainz is enabled but metadata.musicbrainz.contact_email is not set.\n"
                "  MusicBrainz requires every client to identify itself with a real contact\n"
                "  email in its User-Agent header and blocks requests that don't.\n"
                "  Fix: edit config.yaml and set metadata.musicbrainz.contact_email to your\n"
                "  own email, or set metadata.musicbrainz.enabled: false to skip MusicBrainz."
            )


def similarity(a: str, b: str) -> float:
    """Simple case-insensitive similarity ratio between two strings."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_confident_match(searched_artist: str, searched_title: str, found: dict, threshold: float = 0.6) -> bool:
    """Return True only if the found result is close enough to what we searched for."""
    artist_ok = similarity(searched_artist, found.get("artist", "")) >= threshold
    title_ok  = similarity(searched_title,  found.get("title",  "")) >= threshold
    return artist_ok and title_ok


def lookup_musicbrainz(artist: str, title: str, confidence: float = 0.6) -> dict:
    """Search MusicBrainz for a recording. Returns dict of found fields."""
    if mb is None:
        return {}
    try:
        result = mb.search_recordings(recording=title, artist=artist, limit=1)
        recordings = result.get("recording-list", [])
        if not recordings:
            return {}
        rec = recordings[0]
        meta = {
            "title": rec.get("title"),
            "artist": rec.get("artist-credit-phrase"),
        }
        releases = rec.get("release-list", [])
        if releases:
            rel = releases[0]
            meta["year"] = rel.get("date", "")[:4] or None
        meta = {k: v for k, v in meta.items() if v}

        if not is_confident_match(artist, title, meta, threshold=confidence):
            print(f"  [meta]    MusicBrainz: low confidence match — skipping ({meta.get('artist')} / {meta.get('title')})")
            return {}

        return meta
    except Exception as e:
        print(f"  [meta]    MusicBrainz error: {e}")
        return {}


def lookup_discogs(artist: str, title: str, token: str = "", access_token: str = "", access_secret: str = "",
                   max_retries: int = 3, retry_delay: float = 60.0) -> dict:
    """Search Discogs for a release. Returns dict of found fields.
    Retries on HTTP 429 (rate limit), honouring Retry-After if present."""
    import time

    if discogs_client is None:
        return {}
    try:
        if access_token and access_secret:
            d = discogs_client.Client(DISCOGS_USER_AGENT)
            d.set_token(access_token, access_secret)
        elif token:
            d = discogs_client.Client(DISCOGS_USER_AGENT, user_token=token)
        else:
            return {}

        for attempt in range(1, max_retries + 1):
            try:
                results = d.search(f"{artist} {title}", type="release")
                if not results:
                    return {}
                release = results[0]
                meta = {}
                genres = getattr(release, "genres", None)
                styles = getattr(release, "styles", None)
                # Prefer styles (more specific) over genres
                if styles:
                    meta["genre"] = styles[0]
                elif genres:
                    meta["genre"] = genres[0]
                year = getattr(release, "year", None)
                if year:
                    meta["year"] = str(year)
                return meta

            except Exception as e:
                # Check for rate-limit error (HTTP 429)
                status = getattr(e, "status_code", None) or getattr(e, "code", None)
                if status == 429:
                    wait = retry_delay
                    # Honour Retry-After header if the exception carries it
                    headers = getattr(e, "headers", {}) or {}
                    if "Retry-After" in headers:
                        try:
                            wait = float(headers["Retry-After"])
                        except (ValueError, TypeError):
                            pass
                    if attempt < max_retries:
                        print(f"  [meta]    Discogs rate-limited — waiting {wait:.0f}s (attempt {attempt}/{max_retries})")
                        time.sleep(wait)
                        continue
                    else:
                        print(f"  [meta]    Discogs rate-limited — giving up after {max_retries} attempts")
                        return {}
                raise  # re-raise non-429 errors

    except Exception as e:
        print(f"  [meta]    Discogs error: {e}")
        return {}


def lookup_metadata(artist: str, title: str, config: dict) -> dict:
    """
    Look up metadata from enabled sources.
    Priority: MusicBrainz (title/artist/year) → Discogs (genre) → Beatport (genre, most accurate for electronic)
    """
    cfg = config["metadata"]
    meta = {}

    if cfg["musicbrainz"]["enabled"]:
        setup_musicbrainz(cfg["musicbrainz"].get("contact_email", ""))
        confidence = cfg["musicbrainz"].get("confidence", 0.6)
        mb_meta = lookup_musicbrainz(artist, title, confidence=confidence)
        meta.update(mb_meta)

    if cfg["discogs"]["enabled"]:
        discogs_meta = lookup_discogs(
            artist, title,
            token=cfg["discogs"].get("token", ""),
            access_token=cfg["discogs"].get("access_token", ""),
            access_secret=cfg["discogs"].get("access_secret", ""),
            max_retries=cfg["discogs"].get("max_retries", 3),
            retry_delay=cfg["discogs"].get("retry_delay", 60.0),
        )
        if discogs_meta:
            print(f"  [meta]    Discogs found: {discogs_meta}")
            for k, v in discogs_meta.items():
                if k not in meta:
                    meta[k] = v
        else:
            print(f"  [meta]    Discogs: no results")

    # Beatport last — best genre taxonomy for electronic music
    bp_cfg = cfg.get("beatport", {})
    if bp_cfg.get("enabled") and "genre" not in meta:
        token = get_valid_token(bp_cfg)
        if token:
            bp_meta = search_beatport(artist, title, token)
            if bp_meta:
                print(f"  [meta]    Beatport found: {bp_meta}")
                for k, v in bp_meta.items():
                    if k not in meta:
                        meta[k] = v
            else:
                print(f"  [meta]    Beatport: no results")

    return meta


# ---------------------------------------------------------------------------
# Tag writing
# ---------------------------------------------------------------------------

def read_existing_tags(filepath: Path) -> dict:
    """Read current tag values from a file. Returns dict of field: value."""
    try:
        from mutagen.aiff import AIFF
        from mutagen.mp3 import MP3
        ext = filepath.suffix.lower()
        frame_map = {"TIT2": "title", "TPE1": "artist", "TCON": "genre",
                     "TDRC": "year", "TBPM": "bpm", "TKEY": "key"}
        if ext in (".aiff", ".aif"):
            audio = AIFF(str(filepath))
        elif ext == ".mp3":
            audio = MP3(str(filepath))
        else:
            audio = MutagenFile(str(filepath), easy=True)
            if audio:
                return {v: str(audio[k][0]) for k, v in
                        {"title": "title", "artist": "artist", "genre": "genre",
                         "date": "year", "bpm": "bpm"}.items() if k in audio}
            return {}
        if not audio.tags:
            return {}
        result = {}
        for frame_id, field in frame_map.items():
            frame = audio.tags.get(frame_id)
            if frame and str(frame).strip():
                result[field] = str(frame).strip()
        return result
    except Exception:
        return {}


def write_tags(filepath: Path, tags: dict, fields_cfg: dict, dry_run: bool, verbose: bool, force_fields: set[str] | None = None) -> dict:
    """Write metadata tags to an audio file using mutagen ID3 frames directly.
    Skips fields that already have a value unless the field is listed in force_fields."""
    result = {"src": filepath, "tags_written": {}, "status": None, "error": None}

    if MutagenFile is None:
        result["status"] = "error"
        result["error"] = "mutagen not installed"
        return result

    # Read existing tags — don't overwrite populated fields unless explicitly forced
    existing = read_existing_tags(filepath)
    force_fields = force_fields or set()
    to_write = {
        k: v for k, v in tags.items()
        if fields_cfg.get(k, True) and v and (k in force_fields or not existing.get(k))
    }
    # Always normalise key to Camelot notation
    if "key" in to_write:
        to_write["key"] = to_camelot(to_write["key"])

    if not to_write:
        result["status"] = "no_data"
        if verbose:
            print(f"  [meta]    {filepath.name} — no metadata found")
        return result

    if verbose or dry_run:
        for k, v in to_write.items():
            print(f"  [meta]    {filepath.name} — {k}: {v}")

    if dry_run:
        result["status"] = "dry_run"
        result["tags_written"] = to_write
        return result

    try:
        from mutagen.id3 import ID3, TIT2, TPE1, TCON, TDRC, ID3NoHeaderError
        from mutagen.aiff import AIFF
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC

        ext = filepath.suffix.lower()

        if ext in (".aiff", ".aif"):
            audio = AIFF(str(filepath))
            if audio.tags is None:
                audio.add_tags()
            from mutagen.id3 import TBPM, TKEY
            frame_map = {
                "title":  lambda v: TIT2(encoding=3, text=v),
                "artist": lambda v: TPE1(encoding=3, text=v),
                "genre":  lambda v: TCON(encoding=3, text=v),
                "year":   lambda v: TDRC(encoding=3, text=v),
                "bpm":    lambda v: TBPM(encoding=3, text=v),
                "key":    lambda v: TKEY(encoding=3, text=v),
            }
            for field, value in to_write.items():
                if field in frame_map:
                    audio.tags.add(frame_map[field](value))
            audio.save()

        elif ext == ".mp3":
            audio = MP3(str(filepath))
            if audio.tags is None:
                audio.add_tags()
            from mutagen.id3 import TBPM, TKEY
            frame_map = {
                "title":  lambda v: TIT2(encoding=3, text=v),
                "artist": lambda v: TPE1(encoding=3, text=v),
                "genre":  lambda v: TCON(encoding=3, text=v),
                "year":   lambda v: TDRC(encoding=3, text=v),
                "bpm":    lambda v: TBPM(encoding=3, text=v),
                "key":    lambda v: TKEY(encoding=3, text=v),
            }
            for field, value in to_write.items():
                if field in frame_map:
                    audio.tags.add(frame_map[field](value))
            audio.save()

        else:
            # WAV, FLAC, M4A — use easy interface
            audio = MutagenFile(str(filepath), easy=True)
            if audio is None:
                result["status"] = "error"
                result["error"] = "Could not open file with mutagen"
                return result
            easy_map = {"title": "title", "artist": "artist", "genre": "genre", "year": "date"}
            for field, value in to_write.items():
                if field in easy_map:
                    audio[easy_map[field]] = value
            audio.save()

        result["status"] = "updated"
        result["tags_written"] = to_write

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"  [error]   {filepath.name}: {e}")

    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

AUDIO_EXTENSIONS = {".aiff", ".aif", ".wav", ".mp3", ".m4a", ".flac"}


def get_audio_files(input_path: Path, ext_filter: set[str] | None = None, recursive: bool = False) -> list[Path]:
    allowed = ext_filter if ext_filter else AUDIO_EXTENSIONS
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() in allowed else []
    glob = input_path.rglob("*") if recursive else input_path.iterdir()
    return sorted(f for f in glob if f.is_file() and f.suffix.lower() in allowed)


def parse_artist_title(filepath: Path) -> tuple[str, str]:
    """
    Try to parse artist and title from filename.
    Handles formats:
      - 'Artist - Title'
      - 'Artist-Title' (no spaces around dash)
      - 'BPM - Key - Artist - Title'
      - 'BPM-Key-Artist-Title'
    Underscores are treated as spaces.
    """
    import re

    name = filepath.stem.replace("_", " ")

    # Try splitting on ' - ' first (most common DJ format)
    if " - " in name:
        parts = [p.strip() for p in name.split(" - ")]
    else:
        # Fall back to splitting on bare '-'
        parts = [p.strip() for p in name.split("-")]

    # Strip leading BPM (e.g. 140) and Camelot key (e.g. 8A, 12B)
    filtered = [p for p in parts if not re.match(r"^\d{2,3}$|^\d+[AaBb]$", p)]

    # Clean up parenthetical suffixes from title (Extended Mix) etc — keep them
    if len(filtered) >= 2:
        artist = filtered[0].strip()
        title = filtered[1].strip()
        return artist, title

    return name.strip(), ""


def run_meta(input_path: Path, config: dict, dry_run: bool, verbose: bool, ext_filter: set[str] | None = None, recursive: bool = False, overwrite_fields: set[str] | None = None) -> list[dict]:
    """Look up and write metadata for all audio files. Returns list of result dicts."""
    if MutagenFile is None:
        print("[meta] Error: mutagen is not installed. Run: pip install mutagen")
        return []

    try:
        check_musicbrainz_config(config["metadata"])
    except ValueError as e:
        print(f"[meta] Error: {e}")
        print("[meta] Disabling MusicBrainz for this run — Discogs/Beatport will still run if configured.")
        config["metadata"]["musicbrainz"]["enabled"] = False

    fields_cfg = config["metadata"]["fields"]
    files = get_audio_files(input_path, ext_filter, recursive)

    if not files:
        print("[meta] No audio files found")
        return []

    use_filename = config.get("metadata", {}).get("use_filename", True)

    print(f"[meta] {len(files)} file(s) to process")
    results = []
    for f in files:
        artist, title = parse_artist_title(f)
        print(f"  [meta]    Searching: artist={artist!r}  title={title!r}")

        tags = lookup_metadata(artist, title, config)

        # If filename parsing gave us artist/title and they're not already found
        # from an external source, seed them from the filename
        if use_filename:
            if artist and "title" not in tags:
                tags["title"] = title
            if title and "artist" not in tags:
                tags["artist"] = artist

        result = write_tags(f, tags, fields_cfg, dry_run, verbose, force_fields=overwrite_fields)
        results.append(result)

    return results
