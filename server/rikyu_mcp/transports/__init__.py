"""Download transport implementations.

Each module in this package registers one (or more) transport under a name via
``@rikyu_mcp.transfer.register(...)``. They are auto-discovered and imported by
``rikyu_mcp.transfer`` on first use, so dropping a new ``t_*.py`` file here is
all it takes to add a transport — no central registry edit required.
"""
