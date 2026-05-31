"""
Report generation for dj-trackfix.
Summarises results from all operations.
"""

from pathlib import Path


STATUS_LABELS = {
    "converted":  "Converted",
    "skipped":    "Skipped (exists)",
    "fixed":      "Fixed",
    "unchanged":  "Unchanged",
    "sorted":     "Sorted",
    "updated":    "Metadata updated",
    "no_data":    "No metadata found",
    "dry_run":    "Dry run",
    "error":      "Error",
}


def summarise(label: str, results: list[dict]) -> list[str]:
    if not results:
        return []

    lines = [f"\n  {label}"]
    counts: dict[str, int] = {}
    errors = []

    for r in results:
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        if status == "error":
            errors.append(f"    ✗ {r['src'].name}: {r.get('error', '?')}")

    for status, count in sorted(counts.items()):
        label_str = STATUS_LABELS.get(status, status)
        lines.append(f"    {count:4d}  {label_str}")

    if errors:
        lines.append("  Errors:")
        lines.extend(errors)

    return lines


def print_report(
    convert_results: list[dict],
    fix_results: list[dict],
    sort_results: list[dict],
    meta_results: list[dict],
    output_file: str = "",
):
    lines = ["", "=" * 50, "  dj-trackfix — Run Report", "=" * 50]

    lines += summarise("Convert", convert_results)
    lines += summarise("Fix filenames", fix_results)
    lines += summarise("Sort", sort_results)
    lines += summarise("Metadata", meta_results)

    total_errors = sum(
        1 for r in (convert_results + fix_results + sort_results + meta_results)
        if r.get("status") == "error"
    )

    lines += ["", "=" * 50]
    if total_errors:
        lines.append(f"  ⚠  {total_errors} error(s) — review above")
    else:
        lines.append("  ✓  All done")
    lines.append("=" * 50)

    output = "\n".join(lines)
    print(output)

    if output_file:
        try:
            Path(output_file).write_text(output + "\n", encoding="utf-8")
            print(f"\n[report] Written to: {output_file}")
        except Exception as e:
            print(f"\n[report] Could not write report file: {e}")
