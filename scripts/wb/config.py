# Self-contained config: all paths relative to repo (organized/).
# Used by legacy scripts; prefer organized.config.settings elsewhere.
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "../.."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from organized.config import settings

ROOT = settings.BASE_DIR_PATH
DOMAINS = settings.DOMAINS
DERIVED = settings.DERIVED_DIR
VARS = settings.VARS
