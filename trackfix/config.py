"""
Config loader for dj-trackfix.
Loads config.yaml and provides defaults for all settings.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required. Run: pip install pyyaml")
    sys.exit(1)

DEFAULTS = {
    "input_dir": ".",
    "output_dir": ".",
    "keep_originals": True,
    "convert": {
        "source_formats": ["wav", "m4a"],
        "target_format": "aiff",
    },
    "fix": {
        "brackets": True,
        "leading_numbers": True,
    },
    "sort": {
        "by": "genre",
        "fallback_folder": "Other",
    },
    "metadata": {
        "musicbrainz": {
            "enabled": True,
            "user_agent": "dj-trackfix/0.2.0 ( squelch303@soundstation.net )",
        },
        "discogs": {
            "enabled": True,
            "token": "",
        },
        "fields": {
            "title": True,
            "artist": True,
            "genre": True,
            "year": True,
        },
    },
    "report": {
        "enabled": True,
        "output_file": "",
    },
}


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | None = None) -> dict:
    """Load config from file, merging with defaults."""
    config = DEFAULTS.copy()

    path = Path(config_path) if config_path else Path("config.yaml")

    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f) or {}
        config = deep_merge(DEFAULTS, user_config)
        print(f"[config] Loaded: {path}")
    else:
        if config_path:
            print(f"[config] Warning: {path} not found — using defaults")
        else:
            print("[config] No config.yaml found — using defaults")

    return config
