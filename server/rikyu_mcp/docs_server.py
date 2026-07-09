"""MCP server for searching the RikyuAgent documentation guide.

Read-only and needs no SSH access. Uses the pre-built packaged index in
rikyu_mcp/data/docs_index, built from the bundled `rikyu_guide.md` (an
original write-up, not a mirror of the official site); queries are embedded
against the configured serving infrastructure when available, with automatic
fallback to keyword search.

The official docs site is not treated as a live reference here — it is
unreliable at the time of writing — so results deliberately carry no URL and
nothing in this server should direct a user to visit one.
"""
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from rikyu_mcp import config
from rikyu_mcp.rag.store import DocsIndex
from rikyu_mcp.serving import serve

mcp = FastMCP("rikyu-docs")


@lru_cache(maxsize=1)
def _index() -> DocsIndex:
    return DocsIndex(config.DOCS_INDEX_DIR)


def _format(result: dict) -> str:
    return f"## {result['breadcrumb']}\n\n{result['text']}"


@mcp.tool()
def search_docs(query: str, top_k: int = 4) -> str:
    """Search the RikyuAgent documentation guide.

    Always call this first before answering any question about Rikyu specifics:
    job submission, modules, storage, login procedure, or any machine-specific
    detail. Do not rely on prior knowledge or the orientation facts embedded in
    skills — those are fallback aids, not authoritative.

    This searches a guide bundled with the agent, not the official Rikyu docs
    site — do not tell the user to visit a URL for more detail; if they need
    something this guide doesn't cover, point them to RIKEN R-CCS support
    instead.

    If this tool errors or returns no results, fall back to the inline facts in
    the active skill and note that docs were unavailable.

    When results begin with `[search_method: bm25]`, inform the user that
    keyword search was used because the embedding server could not be reached.
    Results may miss semantically relevant sections that don't share exact
    keywords with the query.

    Args:
        query: Natural-language question or keywords.
        top_k: Number of sections to return.
    """
    results = _index().search(query, top_k=top_k)
    if not results:
        return "No matching documentation sections found."
    sections = "\n\n---\n\n".join(_format(r) for r in results)
    if results[0]["method"] == "bm25":
        return f"[search_method: bm25]\n\n{sections}"
    return sections


@mcp.tool()
def list_doc_sections() -> str:
    """List every section of the RikyuAgent guide (table of contents)."""
    lines = [f"- {c['breadcrumb']}" for c in _index().chunks]
    return "\n".join(lines)


@mcp.tool()
def read_doc_section(breadcrumb: str) -> str:
    """Read one guide section in full by its breadcrumb.

    Args:
        breadcrumb: Section path as shown by list_doc_sections or search_docs,
            e.g. 'Running jobs'. Partial matches work.
    """
    needle = breadcrumb.lower()
    matches = [c for c in _index().chunks if needle in c["breadcrumb"].lower()]
    if not matches:
        return f"No section matching '{breadcrumb}'. Use list_doc_sections to see all sections."
    return "\n\n---\n\n".join(_format(c) for c in matches)


def main():
    serve(mcp)


if __name__ == "__main__":
    main()
