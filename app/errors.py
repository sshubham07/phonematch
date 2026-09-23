"""Domain exceptions, mapped to HTTP codes in one exception handler (added in M6)."""


class LLMUnavailable(Exception):
    """Ollama (or the configured LLM backend) cannot be reached or returned an error."""
