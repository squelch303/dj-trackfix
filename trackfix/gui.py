"""
dj-trackfix GUI — Tkinter front-end for the trackfix CLI.

Zero extra dependencies: built entirely on the Python standard library
(tkinter) so it can be frozen into a Windows .exe with PyInstaller
alongside the existing `trackfix` package, without adding new install
requirements.

Drag & drop: dragging a folder onto the app's .exe (or a shortcut to it)
passes that folder as argv[1] — Windows does this automatically — so the
GUI opens pre-loaded with that folder. No drag/drop library needed.

Run directly with:
    python -m trackfix.gui
Or, once installed:
    trackfix-gui
"""

import os
import queue
import sys
import threading
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

from . import __version__
from . import beatport
from . import discogs_auth
from .config import load_config
from .convert import run_convert
from .fix import run_fix
from .sort import run_sort
from .metadata import run_meta
from .report import print_report
from .info import run_info

DONE_SENTINEL = "\0__TRACKFIX_GUI_DONE__\0"


def default_config_path() -> Path:
    """
    A user-writable location for config.yaml, independent of where the app
    is installed (e.g. Program Files, which is read-only without admin
    rights). Mirrors the usual Windows convention of storing per-user
    settings under %APPDATA%.
    """
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "dj-trackfix" / "config.yaml"


def bundled_ffmpeg_dir() -> Path | None:
    """
    If this is a PyInstaller-frozen build with ffmpeg.exe placed next to
    the executable (see BUILD.md), return that directory so it can be
    added to PATH. Returns None when running from source / not frozen.
    """
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).parent
        if (app_dir / "ffmpeg.exe").exists():
            return app_dir
    return None


def example_config_path() -> Path | None:
    """
    Locate config.example.yaml both when running from source and when
    frozen by PyInstaller (bundled via --add-data "config.example.yaml;.",
    which lands in sys._MEIPASS regardless of onefile/onedir mode).
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    candidate = base / "config.example.yaml"
    return candidate if candidate.exists() else None


class QueueWriter:
    """File-like object that pushes print() output into a thread-safe queue."""

    def __init__(self, q: "queue.Queue[str]"):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(s)
        return len(s)

    def flush(self):
        pass


class TrackfixGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"dj-trackfix v{__version__}")
        self.geometry("680x600")
        self.minsize(560, 480)

        # Make sure a bundled ffmpeg.exe (if present) is found by ffmpeg-python.
        ffmpeg_dir = bundled_ffmpeg_dir()
        if ffmpeg_dir:
            os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")

        self.input_path = tk.StringVar()
        self.config_path = tk.StringVar(value=str(default_config_path()))

        self.var_fix = tk.BooleanVar(value=True)
        self.var_convert = tk.BooleanVar(value=True)
        self.var_meta = tk.BooleanVar(value=True)
        self.var_sort = tk.BooleanVar(value=False)

        self.var_dry_run = tk.BooleanVar(value=True)
        self.var_verbose = tk.BooleanVar(value=False)
        self.var_report = tk.BooleanVar(value=True)
        self.var_recursive = tk.BooleanVar(value=False)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.worker = None

        self._build_ui()
        self._poll_log_queue()

        if not ffmpeg_dir and getattr(sys, "frozen", False):
            self._append_log(
                "[warning] ffmpeg.exe not found next to the app — --convert will fail.\n"
                "See BUILD.md for how to bundle it.\n\n"
            )

    # ---- UI construction ------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Track folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.input_path).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(top, text="Browse…", command=self._browse_folder).pack(side="left")

        hint = ttk.Label(
            self,
            text="Tip: drag a folder onto the app's shortcut/icon to open it pre-loaded here.",
            foreground="#666666",
        )
        hint.pack(fill="x", padx=8)

        ops = ttk.LabelFrame(self, text="Operations")
        ops.pack(fill="x", **pad)
        ttk.Checkbutton(ops, text="Fix filenames", variable=self.var_fix).grid(
            row=0, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(
            ops, text="Convert audio (WAV/M4A → AIFF)", variable=self.var_convert
        ).grid(row=0, column=1, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(
            ops, text="Look up & write metadata", variable=self.var_meta
        ).grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(
            ops, text="Sort into subfolders", variable=self.var_sort
        ).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        opts = ttk.LabelFrame(self, text="Options")
        opts.pack(fill="x", **pad)
        ttk.Checkbutton(
            opts, text="Dry run (preview only, changes nothing)", variable=self.var_dry_run
        ).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        ttk.Checkbutton(opts, text="Verbose", variable=self.var_verbose).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(opts, text="Report at end", variable=self.var_report).grid(
            row=1, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Checkbutton(
            opts, text="Recursive (metadata scan)", variable=self.var_recursive
        ).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        cfgrow = ttk.Frame(self)
        cfgrow.pack(fill="x", **pad)
        ttk.Label(cfgrow, text="Config file:").pack(side="left")
        ttk.Entry(cfgrow, textvariable=self.config_path).pack(
            side="left", fill="x", expand=True, padx=6
        )
        ttk.Button(cfgrow, text="Browse…", command=self._browse_config).pack(side="left")
        ttk.Button(cfgrow, text="Edit…", command=self._edit_config).pack(
            side="left", padx=(6, 0)
        )

        authrow = ttk.Frame(self)
        authrow.pack(fill="x", **pad)
        ttk.Button(
            authrow, text="Authenticate Beatport…", command=self._auth_beatport
        ).pack(side="left")
        ttk.Button(
            authrow, text="Authenticate Discogs…", command=self._auth_discogs
        ).pack(side="left", padx=(6, 0))
        ttk.Button(authrow, text="Show tags (info)", command=self._run_info).pack(
            side="left", padx=(6, 0)
        )

        runrow = ttk.Frame(self)
        runrow.pack(fill="x", **pad)
        self.run_button = ttk.Button(runrow, text="Run", command=self._run)
        self.run_button.pack(side="left")
        ttk.Button(runrow, text="Clear log", command=self._clear_log).pack(
            side="left", padx=(6, 0)
        )

        self.log = scrolledtext.ScrolledText(self, state="disabled", height=18, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, **pad)

    # ---- Log handling -----------------------------------------------------

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                if text == DONE_SENTINEL:
                    continue
                self._append_log(text)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    # ---- Actions ------------------------------------------------------

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select track folder")
        if path:
            self.input_path.set(path)

    def _browse_config(self):
        path = filedialog.askopenfilename(
            title="Select config.yaml",
            filetypes=[("YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self.config_path.set(path)

    def _edit_config(self):
        path_str = self.config_path.get().strip() or str(default_config_path())
        p = Path(path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            example = example_config_path()
            if example:
                p.write_text(example.read_text())
            else:
                p.write_text("# dj-trackfix config\n")
        self.config_path.set(str(p))
        try:
            os.startfile(str(p))  # noqa: this GUI targets Windows only
        except Exception as e:
            messagebox.showerror("Error", f"Could not open config file:\n{e}")

    def _auth_config_path(self) -> Path:
        path_str = self.config_path.get().strip() or str(default_config_path())
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.set(str(path))
        return path

    def _load_metadata_section(self, path: Path, source: str) -> dict:
        if not path.exists():
            return {}
        try:
            import yaml

            with open(path) as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("metadata", {}).get(source, {})
        except Exception:
            return {}

    def _auth_beatport(self):
        """
        Beatport's CLI flow (beatport.run_auth) prompts for username/password
        on stdin via input()/getpass — that needs a real console, which a
        windowed GUI app doesn't have. This asks for the same values via
        Tkinter dialogs instead and calls the same underlying functions
        (fetch_client_id / authorize / save_tokens), so nothing about the
        actual auth logic is duplicated — just how the values are collected.
        """
        path = self._auth_config_path()
        cfg = self._load_metadata_section(path, "beatport")

        username = cfg.get("username") or simpledialog.askstring(
            "Beatport", "Beatport username/email:", parent=self
        )
        if not username:
            return
        password = simpledialog.askstring(
            "Beatport", "Beatport password:", parent=self, show="*"
        )
        if not password:
            return

        def job():
            print("\nBeatport Authentication")
            print("[beatport] Fetching client_id...")
            client_id = cfg.get("client_id") or beatport.fetch_client_id()
            if not client_id:
                print("[beatport] Could not fetch client_id automatically")
                return
            print(f"[beatport] client_id: {client_id[:8]}…")
            print("[beatport] Authenticating...")
            token_data = beatport.authorize(username, password, client_id)
            if not token_data or "access_token" not in token_data:
                print("[beatport] Authentication failed")
                return
            beatport.save_tokens(path, token_data, client_id)
            print("[beatport] Authentication successful ✓")

        self._start_worker(job)

    def _auth_discogs(self):
        """Same reasoning as _auth_beatport — native dialogs instead of a
        console, calling discogs_auth's existing token-exchange functions."""
        try:
            import discogs_client
        except ImportError:
            messagebox.showerror(
                "Missing dependency", "discogs-client is not installed."
            )
            return

        path = self._auth_config_path()
        cfg = self._load_metadata_section(path, "discogs")

        consumer_key = cfg.get("consumer_key", "")
        consumer_secret = cfg.get("consumer_secret", "")
        if not (consumer_key and consumer_secret):
            consumer_key = simpledialog.askstring(
                "Discogs", "Consumer Key:", parent=self
            )
            if not consumer_key:
                return
            consumer_secret = simpledialog.askstring(
                "Discogs", "Consumer Secret:", parent=self, show="*"
            )
            if not consumer_secret:
                return

        client = discogs_client.Client(discogs_auth.USER_AGENT)
        client.set_consumer_key(consumer_key, consumer_secret)

        try:
            _token, _secret, url = client.get_authorize_url()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get request token:\n{e}")
            return

        try:
            webbrowser.open(url)
        except Exception:
            pass

        verifier = simpledialog.askstring(
            "Discogs",
            "A browser window should have opened to authorize dj-trackfix.\n"
            f"If not, open this URL manually:\n{url}\n\n"
            "Enter the verifier code from Discogs:",
            parent=self,
        )
        if not verifier:
            return

        def job():
            try:
                access_token, access_secret = client.get_access_token(verifier)
            except Exception as e:
                print(f"[discogs] Failed to get access token: {e}")
                return
            discogs_auth.save_discogs_tokens(path, access_token, access_secret)
            print("[discogs] Authentication successful ✓")

        self._start_worker(job)

    def _run_info(self):
        path = self.input_path.get().strip()
        if not path:
            messagebox.showwarning("No folder", "Pick a track folder first.")
            return
        self._start_worker(lambda: run_info(Path(path).resolve()))

    def _run(self):
        path = self.input_path.get().strip()
        if not path:
            messagebox.showwarning("No folder", "Pick a track folder first.")
            return
        if not Path(path).exists():
            messagebox.showerror("Not found", f"Path not found:\n{path}")
            return

        do_fix = self.var_fix.get()
        do_convert = self.var_convert.get()
        do_meta = self.var_meta.get()
        do_sort = self.var_sort.get()
        do_report = self.var_report.get()
        dry_run = self.var_dry_run.get()
        verbose = self.var_verbose.get()
        recursive = self.var_recursive.get()
        config_path = self.config_path.get().strip() or None

        if not any([do_fix, do_convert, do_meta, do_sort]):
            messagebox.showwarning("Nothing to do", "Select at least one operation.")
            return

        def job():
            config = load_config(config_path)
            input_path = Path(path).resolve()

            fix_results = convert_results = meta_results = sort_results = []

            if dry_run:
                print("\n[dry-run] No files will be modified.\n")

            if do_fix:
                print()
                fix_results = run_fix(input_path, config, dry_run, verbose)
            if do_convert:
                print()
                convert_results = run_convert(
                    input_path, config, dry_run, verbose, in_place=False
                )
            if do_meta:
                print()
                meta_results = run_meta(
                    input_path,
                    config,
                    dry_run,
                    verbose,
                    ext_filter=None,
                    recursive=recursive,
                    overwrite_fields=None,
                )
            if do_sort:
                print()
                sort_results = run_sort(input_path, config, dry_run, verbose)

            if do_report or config["report"]["enabled"]:
                print_report(
                    convert_results,
                    fix_results,
                    sort_results,
                    meta_results,
                    output_file=config["report"].get("output_file", ""),
                )

            print("\nDone.\n")

        self._start_worker(job)

    def _start_worker(self, job):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "A run is already in progress.")
            return

        self.run_button.configure(state="disabled")

        def wrapped():
            old_stdout = sys.stdout
            sys.stdout = QueueWriter(self.log_queue)
            try:
                job()
            except Exception as e:
                print(f"\n[error] {e}\n")
            finally:
                sys.stdout = old_stdout
                self.log_queue.put(DONE_SENTINEL)

        self.worker = threading.Thread(target=wrapped, daemon=True)
        self.worker.start()
        self._watch_worker()

    def _watch_worker(self):
        if self.worker and self.worker.is_alive():
            self.after(200, self._watch_worker)
        else:
            self.run_button.configure(state="normal")


def main():
    app = TrackfixGUI()
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.exists() and candidate.is_dir():
            app.input_path.set(str(candidate.resolve()))
    app.mainloop()


if __name__ == "__main__":
    main()
