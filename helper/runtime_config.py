"""Read required secrets without a source-code fallback."""
import os


def required_env(name):
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Set the {name} environment variable before starting.")
    return value
