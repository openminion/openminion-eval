"""Module entrypoint for `python -m openminion_eval`."""

from __future__ import annotations

import sys

from openminion_eval.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
