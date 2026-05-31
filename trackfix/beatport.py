"""
Beatport API v4 integration.

Auth flow (standard OAuth2 authorization_code, documented by Beatport):
1. Scrape client_id from Beatport's public docs page JS
2. POST /auth/login/ with username/password -> session cookies
3. GET /auth/o/authorize/ -> auth code in Location header
4. POST /auth/o/token/ with code -> access + refresh tokens

The client_id scraping approach is derived from reading Beatport's own
public JavaScript — the key name 'API_CLIENT_ID' is their own variable.
"""

import getpass
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

try:
    import requests
except ImportError:
    requests = None

API_BASE          = "https://api.beatport.com/v4"
REDIRECT_URI      = f"{API_BASE}/auth/o/post-message/"
USER_AGENT        = "dj-trackfix/0.2.0"
SCRIPT_SRC_RE     = re.compile(r"src=.(.*js)")
CLIENT_ID_RE      = re.compile(r"API_CLIENT_ID: \'(.*)\'")


# ---------------------------------------------------------------------------
# Client ID scraping
# ---------------------------------------------------------------------------

def fetch_client_id() -> str | None:
    """Scrape the Beatport API client_id from their docs JS files."""
    if requests is None:
        return None
    try:
        html = requests.get(f"{API_BASE}/docs/", timeout=15).text
        for script_src in SCRIPT_SRC_RE.findall(html):
            url = f"https://api.beatport.com{script_src}"
            try:
                js = requests.get(url, timeout=15).text
                matches = CLIENT_ID_RE.findall(js)
                if matches:
                    return matches[0]
            except Exception:
                continue
    except Exception as e:
        print(f"[beatport] Could not fetch client_id: {e}")
    return None


# ---------------------------------------------------------------------------
# Auth flow
# ---------------------------------------------------------------------------

def authorize(username: str, password: str, client_id: str) -> dict | None:
    """
    Full headless OAuth flow using username/password.
    Returns token dict with access_token, refresh_token etc.
    """
    if requests is None:
        print("[beatport] requests library not installed")
        return None

    try:
        with requests.Session() as s:
            s.headers["User-Agent"] = USER_AGENT

            # Step 1 — login to get session cookies
            resp = s.post(f"{API_BASE}/auth/login/", json={
                "username": username,
                "password": password,
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "username" not in data:
                print(f"[beatport] Login failed: {data}")
                return None

            # Step 2 — get authorization code
            resp = s.get(
                f"{API_BASE}/auth/o/authorize/",
                params={
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": REDIRECT_URI,
                },
                allow_redirects=False,
                timeout=15,
            )
            if "Location" not in resp.headers:
                print(f"[beatport] No redirect location — status {resp.status_code}")
                return None

            parsed = urlparse(resp.headers["Location"])
            codes = parse_qs(parsed.query).get("code")
            if not codes:
                print(f"[beatport] No auth code in redirect: {resp.headers['Location']}")
                return None
            auth_code = codes[0]

            # Step 3 — exchange code for token
            resp = s.post(
                f"{API_BASE}/auth/o/token/",
                params={
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": REDIRECT_URI,
                    "client_id": client_id,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()

    except requests.exceptions.HTTPError as e:
        print(f"[beatport] HTTP error: {e.response.status_code} {e}")
        try:
            print(f"[beatport] Response: {e.response.json()}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"[beatport] Auth error: {e}")
        return None


def refresh_access_token(refresh_tok: str, client_id: str) -> dict | None:
    """Refresh an expired access token."""
    if requests is None:
        return None
    try:
        resp = requests.post(f"{API_BASE}/auth/o/token/", params={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": client_id,
        }, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[beatport] Token refresh error: {e}")
        return None


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def save_tokens(config_path: Path, token_data: dict, client_id: str = ""):
    """Write tokens into config.yaml."""
    try:
        import yaml
    except ImportError:
        print("[beatport] pyyaml required to save tokens")
        return

    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    bp = config.setdefault("metadata", {}).setdefault("beatport", {})
    bp["access_token"]  = token_data.get("access_token", "")
    bp["refresh_token"] = token_data.get("refresh_token", "")
    bp["enabled"]       = True
    if client_id:
        bp["client_id"] = client_id

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"[beatport] Tokens saved to {config_path}")


def get_valid_token(cfg: dict, config_path: str | None = None) -> str | None:
    """Return a valid access token, refreshing if needed."""
    access_token = cfg.get("access_token", "")
    refresh_tok  = cfg.get("refresh_token", "")
    client_id    = cfg.get("client_id", "")

    if access_token:
        return access_token

    if refresh_tok and client_id:
        print("[beatport] Refreshing token...")
        token_data = refresh_access_token(refresh_tok, client_id)
        if token_data and "access_token" in token_data:
            path = Path(config_path) if config_path else Path("config.yaml")
            save_tokens(path, token_data, client_id)
            return token_data["access_token"]

    print("[beatport] No valid token — run: trackfix --auth-beatport")
    return None


# ---------------------------------------------------------------------------
# Interactive auth command
# ---------------------------------------------------------------------------

def run_auth(config_path: str | None = None):
    """Headless Beatport auth — just needs username and password."""
    path = Path(config_path) if config_path else Path("config.yaml")

    # Load existing credentials from config
    cfg = {}
    if path.exists():
        try:
            import yaml
            with open(path) as f:
                loaded = yaml.safe_load(f) or {}
            cfg = loaded.get("metadata", {}).get("beatport", {})
        except Exception:
            pass

    username = cfg.get("username", "")
    password = cfg.get("password", "")

    print("\nBeatport Authentication")

    if not username:
        username = input("Beatport username/email: ").strip()
    else:
        print(f"Username: {username} (from config)")

    if not password:
        password = getpass.getpass("Beatport password: ")

    print("\n[beatport] Fetching client_id...")
    client_id = cfg.get("client_id") or fetch_client_id()
    if not client_id:
        print("[beatport] Could not fetch client_id automatically")
        client_id = input("Enter client_id manually: ").strip()
    else:
        print(f"[beatport] client_id: {client_id[:8]}…")

    print("[beatport] Authenticating...")
    token_data = authorize(username, password, client_id)

    if not token_data or "access_token" not in token_data:
        print("[beatport] Authentication failed")
        return False

    save_tokens(path, token_data, client_id)
    print("[beatport] Authentication successful ✓")
    return True


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def strip_version(title: str) -> str:
    """Strip mix/version info from title for broader search matching."""
    import re
    return re.sub(r"\s*[\(\[].*?[\)\]]", "", title).strip()


def search_beatport(artist: str, title: str, access_token: str) -> dict:
    """Search Beatport for a track. Returns dict with genre."""
    if requests is None:
        return {}

    # Search with version stripped for broader matching
    search_title = strip_version(title)
    query = f"{artist} {search_title}".strip()

    try:
        resp = requests.get(
            f"{API_BASE}/catalog/search",
            params={"q": query, "per_page": 5},
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Without type filter, response has tracks/releases/etc at top level
        tracks = data.get("tracks") or data.get("results") or []
        if not tracks:
            return {}

        track = tracks[0]
        meta = {}

        # genre is a single dict, not a list
        genre = track.get("genre")
        if genre:
            meta["genre"] = genre.get("name", "")

        # year from release date
        release_date = track.get("new_release_date") or track.get("publish_date")
        if release_date:
            meta["year"] = release_date[:4]

        # BPM
        bpm = track.get("bpm")
        if bpm:
            meta["bpm"] = str(bpm)

        # Key — prefer Camelot notation (e.g. 10B), fall back to name (D Major)
        key = track.get("key")
        if key:
            camelot = f"{key.get('camelot_number')}{key.get('camelot_letter')}"
            meta["key"] = camelot if key.get("camelot_number") else key.get("name", "")

        return {k: v for k, v in meta.items() if v}

    except Exception as e:
        print(f"  [beatport] Search error: {e}")
        return {}
