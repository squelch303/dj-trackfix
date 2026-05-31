"""
dj-trackfix CLI entry point.

Usage:
    trackfix --all --input /path/to/tracks
    trackfix --convert --fix --input /path/to/tracks --dry-run
    trackfix --meta --input track.aiff --verbose
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .convert import run_convert
from .fix import run_fix
from .sort import run_sort
from .metadata import run_meta
from .report import print_report
from .beatport import run_auth
from .discogs_auth import run_auth_discogs
from .info import run_info
from .setmeta import run_set


def main():
    parser = argparse.ArgumentParser(
        prog="trackfix",
        description=f"dj-trackfix v{__version__} — DJ audio file toolkit",
    )

    # Operations
    ops = parser.add_argument_group("Operations")
    ops.add_argument("--all",     "-a", action="store_true", help="Run all operations (fix → convert → meta → sort)")
    ops.add_argument("--set",          action="append", metavar="field=value", help="Manually set a tag (e.g. --set genre='Hard Trance'). Repeatable.")
    ops.add_argument("--convert", "-c", action="store_true", help="Convert audio files to target format")
    ops.add_argument("--fix",     "-f", action="store_true", help="Fix filenames (brackets, leading numbers)")
    ops.add_argument("--sort",    "-s", action="store_true", help="Sort files into genre/artist/year subfolders")
    ops.add_argument("--meta",    "-m", action="store_true", help="Look up and write metadata tags")

    # Options
    opts = parser.add_argument_group("Options")
    opts.add_argument("--input",   "-i", default=".", help="Input file or directory (default: current dir)")
    opts.add_argument("--config",  "-C", default=None, help="Path to config.yaml (default: ./config.yaml)")
    opts.add_argument("--dry-run", "-n", action="store_true", help="Preview changes without writing anything")
    opts.add_argument("--verbose", "-v", action="store_true", help="Print every action")
    opts.add_argument("--report",  "-r", action="store_true", help="Print summary report at the end")
    opts.add_argument("--info",          "-I", action="store_true", help="Display current tags on files (read-only)")
    opts.add_argument("--auth-beatport", action="store_true", help="Authenticate with Beatport and save tokens to config.yaml")
    opts.add_argument("--auth-discogs",  action="store_true", help="Authenticate with Discogs (OAuth) and save tokens to config.yaml")
    opts.add_argument("--version", action="version", version=f"dj-trackfix {__version__}")

    args = parser.parse_args()

    # Info — standalone read-only, exits after
    if args.info:
        input_path = Path(args.input).resolve()
        run_info(input_path)
        sys.exit(0)

    # Auth flows — standalone, exit after
    if args.auth_beatport:
        run_auth(args.config)
        sys.exit(0)

    if args.auth_discogs:
        run_auth_discogs(args.config)
        sys.exit(0)

    # Resolve operations
    do_all = args.all
    do_convert = args.convert or do_all
    do_fix     = args.fix     or do_all
    do_sort    = args.sort    or do_all
    do_meta    = args.meta    or do_all
    do_report  = args.report  or do_all

    if args.set:
        input_path = Path(args.input).resolve()
        results = run_set(input_path, args.set, dry_run=args.dry_run, verbose=args.verbose)
        print_report([], [], [], results, output_file="")
        sys.exit(0)

    if not any([do_convert, do_fix, do_sort, do_meta]):
        parser.print_help()
        sys.exit(0)

    # Load config
    config = load_config(args.config)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: input path not found: {input_path}")
        sys.exit(1)

    dry_run = args.dry_run
    verbose = args.verbose

    if dry_run:
        print("\n[dry-run] No files will be modified.\n")

    convert_results = []
    fix_results     = []
    sort_results    = []
    meta_results    = []

    # Run in sensible order: fix names → convert → metadata → sort
    if do_fix:
        print()
        fix_results = run_fix(input_path, config, dry_run, verbose)

    if do_convert:
        print()
        convert_results = run_convert(input_path, config, dry_run, verbose)

    if do_meta:
        print()
        meta_results = run_meta(input_path, config, dry_run, verbose)

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


if __name__ == "__main__":
    main()
