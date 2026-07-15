"""Fail closed when repository files appear to contain credentials or private keys."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".publish-venv", ".testdeps", ".venv", "venv", "__pycache__"}
BLOCKED_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".secret"}
BLOCKED_NAMES = {".env", "cookies.txt", "cookie.txt"}
PATTERNS = {
    "private-key": re.compile("-----" + r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "master-key": re.compile(r"P115RAPIDRETRY_KEY\s*[:=]\s*['\"]?[A-Za-z0-9_-]{40,}"),
    "plaintext-cookie": re.compile(
        r"UID=[^;\s]{8,};\s*CID=[^;\s]{8,};\s*SEID=[^;\s]{8,}", re.IGNORECASE
    ),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}\b"),
}


def candidates():
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    findings: list[tuple[str, str, int]] = []
    for path in candidates():
        relative = path.relative_to(ROOT).as_posix()
        lower_name = path.name.lower()
        if path.suffix.lower() in BLOCKED_SUFFIXES or lower_name in BLOCKED_NAMES:
            findings.append((relative, "blocked-secret-file", 0))
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append((relative, label, number))

    if findings:
        print("Security scan failed. Content is intentionally not displayed:", file=sys.stderr)
        for relative, label, number in findings:
            location = f":{number}" if number else ""
            print(f"- {relative}{location} [{label}]", file=sys.stderr)
        return 1
    print("Security scan passed: no credential patterns or secret files found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
