"""
Standalone entry point for PyInstaller.

PyInstaller executes whatever script you point it at as `__main__` — the
same as running `python trackfix/gui.py` directly. trackfix/gui.py lives
inside the `trackfix` package and uses relative imports (`from . import
__version__`, `from .config import load_config`, etc.), which only work
when the module is imported *as part of* the package (`python -m
trackfix.gui`, or the pip-installed `trackfix-gui` entry point) — not when
frozen as the __main__ script directly, which is exactly what caused:

    ImportError: attempted relative import with no known parent package

This shim uses an absolute import instead, so it has no such problem when
frozen. packaging/build_windows.bat and .github/workflows/release.yml both
point PyInstaller at this file, not at trackfix/gui.py.
"""

from trackfix.gui import main

if __name__ == "__main__":
    main()
