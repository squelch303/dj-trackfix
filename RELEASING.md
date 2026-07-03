# Releasing dj-trackfix

Pushing a version tag builds the Windows GUI app and publishes it to GitHub
Releases automatically — see `.github/workflows/release.yml`.

## Steps

1. Bump the version:
   - `pyproject.toml` → `version = "..."`
   - `packaging/installer.iss` → the fallback `MyAppVersion` define (cosmetic
     only; CI overrides it from the tag via `/DMyAppVersion`)
2. Add an entry to `CHANGELOG.md` (move `[Unreleased]` items under a new
   version heading).
3. Commit, then tag and push:
   ```bash
   git add -A
   git commit -m "Release 0.3.0"
   git tag 0.3.0
   git push origin main --tags
   ```
4. GitHub Actions picks up the tag push and, on a `windows-latest`
   runner:
   - installs dj-trackfix and PyInstaller
   - builds `dj-trackfix-gui.exe` (onedir)
   - downloads a static Windows ffmpeg build and drops `ffmpeg.exe` next to
     the exe
   - zips the portable build
   - installs Inno Setup and compiles `packaging/installer.iss` into
     `dj-trackfix-<version>-setup.exe`
   - publishes both files to a new GitHub Release for that tag, with
     auto-generated release notes

Watch progress under the repo's **Actions** tab. A run takes a few minutes;
if it fails partway, re-pushing the same tag won't retrigger the workflow —
delete the tag (`git tag -d 0.3.0 && git push origin :refs/tags/0.3.0`),
fix the issue, and re-tag.

## Building locally instead

If you want an exe/installer without going through CI (e.g. to test a
change before tagging), see `packaging/BUILD.md` — same steps, run by hand
on a Windows machine.

## What's not automated

- Version bumps and changelog entries (deliberately manual).
- Code signing — the exe is unsigned, so Windows SmartScreen may warn on
  first run. Not addressed here.
