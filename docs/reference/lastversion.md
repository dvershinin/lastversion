---
title: "API Reference: lastversion"
description: "Python API reference for the `lastversion.lastversion` module, including RPM changelog generation and release discovery behavior."
---

::: lastversion.lastversion

### RPM changelog generation

When updating a `.spec` file, you can ask lastversion to generate a concise RPM `%changelog` entry from upstream release notes:

```bash
lastversion path/to/package.spec --changelog
```

Environment variables:

- `OPENAI_API_KEY` or `LASTVERSION_OPENAI_API_KEY`
- `LASTVERSION_OPENAI_MODEL` (default: `gpt-4o-mini`)

Behavior:

- Tries conventional changelog files at the tag (e.g., `CHANGELOG.md`, `NEWS`) via raw Git first, then falls back to API.
- Produces 1–7 short bullets focusing on user-facing changes, fixes, security, and compatibility.
- Falls back to a single line `- upstream release v<version>` if upstream notes are unavailable or the API call fails.
