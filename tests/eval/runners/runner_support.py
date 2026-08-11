from __future__ import annotations

from collections.abc import MutableMapping
import os
from pathlib import Path
import sys
import tempfile

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SRC = PACKAGE_ROOT / "src"
FRAMEWORK_ROOT = PACKAGE_ROOT.parent
OPENMINION_SRC = FRAMEWORK_ROOT / "openminion" / "src"
SOPHIAGRAPH_SRC = FRAMEWORK_ROOT / "sophiagraph" / "src"


def configure_repo_paths() -> None:
    for path in (PACKAGE_SRC, PACKAGE_ROOT, OPENMINION_SRC, SOPHIAGRAPH_SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def generated_output_root(name: str) -> Path:
    configured = os.getenv("OPENMINION_GENERATED_ROOT", "").strip()
    if configured:
        return (Path(configured).expanduser() / name).resolve()

    from openminion.base.generated_paths import resolve_generated_root

    return resolve_generated_root(home_root=FRAMEWORK_ROOT) / name


def isolate_runtime_roots(
    environ: MutableMapping[str, str] | None = None,
    *,
    prefix: str = "openminion-eval-",
) -> Path:
    """Replace ambient OpenMinion roots for executable Eval runners."""
    target = os.environ if environ is None else environ
    home_root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    data_root = home_root / ".openminion"
    generated_root = data_root / "runtime"
    target["OPENMINION_HOME"] = str(home_root)
    target["OPENMINION_DATA_ROOT"] = str(data_root)
    target["OPENMINION_GENERATED_ROOT"] = str(generated_root)
    return generated_root
