"""Base64-over-SSH download transport.

Encodes the remote file as base64 on the login node and decodes it locally.
Uses `transfer.run_capture` (full stdout) rather than
`middleware.run_command`, whose 200 KB output cap would silently truncate
and corrupt any file whose base64 encoding exceeds that limit.
"""
import base64
from pathlib import Path

from rikyu_mcp.middleware import quote_path
from rikyu_mcp.transfer import register, run_capture


def _decode(b64_text: str) -> bytes:
    """Decode a base64 text blob back into raw bytes."""
    return base64.b64decode(b64_text)


@register("base64")
def base64_transport(remote_path: str, local_dest: Path) -> None:
    """Fetch `remote_path` by base64-encoding it on the login node.

    Runs `base64` on the remote file via `run_capture` — not
    `middleware.run_command` — so the full encoded output is captured even
    when it exceeds the 200 KB truncation cap that `run_command` applies.
    """
    text = run_capture(f"base64 {quote_path(remote_path)}")
    local_dest.write_bytes(_decode(text))
