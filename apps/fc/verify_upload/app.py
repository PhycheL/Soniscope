"""FC custom-runtime entrypoint for verify-upload."""

from __future__ import annotations

import os
import sys

_FUNCTION_DIR = os.path.dirname(os.path.abspath(__file__))
_FC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FUNCTION_DIR not in sys.path:
    sys.path.insert(0, _FUNCTION_DIR)
if _FC_ROOT not in sys.path:
    sys.path.insert(0, _FC_ROOT)

from handler import handler  # noqa: E402
from shared.custom_runtime import serve  # noqa: E402


if __name__ == "__main__":
    serve(handler)
