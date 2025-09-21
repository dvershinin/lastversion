Title: Google-style docstrings for all functions

Scope:
- Apply to all Python functions, methods, and coroutines in this repo
- New and edited code must include Google-style docstrings

Rules:
- Use Google docstring format with sections: Summary, Args, Returns, Raises (as applicable)
- First line: one-sentence summary in imperative mood, ending with a period
- Add type information in Args and Returns sections even if type hints exist
- Document coroutine behavior where relevant (e.g., long-running tasks, cancellation)
- Keep docstrings concise and specific to behavior; avoid restating obvious type hints

Examples:

```python
async def send_message(chat_id: int, text: str) -> int:
    """Send a message to a chat.

    Args:
        chat_id: Target Telegram chat ID.
        text: Message content to send.

    Returns:
        Message ID of the sent message.

    Raises:
        RuntimeError: If sending fails after retries.
    """
    ...
```

Enforcement:
- PRs must include docstrings for all new/modified functions
- Lint review may reject code without proper docstrings


