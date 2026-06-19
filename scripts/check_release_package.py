"""Build and smoke-test the standalone openminion-eval package."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def _single_artifact(dist_dir: Path, suffix: str) -> Path:
    matches = sorted(dist_dir.glob(f"*{suffix}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {suffix} artifact, got {matches!r}")
    return matches[0]


def _remove_build_residue() -> None:
    for path in (
        REPO_ROOT / "build",
        REPO_ROOT / "dist",
        REPO_ROOT / "src" / "openminion_eval.egg-info",
    ):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def _assert_package_docs_shape() -> None:
    required_paths = [
        REPO_ROOT / "docs" / "README.md",
        REPO_ROOT / "docs" / "certification-readiness-matrix.md",
        REPO_ROOT / "docs" / "eval-cases.md",
        REPO_ROOT / "docs" / "eval-families.md",
        REPO_ROOT / "docs" / "standalone-claim-alignment.md",
        REPO_ROOT / "docs" / "source-tree-owner-map.md",
        REPO_ROOT / "src" / "openminion_eval" / "README.md",
        REPO_ROOT / "API_COMPATIBILITY.md",
        REPO_ROOT / "RELEASING.md",
    ]
    missing = [
        str(path.relative_to(REPO_ROOT)) for path in required_paths if not path.exists()
    ]
    if missing:
        raise RuntimeError(f"package docs/layout drifted: missing {missing!r}")


def _smoke_script() -> str:
    return r"""
from __future__ import annotations

import importlib
from importlib.metadata import distribution
from importlib import resources
import os
from pathlib import Path
from typing import get_args

import openminion_eval
from openminion_eval import (
    EVAL_INTERFACE_VERSION,
    EvalCase,
    EvalRunContext,
    EvalRunManifest,
    EvalRunner,
    EvalSubjectInterface,
    GoalDriftSignalKind,
    GradeMode,
    build_run_manifest,
    compare_suite_results,
    hash_transcripts,
    registered_cases,
)
from openminion_eval.cases import grade_case
from openminion_eval.skills import (
    load_nl_named_skill_manifest,
    load_skill_quality_manifest,
)

target_root = Path(os.environ["OPENMINION_EVAL_RELEASE_TARGET"]).resolve()
package_file = Path(openminion_eval.__file__).resolve()
if not package_file.is_relative_to(target_root):
    raise SystemExit(f"imported package from {package_file}, expected {target_root}")

if EVAL_INTERFACE_VERSION != "v1":
    raise SystemExit(f"unexpected eval interface version: {EVAL_INTERFACE_VERSION!r}")
if EvalRunner.__name__ != "EvalRunner":
    raise SystemExit("EvalRunner root export missing")
if EvalRunContext.__name__ != "EvalRunContext":
    raise SystemExit("EvalRunContext root export missing")
if EvalSubjectInterface.__name__ != "EvalSubjectInterface":
    raise SystemExit("EvalSubjectInterface root export missing")
if EvalCase.__name__ != "EvalCase":
    raise SystemExit("EvalCase root export missing")
if EvalRunManifest.__name__ != "EvalRunManifest":
    raise SystemExit("EvalRunManifest root export missing")
if not callable(build_run_manifest):
    raise SystemExit("build_run_manifest root export missing")
if not callable(compare_suite_results):
    raise SystemExit("compare_suite_results root export missing")
if not callable(hash_transcripts):
    raise SystemExit("hash_transcripts root export missing")
if GradeMode.STRUCTURAL.value != "structural":
    raise SystemExit("GradeMode root export drifted")
if len(registered_cases()) != 5:
    raise SystemExit("starter EvalCase registry drifted")
if grade_case(registered_cases()[0]).case_id != registered_cases()[0].case_id:
    raise SystemExit("EvalCase grading smoke failed")

dist_files = {str(path) for path in distribution("openminion-eval").files or ()}
if not any(path.endswith("dist-info/licenses/LICENSE") for path in dist_files):
    raise SystemExit("LICENSE missing from installed wheel metadata")
if not any(path.endswith("dist-info/licenses/NOTICE") for path in dist_files):
    raise SystemExit("NOTICE missing from installed wheel metadata")

if set(get_args(GoalDriftSignalKind)) != {
    "actions_diverge_from_criteria",
    "inaction_against_criteria",
    "objective_substitution",
    "mission_type_drift",
}:
    raise SystemExit("GoalDriftSignalKind root export drifted")

skill_root = resources.files("openminion_eval.skills").joinpath("resources")
if not skill_root.joinpath("skill_quality", "manifest.json").is_file():
    raise SystemExit("skill_quality manifest missing from installed wheel")
if not skill_root.joinpath("nl_named_skill", "manifest.json").is_file():
    raise SystemExit("nl_named_skill manifest missing from installed wheel")

catalog_count = 0
pending = [skill_root.joinpath("catalog")]
while pending:
    current = pending.pop()
    for child in current.iterdir():
        if child.is_dir():
            pending.append(child)
        elif child.name == "SKILL.md":
            catalog_count += 1
if catalog_count != 10:
    raise SystemExit(f"expected 10 packaged SKILL.md files, got {catalog_count}")

if len(load_skill_quality_manifest()[1]) != 10:
    raise SystemExit("skill quality manifest did not load packaged scenarios")
if len(load_nl_named_skill_manifest()[1]) != 10:
    raise SystemExit("NL named-skill manifest did not load packaged scenarios")

try:
    importlib.import_module("openminion_eval.memory_eval")
except ModuleNotFoundError as exc:
    if exc.name != "openminion_eval.memory_eval":
        raise
else:
    raise SystemExit("openminion_eval.memory_eval should not ship in the wheel")
"""


def main() -> int:
    _assert_package_docs_shape()
    _remove_build_residue()
    try:
        with tempfile.TemporaryDirectory(prefix="openminion-eval-release-") as tmp:
            tmp_root = Path(tmp)
            dist_dir = tmp_root / "dist"
            install_dir = tmp_root / "install"
            dist_dir.mkdir()
            install_dir.mkdir()

            _run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--sdist",
                    "--wheel",
                    "--outdir",
                    str(dist_dir),
                    str(REPO_ROOT),
                ],
                cwd=REPO_ROOT,
            )
            sdist = _single_artifact(dist_dir, ".tar.gz")
            wheel = _single_artifact(dist_dir, ".whl")

            _run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(install_dir),
                    str(wheel),
                ],
                cwd=tmp_root,
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = str(install_dir)
            env["OPENMINION_EVAL_RELEASE_TARGET"] = str(install_dir)
            _run([sys.executable, "-c", _smoke_script()], cwd=tmp_root, env=env)
            _run(
                [
                    sys.executable,
                    "-m",
                    "openminion_eval.cases",
                    "--category",
                    "coding",
                ],
                cwd=tmp_root,
                env=env,
            )

            print(f"release-check ok: {sdist.name}, {wheel.name}")
    finally:
        _remove_build_residue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
