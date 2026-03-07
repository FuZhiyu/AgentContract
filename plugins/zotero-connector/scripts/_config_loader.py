"""
Minimal config loader for agent-contract plugins (self-contained copy).

Lookup order:
1. .claude/agent-contract.yaml (project-specific)
2. ~/.config/agent-contract/config.yaml (global fallback)
"""

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

_PROJECT_CONFIG = Path(".claude") / "agent-contract.yaml"
_GLOBAL_CONFIG = Path.home() / ".config" / "agent-contract" / "config.yaml"


def load_config(plugin_name: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if yaml is None:
        raise ImportError("PyYAML is required: pip install pyyaml")

    for path in (_PROJECT_CONFIG, _GLOBAL_CONFIG):
        if path.exists():
            with open(path) as f:
                config = yaml.safe_load(f) or {}
            return config.get(plugin_name, {}) if plugin_name else config

    raise FileNotFoundError(
        f"No config file found. Create one at:\n"
        f"  - {_PROJECT_CONFIG} (project-specific)\n"
        f"  - {_GLOBAL_CONFIG} (global)"
    )


def get_api_key(plugin_name: str, key_name: str) -> str | None:
    """Get a specific API key from plugin config."""
    try:
        return load_config(plugin_name).get(key_name)
    except (FileNotFoundError, ImportError):
        return None


def get_mistral_api_key() -> str | None:
    """Get Mistral API key from paper-reader config."""
    return get_api_key('paper-reader', 'mistral_api_key')


def get_zotero_config() -> dict[str, Any]:
    """Get Zotero configuration from paper-reader config."""
    config = load_config('paper-reader')
    return {
        'api_key': config.get('zotero_api_key'),
        'library_type': config.get('zotero_library_type', 'user'),
        'library_id': config.get('zotero_library_id'),
    }
