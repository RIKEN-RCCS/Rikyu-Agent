"""Configuration for the rikyu MCP servers.

Everything cluster- or site-specific lives here, sourced from environment
variables with AI4S defaults. The SSH host is an alias resolved by the
user's ~/.ssh/config (no credentials are stored in this project).
"""
import json
import os
from functools import lru_cache
from pathlib import Path

# --- Cluster access -------------------------------------------------------

# SSH host alias for the AI4S login node (configure in ~/.ssh/config).
HOST = os.environ.get("RIKYU_HOST", "rikyu")

# --- Cluster description ---------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def load_cluster_config() -> dict:
    """Load the static AI4S cluster description (partitions, modules, storage)."""
    path = Path(os.environ.get("RIKYU_CLUSTER_CONFIG", _DATA_DIR / "ai4s_config.json"))
    with open(path) as f:
        return json.load(f)


# --- Documentation / RAG ---------------------------------------------------

DOCS_INDEX_DIR = Path(os.environ.get("RIKYU_DOCS_INDEX", _DATA_DIR / "docs_index"))
DOCS_REPO_URL = "https://github.com/RIKEN-RCCS/ai4s_early_access"
DOCS_SITE_BASE = "https://riken-rccs.github.io/ai4s_early_access/en/"

# Custom embedding endpoint (OpenAI-compatible /v1/embeddings shape).
# When unset, the docs server falls back to keyword (BM25) search.
EMBED_BASE_URL = os.environ.get("RIKYU_EMBED_BASE_URL")
EMBED_MODEL = os.environ.get("RIKYU_EMBED_MODEL", "")
EMBED_API_KEY = os.environ.get("RIKYU_EMBED_API_KEY", "")
