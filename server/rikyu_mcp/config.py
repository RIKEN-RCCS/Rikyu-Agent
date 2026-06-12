"""Configuration for the rikyu MCP servers.

Settings come from, in order of precedence:
  1. Environment variables (RIKYU_*)
  2. The user config file ~/.rikyu/config.json (path override: RIKYU_CONFIG)
  3. Defaults

The config file is created with the help of the `configuring` skill:

    {
      "ssh": {"host": "rikyu"},
      "embedding": {
        "base_url": "https://your-serving-host/v1",
        "api_key": "...",
        "model": "your-embedding-model"
      }
    }

`ssh.host` is an alias from ~/.ssh/config or a plain user@hostname; key-based
auth is assumed (no credentials are stored here). The embedding endpoint must
speak the OpenAI /v1/embeddings dialect.
"""
import json
import os
from functools import lru_cache
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("RIKYU_CONFIG", "~/.rikyu/config.json")).expanduser()


def _file_config() -> dict:
    """The parsed config file, or {} if absent. Raises on malformed JSON."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed config file {CONFIG_PATH}: {e}") from e


def ssh_host() -> str:
    """SSH destination for the AI4S login node (alias or user@hostname)."""
    return (os.environ.get("RIKYU_HOST")
            or _file_config().get("ssh", {}).get("host")
            or "rikyu")


def embedding() -> dict:
    """Embedding endpoint settings: base_url, api_key, model.

    base_url empty means not configured — docs search falls back to BM25.
    """
    file = _file_config().get("embedding", {})
    return {
        "base_url": os.environ.get("RIKYU_EMBED_BASE_URL") or file.get("base_url") or "",
        "api_key": os.environ.get("RIKYU_EMBED_API_KEY") or file.get("api_key") or "",
        "model": os.environ.get("RIKYU_EMBED_MODEL") or file.get("model") or "",
    }


# --- Static data ------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

DOCS_INDEX_DIR = Path(os.environ.get("RIKYU_DOCS_INDEX", _DATA_DIR / "docs_index"))
DOCS_REPO_URL = "https://github.com/RIKEN-RCCS/ai4s_early_access"
DOCS_SITE_BASE = "https://riken-rccs.github.io/ai4s_early_access/en/"


@lru_cache(maxsize=1)
def load_cluster_config() -> dict:
    """Load the static AI4S cluster description (partitions, modules, storage)."""
    path = Path(os.environ.get("RIKYU_CLUSTER_CONFIG", _DATA_DIR / "ai4s_config.json"))
    with open(path) as f:
        return json.load(f)
