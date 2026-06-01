"""Runtime path resolution (placeholder for US-002).

Resolves ``SONISCOPE_HOME`` and derives inbox / fragments / tmp paths.
"""

from __future__ import annotations

from pathlib import Path

# US-002 will implement the full resolution logic.
# For now we expose a constant so imports don't break.
DEFAULT_SONISCOPE_HOME = Path.home() / "SoniScope"
