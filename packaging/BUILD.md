# Building a standalone Windows app

This turns dj-trackfix into something a non-technical Windows user can just
double-click — no Python, no terminal, no `pip install`. There are three
pieces, built in order:

1. **The GUI** (`trackfix/gui.py`) — already in the repo, ships with the app.
2. **A standalone .exe** — PyInstaller bundles Python + all dependencies.
3. **An installer** — Inno Setup wraps the .exe into `dj-trackfix-setup.exe`
   with a Start Menu entry and uninstaller.

You need to do this on an actual Windows machine — PyInstaller builds for
the OS it runs on, so it can't be cross-compiled from Linux/macOS/this
Cowork sandbox.

## Prerequisites (one-time, on your Windows dev machine)

- Python 3.10+ (already have this)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (free) — only needed for step 3
- A copy of `ffmpeg.exe` — get a static Windows build from
  [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (the "essentials" build is
  enough) or `winget install ffmpeg` and copy the exe out of wherever winget
  put it. dj-trackfix shells out to `ffmpeg` for `--convert`, and a frozen
  exe can't rely on `pip`-installed anything being on PATH, so it has to be
  bundled as a real binary sitting next to the app.

## Step 1 — Build the exe

From the repo root:

```
packaging\build_windows.bat
```

This creates a throwaway `.venv-build`, installs dj-trackfix + PyInstaller
into it, and runs PyInstaller in `--onedir --windowed` mode (a folder, not
a single file — see "Why onedir" below). Output lands in:

```
dist\dj-trackfix-gui\
    dj-trackfix-gui.exe
    _internal\ (or similar, depending on PyInstaller version)
    config.example.yaml
```

Then **copy `ffmpeg.exe` into `dist\dj-trackfix-gui\`**, next to
`dj-trackfix-gui.exe`. The GUI checks for it there at startup and adds that
folder to `PATH` automatically — see `bundled_ffmpeg_dir()` in `gui.py`.

At this point `dist\dj-trackfix-gui\` is a complete, portable app — you can
zip it and hand it to someone, or double-click `dj-trackfix-gui.exe`
directly. Steps 2/3 below just wrap it in a proper installer.

### Why onedir, not onefile

`--onefile` self-extracts to a temp folder on every launch, which means
re-extracting a bundled `ffmpeg.exe` (tens of MB) every single run, and
onefile exes get flagged by Windows Defender/SmartScreen more often than
onedir builds. `--onedir` keeps everything on disk permanently after
install, starts faster, and is what the installer script below expects.

## Step 2 — Test it

Run `dist\dj-trackfix-gui\dj-trackfix-gui.exe` directly. Try:
- Browse to a folder of test tracks, leave "Dry run" checked, hit Run —
  confirm the log shows sensible output and nothing gets modified.
- "Show tags (info)" on a file.
- "Authenticate Beatport…" / "Authenticate Discogs…" — these open in a
  separate console window (they need real keyboard input for
  username/password/verifier prompts, which a windowed app can't provide).

If ffmpeg wasn't copied in correctly, the log shows a warning at startup
and `--convert` will fail — copy `ffmpeg.exe` in and relaunch.

## Step 3 — Build the installer

Open `packaging\installer.iss` in the Inno Setup Compiler and click
**Build**, or from the command line:

```
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

Output: `packaging\output\dj-trackfix-setup.exe` — a single file you can
send to anyone. It installs per-user (no admin/UAC prompt needed) into
`%LocalAppData%\Programs\dj-trackfix`, adds a Start Menu shortcut, and
offers an optional desktop shortcut.

## Where things get written at runtime

- **Config** (`config.yaml`): `%APPDATA%\dj-trackfix\config.yaml`, created
  on first use of the "Edit…" config button. This keeps the app working
  even when installed somewhere read-only, and matches normal Windows
  per-user settings conventions.
- **Converted/sorted/tagged files**: wherever the user's chosen track
  folder is — dj-trackfix never writes inside its own install directory.

## Updating the app later

Bump the version in `pyproject.toml` and `packaging/installer.iss`
(`MyAppVersion`), re-run `build_windows.bat`, re-copy `ffmpeg.exe`, rebuild
the installer. Inno Setup's uninstall/reinstall flow handles upgrades
cleanly since the AppId in `installer.iss` stays fixed.
