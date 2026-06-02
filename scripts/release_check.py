"""Compatibility entrypoint for the canonical package release smoke."""

from __future__ import annotations

from check_release_package import main


if __name__ == "__main__":
    raise SystemExit(main())
