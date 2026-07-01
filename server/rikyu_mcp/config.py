"""Configuration for the rikyu MCP servers.

Settings come from, in order of precedence:
  1. Environment variables (RIKYU_*)
  2. The user config file ~/.rikyu/config.json (path override: RIKYU_CONFIG)
  3. Defaults

The config file is created with the help of the `configuring` skill:

    {
      "ssh": {"host": "rikyu"},
      "embedding": {"api_key": "..."}
    }

`ssh.host` is an alias from ~/.ssh/config or a plain user@hostname; key-based
auth is assumed (no credentials are stored here). The embedding endpoint and
model are hardcoded constants (EMBED_BASE_URL / EMBED_MODEL) — changing them
requires a full re-ingest of the docs index.
"""
import json
import os
from contextlib import ExitStack
from functools import lru_cache
from importlib import resources
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
    """SSH destination for the Rikyu login node (alias or user@hostname)."""
    return (os.environ.get("RIKYU_HOST")
            or _file_config().get("ssh", {}).get("host")
            or "rikyu")


def download_transport() -> str:
    """Default transport for fs_download.

    Resolved in order: RIKYU_DOWNLOAD_TRANSPORT, then local.download_transport
    in the config file, then "rsync". The benchmark (see
    __reports__/fs-download-rework/findings.md) found rsync fastest for large
    files with resume+checksum; "scp" is an equally reasonable choice for
    maximum universality. Switching the default is a config change, not code.
    """
    return (os.environ.get("RIKYU_DOWNLOAD_TRANSPORT")
            or _file_config().get("local", {}).get("download_transport")
            or "rsync")


EMBED_BASE_URL = "http://llm.ai.r-ccs.riken.jp:11434/v1"
EMBED_MODEL = "bge-m3:567m"


def embed_api_key() -> str:
    """API key for the embedding endpoint (the only user-configurable embedding setting).

    Resolved in order: RIKYU_EMBED_API_KEY, then RCCS_EMBED_API_KEY, then
    embedding.api_key in the config file. RCCS_EMBED_API_KEY is a shared fallback:
    the embedding endpoint is common RIKEN R-CCS infrastructure, so a user running
    several R-CCS plugins (e.g. this and the HOKUSAI plugin) can export the one key
    once instead of repeating it in each plugin's config. Empty string means no
    auth header is sent.
    """
    file = _file_config().get("embedding", {})
    return (os.environ.get("RIKYU_EMBED_API_KEY")
            or os.environ.get("RCCS_EMBED_API_KEY")
            or file.get("api_key") or "")


# --- Static data ------------------------------------------------------------

_RESOURCE_STACK = ExitStack()


def _bundled_data_dir() -> Path:
    """Filesystem path to package data, including zip-safe extraction fallback."""
    data = resources.files("rikyu_mcp") / "data"
    return _RESOURCE_STACK.enter_context(resources.as_file(data))


_DATA_DIR = _bundled_data_dir()

DOCS_INDEX_DIR = Path(os.environ.get("RIKYU_DOCS_INDEX", _DATA_DIR / "docs_index"))
DOCS_REPO_URL = "https://github.com/RIKEN-RCCS/ai4s_early_access"
DOCS_SITE_BASE = "https://riken-rccs.github.io/ai4s_early_access/en/"


@lru_cache(maxsize=1)
def load_cluster_config() -> dict:
    """Load the static Rikyu cluster description (partitions, modules, storage)."""
    path = Path(os.environ.get("RIKYU_CLUSTER_CONFIG", _DATA_DIR / "rikyu_config.json"))
    with open(path) as f:
        return json.load(f)


# --- Local filesystem paths --------------------------------------------------

def download_dir() -> Path:
    """Local directory that downloaded files land in when no explicit path is given.

    Resolved in order: RIKYU_DOWNLOAD_DIR, then local.download_dir in the config
    file, then the current working directory. Always returned as an absolute,
    expanded Path.
    """
    raw = (os.environ.get("RIKYU_DOWNLOAD_DIR")
           or _file_config().get("local", {}).get("download_dir")
           or str(Path.cwd()))
    return Path(raw).expanduser().resolve()


def resolve_local_dest(remote_path: str, local_path: str | None) -> Path:
    """Decide the local filesystem destination for a file downloaded from the cluster.

    If local_path is None, the file lands in download_dir() under the remote
    file's basename. Otherwise local_path is treated as a directory (if it
    already exists as one, or ends with a path separator) and the remote
    basename is appended, or as the full destination path otherwise. The
    parent directory is created if missing.

    If the config file sets a truthy local.sandbox, the resolved destination
    must stay inside download_dir(); ValueError is raised if it would escape.
    """
    basename = os.path.basename(remote_path.rstrip("/"))

    if local_path is None:
        dest = download_dir() / basename
    else:
        expanded = Path(local_path).expanduser()
        if not expanded.is_absolute():
            expanded = Path.cwd() / expanded
        if expanded.is_dir() or local_path.endswith(os.sep):
            dest = expanded / basename
        else:
            dest = expanded

    dest.parent.mkdir(parents=True, exist_ok=True)

    if _file_config().get("local", {}).get("sandbox"):
        sandbox_root = download_dir().resolve()
        if not dest.resolve().is_relative_to(sandbox_root):
            raise ValueError(
                f"Refusing to write outside the sandboxed download directory "
                f"{sandbox_root}: resolved destination {dest.resolve()}"
            )

    return dest.resolve()
