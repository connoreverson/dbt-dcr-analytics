from __future__ import annotations

import sys

# Force UTF-8 output on Windows (cp1252 cannot encode ✓ ✗ ⚠ → characters)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scripts.preflight.cli import main

sys.exit(main())
