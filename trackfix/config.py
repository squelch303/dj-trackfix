"""
Config loader for dj-trackfix.
Loads config.yaml and provides defaults for all settings.
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required. Run: pip install pyyaml")
    sys.exit(1)

# The maintainer's own contact address — never migrate this into a user's
# contact_email, since that would just re-expose it under the new key.
_MAINTAINER_EMAIL = "squelch303@soundstation.net"
_USER_AGENT_EMAIL_RE = re.compile(r"\(\s*([^\s()]+@[^\s()]+)\s*\)")

# Placeholder used in config.example.yaml — treated as "not configured" both
# here (migration) and in metadata.check_musicbrainz_config (the run-time gate).
UNCONFIGURED_EMAIL = "your-email@example.com"

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
            # No default — MusicBrainz requires each user to supply their own
            # contact email. Must be set in config.yaml before --meta will run.
            "contact_email": "",
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


def migrate_legacy_musicbrainz_config(config: dict) -> bool:
    """Detect the old `metadata.musicbrainz.user_agent` key (pre-contact_email format)
    and migrate it. Mutates `config` in place. Returns True if anything changed.

    - If the old user_agent string carried the maintainer's own email, it's replaced
      with the standard "not configured" placeholder (never copied into contact_email
      as-is — that would just re-expose it under the new key instead of removing it).
    - If it carried some other (real user) email, that email is migrated into
      contact_email, but only if contact_email isn't already set.
    """
    mb_cfg = config.get("metadata", {}).get("musicbrainz")
    if not isinstance(mb_cfg, dict) or "user_agent" not in mb_cfg:
        return False

    legacy_ua = mb_cfg.pop("user_agent") or ""
    match = _USER_AGENT_EMAIL_RE.search(legacy_ua)
    email = match.group(1) if match else ""

    if email and email.lower() != _MAINTAINER_EMAIL:
        if not mb_cfg.get("contact_email"):
            mb_cfg["contact_email"] = email
            print(f"[config] Migrated legacy musicbrainz.user_agent -> contact_email: {email}")
    else:
        if not mb_cfg.get("contact_email"):
            mb_cfg["contact_email"] = UNCONFIGURED_EMAIL
        print("[config] Removed legacy musicbrainz.user_agent (referenced the maintainer's "
              "contact, not yours) — set metadata.musicbrainz.contact_email to your own email.")

    return True


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

        if migrate_legacy_musicbrainz_config(config):
            try:
                with open(path, "w") as f:
                    yaml.safe_dump(config, f, default_flow_style=False, sort_keys=True)
                print(f"[config] Saved migrated settings back to {path}")
            except OSError as e:
                print(f"[config] Warning: could not save migrated config to {path}: {e}")
    else:
        if config_path:
            print(f"[config] Warning: {path} not found — using defaults")
        else:
            print("[config] No config.yaml found — using defaults")

    return config
