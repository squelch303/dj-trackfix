"""
Discogs OAuth authentication.
Uses Consumer Key/Secret to obtain an access token via OAuth1.

Run: trackfix --auth-discogs
Tokens are saved to config.yaml (gitignored).
"""

import webbrowser
from pathlib import Path


try:
    import discogs_client
except ImportError:
    discogs_client = None


USER_AGENT = "dj-trackfix/0.2.0"


def save_discogs_tokens(config_path: Path, access_token: str, access_secret: str):
    """Write Discogs access token/secret back into config.yaml."""
    try:
        import yaml
    except ImportError:
        print("[discogs] pyyaml required to save tokens")
        return

    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    config.setdefault("metadata", {}).setdefault("discogs", {})
    config["metadata"]["discogs"]["access_token"]  = access_token
    config["metadata"]["discogs"]["access_secret"] = access_secret
    config["metadata"]["discogs"]["enabled"] = True
    # Clear plain token if present — OAuth supersedes it
    config["metadata"]["discogs"].pop("token", None)

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"[discogs] Tokens saved to {config_path}")


def run_auth_discogs(config_path: str | None = None):
    """Interactive Discogs OAuth flow."""
    if discogs_client is None:
        print("[discogs] Error: discogs-client not installed")
        return False

    path = Path(config_path) if config_path else Path("config.yaml")

    print("\nDiscogs OAuth Authentication")

    # Try to load existing keys from config first
    consumer_key = ""
    consumer_secret = ""
    if path.exists():
        try:
            import yaml
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}
            consumer_key    = cfg.get("metadata", {}).get("discogs", {}).get("consumer_key", "")
            consumer_secret = cfg.get("metadata", {}).get("discogs", {}).get("consumer_secret", "")
        except Exception:
            pass

    if consumer_key and consumer_secret:
        print(f"Using Consumer Key from config: {consumer_key[:6]}…\n")
    else:
        print("You'll need the Consumer Key and Consumer Secret from your app registration.")
        print("https://www.discogs.com/settings/developers\n")
        consumer_key    = input("Consumer Key:    ").strip()
        consumer_secret = input("Consumer Secret: ").strip()

    d = discogs_client.Client(USER_AGENT)
    d.set_consumer_key(consumer_key, consumer_secret)

    try:
        token, secret, url = d.get_authorize_url()
    except Exception as e:
        print(f"[discogs] Failed to get request token: {e}")
        return False

    print(f"\n[discogs] Open this URL in your browser to authorize:")
    print(f"\n  {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass  # WSL / headless — URL already printed above

    verifier = input("\nEnter the verifier code from Discogs: ").strip()

    try:
        access_token, access_secret = d.get_access_token(verifier)
    except Exception as e:
        print(f"[discogs] Failed to get access token: {e}")
        return False

    save_discogs_tokens(path, access_token, access_secret)
    print("[discogs] Authentication successful ✓")
    return True
