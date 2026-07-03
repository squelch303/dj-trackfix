@echo off
REM ============================================================
REM  dj-trackfix — Windows build script
REM  Builds a standalone dj-trackfix-gui.exe (no Python required
REM  on the user's machine) using PyInstaller.
REM
REM  Run this from the repo root on a Windows machine with Python
REM  3.10+ installed:
REM      packaging\build_windows.bat
REM
REM  Output: dist\dj-trackfix\dj-trackfix-gui.exe  (+ supporting files)
REM  See packaging\BUILD.md for the full walkthrough, including how
REM  to bundle ffmpeg.exe and build the installer.
REM ============================================================

setlocal

cd /d "%~dp0\.."

echo [1/4] Creating build virtualenv (.venv-build)...
python -m venv .venv-build
call .venv-build\Scripts\activate.bat

echo [2/4] Installing dj-trackfix + build deps...
pip install --upgrade pip >nul
pip install -e .
pip install pyinstaller

echo [3/4] Running PyInstaller...
pyinstaller ^
    --name dj-trackfix-gui ^
    --windowed ^
    --noconfirm ^
    --paths . ^
    --add-data "config.example.yaml;." ^
    --hidden-import musicbrainzngs ^
    --hidden-import discogs_client ^
    --collect-all discogs_client ^
    trackfix\gui.py

echo [4/4] Done.
echo.
echo Output folder: dist\dj-trackfix-gui\
echo.
echo NEXT STEP: copy ffmpeg.exe into dist\dj-trackfix-gui\ next to
echo dj-trackfix-gui.exe (see packaging\BUILD.md) before building the
echo installer or handing the folder to a user.

endlocal
