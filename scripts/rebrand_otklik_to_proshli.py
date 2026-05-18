"""One-shot rebrand from Otklik to Proshli across the monorepo.

Ordered replacements are applied longest-pattern-first so we don't
double-rewrite (e.g. `otklik.ai` must rewrite before the bare
`otklik` catch-all). Cyrillic "отклик/Откликнуться" is the Russian
verb for "to apply to a vacancy" — never touched.

Generated files (`pnpm-lock.yaml`, `uv.lock`, `apps/api/openapi.json`)
are skipped here and regenerated via `pnpm install` / `uv lock`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Skip these directories entirely (recursion stops here).
SKIP_DIRS = {
    ".git", "node_modules", ".next", ".venv", "venv",
    "dist", "build", "storybook-static", ".turbo",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "__pycache__", ".idea", ".vscode",
}

# Skip these exact relative paths — generated, regenerated separately.
SKIP_FILES = {
    "pnpm-lock.yaml",
    "apps/api/uv.lock",
    "apps/workers/uv.lock",
    "apps/api/openapi.json",
    "scripts/rebrand_otklik_to_proshli.py",
}

# Skip these file extensions (binary or irrelevant).
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".ico", ".gif", ".webp",
    ".woff", ".woff2", ".ttf", ".otf",
    ".pdf", ".zip", ".tar", ".gz",
    ".sqlite", ".db",
    ".tsbuildinfo",
}

# Order matters: longest/most-specific first.
REPLACEMENTS: list[tuple[str, str]] = [
    # URLs / emails
    ("staging.otklik.ai", "staging.proshli.ru"),
    ("bot@otklik.ai", "bot@proshli.ru"),
    ("noreply@otklik.ai", "noreply@proshli.ru"),
    ("noreply@otklik.local", "noreply@proshli.local"),
    ("otklik.ai", "proshli.ru"),
    ("otklik.local", "proshli.local"),
    ("otklik.db", "proshli.db"),

    # Brand display
    ("Otklik.ai", "Proshli"),
    ("Otklik AI", "Proshli AI"),

    # Env var prefixes (UPPERCASE)
    ("OTKLIK_API_URL", "PROSHLI_API_URL"),
    ("OTKLIK_BOT_TOKEN", "PROSHLI_BOT_TOKEN"),
    ("OTKLIK_BOT_SERVICE_KEY", "PROSHLI_BOT_SERVICE_KEY"),
    ("OTKLIK_REDIS_URL", "PROSHLI_REDIS_URL"),

    # Package scope
    ("@otklik/", "@proshli/"),

    # Compound infra names (kebab-case)
    ("otklik-api-staging", "proshli-api-staging"),
    ("otklik-web-staging", "proshli-web-staging"),
    ("otklik-workers-staging", "proshli-workers-staging"),
    ("otklik-pg-data", "proshli-pg-data"),
    ("otklik-meili-data", "proshli-meili-data"),
    ("otklik-meili", "proshli-meili"),
    ("otklik-pg", "proshli-pg"),
    ("otklik-redis", "proshli-redis"),
    ("otklik-api", "proshli-api"),
    ("otklik-web", "proshli-web"),
    ("otklik-workers", "proshli-workers"),
    ("otklik-monorepo", "proshli-monorepo"),

    # Snake-case identifiers
    ("otklik_web_token", "proshli_web_token"),

    # Generic standalone (must be last)
    ("Otklik", "Proshli"),
    ("otklik", "proshli"),
]


def is_text_file(path: Path) -> bool:
    """Best-effort binary detection — read first 8KB, look for NUL bytes."""
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        return b"\x00" not in chunk
    except OSError:
        return False


def walk_files() -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = p.relative_to(ROOT).as_posix()
            if rel in SKIP_FILES:
                continue
            if p.suffix.lower() in SKIP_EXTS:
                continue
            if not is_text_file(p):
                continue
            out.append(p)
    return out


def rewrite(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for old, new in REPLACEMENTS:
        if old in text:
            n = text.count(old)
            counts[old] = counts.get(old, 0) + n
            text = text.replace(old, new)
    return text, counts


def main() -> int:
    dry_run = "--apply" not in sys.argv
    files = walk_files()
    total_files_touched = 0
    total_repls: dict[str, int] = {}

    for p in files:
        try:
            original = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new, counts = rewrite(original)
        if not counts:
            continue
        total_files_touched += 1
        for k, v in counts.items():
            total_repls[k] = total_repls.get(k, 0) + v
        if not dry_run:
            # Preserve original line endings — read_text normalised CRLF→LF.
            p.write_text(new, encoding="utf-8", newline="\n")
        print(f"  {'(dry)' if dry_run else 'WRITE'} {p.relative_to(ROOT).as_posix()}: "
              + ", ".join(f"{v}× {k}" for k, v in counts.items()))

    print()
    print(f"Files touched: {total_files_touched}")
    print("Replacements:")
    for k, v in sorted(total_repls.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}× {k}")
    if dry_run:
        print("\nDry run. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
