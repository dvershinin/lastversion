#!/usr/bin/env python3
"""
Pre-commit hook to ensure all documentation files have proper front-matter for SEO.

Required front-matter fields:
- title: Page title for SEO
- description: Meta description for search engines (recommended 100-160 chars)

Usage:
    python scripts/check_docs_frontmatter.py [files...]

If no files are provided, checks all .md files in docs/ directory.
"""

import re
import sys
from pathlib import Path

# Files that don't need front-matter (e.g., snippets, includes)
EXCLUDED_PATTERNS = [
    "snippets/",
    "includes/",
    "_",  # Files starting with underscore
]

# Required front-matter fields
REQUIRED_FIELDS = ["title", "description"]

# Regex to extract YAML front-matter
FRONTMATTER_REGEX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def is_excluded(filepath: Path) -> bool:
    """Check if file should be excluded from front-matter check."""
    filepath_str = str(filepath)
    return any(pattern in filepath_str for pattern in EXCLUDED_PATTERNS)


def extract_frontmatter(content: str) -> str | None:
    """Extract front-matter from markdown content."""
    match = FRONTMATTER_REGEX.match(content)
    if not match:
        return None
    return match.group(1)


def parse_frontmatter(frontmatter_text: str) -> dict[str, str]:
    """Parse YAML front-matter into a dictionary (simple key: value pairs)."""
    fields: dict[str, str] = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                fields[key] = value
    return fields


def check_file(filepath: Path) -> list[str]:
    """Check a single file for proper front-matter."""
    if is_excluded(filepath):
        return []

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [f"{filepath}: Could not read file: {exc}"]

    frontmatter_text = extract_frontmatter(content)
    if frontmatter_text is None:
        return [f"{filepath}: Missing front-matter (no --- block at start of file)"]

    fields = parse_frontmatter(frontmatter_text)
    errors: list[str] = []

    for required_field in REQUIRED_FIELDS:
        if required_field not in fields:
            errors.append(f"{filepath}: Missing required front-matter field: {required_field}")
        elif not fields[required_field]:
            errors.append(f"{filepath}: Empty front-matter field: {required_field}")

    # Check description length (SEO best practice: ~100-160 chars, allow some slack)
    if "description" in fields:
        desc_len = len(fields["description"])
        if desc_len < 50:
            errors.append(f"{filepath}: Description too short ({desc_len} chars, recommend 100-160)")
        elif desc_len > 200:
            errors.append(f"{filepath}: Description too long ({desc_len} chars, recommend 100-160)")

    return errors


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        docs_dir = Path(__file__).parent.parent / "docs"
        files = list(docs_dir.rglob("*.md"))

    all_errors: list[str] = []

    for filepath in files:
        # Only check files in docs/ directory
        if "docs" not in str(filepath):
            continue
        if filepath.suffix != ".md":
            continue
        all_errors.extend(check_file(filepath))

    if all_errors:
        print("Front-matter check failed:\n")
        for error in all_errors:
            print(f"  - {error}")
        print("\nEach documentation file should have front-matter like:\n")
        print("---")
        print('title: "Page Title for SEO"')
        print('description: "A compelling meta description of 100-160 characters for search engines."')
        print("---\n")
        raise SystemExit(1)

    print(f"✅ All {len(files)} documentation files have proper front-matter")


if __name__ == "__main__":
    main()
