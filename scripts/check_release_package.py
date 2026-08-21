"""Build and smoke-test the standalone openminion-eval package."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    expected_returncode: int = 0,
) -> None:
    result = subprocess.run(args, cwd=cwd, env=env, check=False)
    if result.returncode != expected_returncode:
        raise RuntimeError(
            f"expected return code {expected_returncode}, got {result.returncode}: "
            f"{args!r}"
        )


def _run_eval_cli(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    expected_returncode: int = 0,
) -> None:
    _run(
        [sys.executable, "-m", "openminion_eval", *args],
        cwd=cwd,
        env=env,
        expected_returncode=expected_returncode,
    )


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
        REPO_ROOT / "docs" / "artifact-workflows.md",
        REPO_ROOT / "docs" / "artifact-schemas.md",
        REPO_ROOT / "docs" / "certification-readiness-matrix.md",
        REPO_ROOT / "docs" / "eval-cases.md",
        REPO_ROOT / "docs" / "eval-families.md",
        REPO_ROOT / "docs" / "memory-effectiveness.md",
        REPO_ROOT / "docs" / "memory-context-scorecard.md",
        REPO_ROOT / "docs" / "ci-recipes.md",
        REPO_ROOT / "docs" / "artifacts-and-manual-grading.md",
        REPO_ROOT / "docs" / "standalone-claim-alignment.md",
        REPO_ROOT / "docs" / "source-tree-owner-map.md",
        REPO_ROOT / "docs" / "schemas" / "eval-dataset.v1.schema.json",
        REPO_ROOT / "docs" / "schemas" / "manual-review.v1.schema.json",
        REPO_ROOT / "docs" / "schemas" / "memory-scorecard.v1.schema.json",
        REPO_ROOT / "docs" / "schemas" / "red-team-security.v1.schema.json",
        REPO_ROOT / "docs" / "schemas" / "synthetic-golden.v1.schema.json",
        REPO_ROOT / "src" / "openminion_eval" / "README.md",
        REPO_ROOT / "API_COMPATIBILITY.md",
        REPO_ROOT / "RELEASING.md",
    ]
    missing = [
        str(path.relative_to(REPO_ROOT)) for path in required_paths if not path.exists()
    ]
    if missing:
        raise RuntimeError(f"package docs/layout drifted: missing {missing!r}")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    forbidden_fragments = [
        "https://pypi.org/project/openminion-eval/",
        "img.shields.io/pypi/",
        "pip install openminion-eval",
    ]
    leaked = [fragment for fragment in forbidden_fragments if fragment in readme]
    if leaked:
        raise RuntimeError(
            f"README advertises unpublished PyPI package surface: {leaked!r}"
        )


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
    BENCHMARK_ADAPTER_VERSION,
    EVAL_INTERFACE_VERSION,
    EvalCase,
    EvalRunContext,
    EvalRunManifest,
    EvalResult,
    EvalRunner,
    EvalScorer,
    EvalScorerInfo,
    EvalScorerSpec,
    EvalSubjectInterface,
    CliSubject,
    HttpSubject,
    ReplaySubject,
    EvalDatasetValidationError,
    BOUNDARY_ARTIFACT_VERSION,
    BoundaryArtifactValidationError,
    DELEGATED_MEMORY_DIFF_VERSION,
    DelegatedMemoryEvalTrace,
    EvalSuiteDiffArtifact,
    IntegrationProbeDisposition,
    RedTeamSecurityArtifact,
    SyntheticGoldenArtifact,
    GoalDriftSignalKind,
    GradeMode,
    MemoryEffectivenessCase,
    MemoryEffectivenessTrace,
    MemoryBenchmarkSource,
    MemoryExpectation,
    MEMORY_CONTEXT_SCORECARD_VERSION,
    MemoryContextScorecardV1,
    RuntimeReliabilityCase,
    RuntimeReliabilityObservation,
    SUITE_DIFF_VERSION,
    build_eval_dataset_template,
    build_delegated_memory_scorecard_diff,
    build_delegated_memory_scorecard,
    build_case_traces,
    build_integration_quarantine_map,
    build_suite_diff_artifact,
    build_memory_context_scorecard,
    build_memory_scorecard,
    build_runtime_reliability_report,
    build_run_manifest,
    build_manual_review_queue,
    default_memory_context_scorecard_cases_path,
    default_delegated_memory_cases_path,
    default_memory_benchmark_manifest_path,
    default_memory_effectiveness_cases_path,
    compare_suite_results,
    compare_delegated_memory_scorecards,
    hash_transcripts,
    load_packaged_memory_benchmark_sample,
    load_delegated_memory_cases,
    load_delegated_memory_scorecard_diff,
    load_delegated_memory_scorecard,
    load_suite_diff,
    load_replay_subject,
    load_memory_context_scorecard_fixtures,
    load_memory_effectiveness_cases,
    load_manual_results,
    load_manual_review_queue,
    load_eval_dataset_jsonl,
    load_red_team_security_artifact,
    load_synthetic_golden_artifact,
    list_builtin_families,
    parse_http_headers,
    render_suite_result_markdown,
    render_baseline_diff_markdown,
    render_memory_scorecard_markdown,
    render_delegated_memory_diff_markdown,
    render_delegated_memory_scorecard_markdown,
    render_memory_context_scorecard_markdown,
    render_suite_diff_artifact_markdown,
    registered_cases,
    score_memory_case,
    select_transcripts,
    write_eval_dataset_template,
    write_delegated_memory_scorecard_diff,
    write_delegated_memory_scorecard,
    write_suite_diff,
    write_red_team_security_artifact,
    write_manual_results,
    write_manual_review_queue,
    write_synthetic_golden_artifact,
)
from openminion_eval.schemas import EvalTranscript
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
if EvalScorer.__name__ != "EvalScorer":
    raise SystemExit("EvalScorer root export missing")
if EvalScorerSpec.__name__ != "EvalScorerSpec":
    raise SystemExit("EvalScorerSpec root export missing")
if EvalScorerInfo.__name__ != "EvalScorerInfo":
    raise SystemExit("EvalScorerInfo root export missing")
if not isinstance(openminion_eval.__version__, str) or not openminion_eval.__version__:
    raise SystemExit("__version__ root export missing")
if EvalRunContext.__name__ != "EvalRunContext":
    raise SystemExit("EvalRunContext root export missing")
if EvalSubjectInterface.__name__ != "EvalSubjectInterface":
    raise SystemExit("EvalSubjectInterface root export missing")
if CliSubject.__name__ != "CliSubject":
    raise SystemExit("CliSubject root export missing")
if HttpSubject.__name__ != "HttpSubject":
    raise SystemExit("HttpSubject root export missing")
if ReplaySubject.__name__ != "ReplaySubject":
    raise SystemExit("ReplaySubject root export missing")
if not callable(load_replay_subject):
    raise SystemExit("load_replay_subject root export missing")
if parse_http_headers(["X-Test=yes"])["X-Test"] != "yes":
    raise SystemExit("parse_http_headers root export drifted")
if EvalCase.__name__ != "EvalCase":
    raise SystemExit("EvalCase root export missing")
if EvalRunManifest.__name__ != "EvalRunManifest":
    raise SystemExit("EvalRunManifest root export missing")
if MemoryEffectivenessCase.__name__ != "MemoryEffectivenessCase":
    raise SystemExit("MemoryEffectivenessCase root export missing")
if MemoryEffectivenessTrace.__name__ != "MemoryEffectivenessTrace":
    raise SystemExit("MemoryEffectivenessTrace root export missing")
if MemoryBenchmarkSource.__name__ != "MemoryBenchmarkSource":
    raise SystemExit("MemoryBenchmarkSource root export missing")
if BENCHMARK_ADAPTER_VERSION != "1":
    raise SystemExit("benchmark adapter version drifted")
if not callable(build_run_manifest):
    raise SystemExit("build_run_manifest root export missing")
if not callable(load_memory_effectiveness_cases):
    raise SystemExit("load_memory_effectiveness_cases root export missing")
if not callable(default_memory_effectiveness_cases_path):
    raise SystemExit("default_memory_effectiveness_cases_path root export missing")
if not callable(load_packaged_memory_benchmark_sample):
    raise SystemExit("load_packaged_memory_benchmark_sample root export missing")
if not callable(default_memory_benchmark_manifest_path):
    raise SystemExit("default_memory_benchmark_manifest_path root export missing")
if not callable(score_memory_case):
    raise SystemExit("score_memory_case root export missing")
if not callable(build_memory_scorecard):
    raise SystemExit("build_memory_scorecard root export missing")
if not callable(build_delegated_memory_scorecard):
    raise SystemExit("build_delegated_memory_scorecard root export missing")
if not callable(build_delegated_memory_scorecard_diff):
    raise SystemExit("build_delegated_memory_scorecard_diff root export missing")
if not callable(compare_delegated_memory_scorecards):
    raise SystemExit("compare_delegated_memory_scorecards root export missing")
if DELEGATED_MEMORY_DIFF_VERSION != "delegated-memory-diff.v1":
    raise SystemExit("delegated memory diff version drifted")
if not callable(load_delegated_memory_scorecard):
    raise SystemExit("load_delegated_memory_scorecard root export missing")
if not callable(load_delegated_memory_scorecard_diff):
    raise SystemExit("load_delegated_memory_scorecard_diff root export missing")
if not callable(write_delegated_memory_scorecard):
    raise SystemExit("write_delegated_memory_scorecard root export missing")
if not callable(write_delegated_memory_scorecard_diff):
    raise SystemExit("write_delegated_memory_scorecard_diff root export missing")
if MEMORY_CONTEXT_SCORECARD_VERSION != "memory-context-scorecard.v1":
    raise SystemExit("memory context scorecard version drifted")
if MemoryContextScorecardV1.__name__ != "MemoryContextScorecardV1":
    raise SystemExit("MemoryContextScorecardV1 root export missing")
if not callable(build_memory_context_scorecard):
    raise SystemExit("build_memory_context_scorecard root export missing")
if not callable(build_runtime_reliability_report):
    raise SystemExit("build_runtime_reliability_report root export missing")
if not callable(load_memory_context_scorecard_fixtures):
    raise SystemExit("load_memory_context_scorecard_fixtures root export missing")
if not callable(default_memory_context_scorecard_cases_path):
    raise SystemExit("default_memory_context_scorecard_cases_path root export missing")
if not callable(build_case_traces):
    raise SystemExit("build_case_traces root export missing")
if not callable(compare_suite_results):
    raise SystemExit("compare_suite_results root export missing")
if not callable(build_suite_diff_artifact):
    raise SystemExit("build_suite_diff_artifact root export missing")
if SUITE_DIFF_VERSION != "suite-diff.v1":
    raise SystemExit("suite diff version drifted")
if EvalSuiteDiffArtifact.__name__ != "EvalSuiteDiffArtifact":
    raise SystemExit("EvalSuiteDiffArtifact root export missing")
if not callable(load_suite_diff):
    raise SystemExit("load_suite_diff root export missing")
if not callable(write_suite_diff):
    raise SystemExit("write_suite_diff root export missing")
if not callable(hash_transcripts):
    raise SystemExit("hash_transcripts root export missing")
if not callable(select_transcripts):
    raise SystemExit("select_transcripts root export missing")
if not callable(load_eval_dataset_jsonl):
    raise SystemExit("load_eval_dataset_jsonl root export missing")
if build_eval_dataset_template(family="routing")["name"] != "routing-starter":
    raise SystemExit("dataset template root export drifted")
if not callable(write_eval_dataset_template):
    raise SystemExit("write_eval_dataset_template root export missing")
if EvalDatasetValidationError.__name__ != "EvalDatasetValidationError":
    raise SystemExit("EvalDatasetValidationError root export missing")
if IntegrationProbeDisposition.__name__ != "IntegrationProbeDisposition":
    raise SystemExit("IntegrationProbeDisposition root export missing")
if not callable(build_integration_quarantine_map):
    raise SystemExit("build_integration_quarantine_map root export missing")
if not callable(render_suite_result_markdown):
    raise SystemExit("render_suite_result_markdown root export missing")
if not callable(render_baseline_diff_markdown):
    raise SystemExit("render_baseline_diff_markdown root export missing")
if not callable(render_suite_diff_artifact_markdown):
    raise SystemExit("render_suite_diff_artifact_markdown root export missing")
if not callable(render_memory_scorecard_markdown):
    raise SystemExit("render_memory_scorecard_markdown root export missing")
if not callable(render_delegated_memory_scorecard_markdown):
    raise SystemExit("render_delegated_memory_scorecard_markdown root export missing")
if not callable(render_delegated_memory_diff_markdown):
    raise SystemExit("render_delegated_memory_diff_markdown root export missing")
if not callable(render_memory_context_scorecard_markdown):
    raise SystemExit("render_memory_context_scorecard_markdown root export missing")
if BOUNDARY_ARTIFACT_VERSION != "1":
    raise SystemExit("boundary artifact version drifted")
if BoundaryArtifactValidationError.__name__ != "BoundaryArtifactValidationError":
    raise SystemExit("BoundaryArtifactValidationError root export missing")
if RedTeamSecurityArtifact.__name__ != "RedTeamSecurityArtifact":
    raise SystemExit("RedTeamSecurityArtifact root export missing")
if SyntheticGoldenArtifact.__name__ != "SyntheticGoldenArtifact":
    raise SystemExit("SyntheticGoldenArtifact root export missing")
if not callable(load_red_team_security_artifact):
    raise SystemExit("load_red_team_security_artifact root export missing")
if not callable(load_synthetic_golden_artifact):
    raise SystemExit("load_synthetic_golden_artifact root export missing")
if not callable(write_red_team_security_artifact):
    raise SystemExit("write_red_team_security_artifact root export missing")
if not callable(write_synthetic_golden_artifact):
    raise SystemExit("write_synthetic_golden_artifact root export missing")
if select_transcripts([EvalTranscript(name="smoke", turns=[], tags=["public"])], include_tags=["public"])[0].name != "smoke":
    raise SystemExit("select_transcripts root export drifted")
if GradeMode.STRUCTURAL.value != "structural":
    raise SystemExit("GradeMode root export drifted")
if len(registered_cases()) != 5:
    raise SystemExit("starter EvalCase registry drifted")
if grade_case(registered_cases()[0]).case_id != registered_cases()[0].case_id:
    raise SystemExit("EvalCase grading smoke failed")
if not list_builtin_families():
    raise SystemExit("built-in family registry is empty")
if build_manual_review_queue(tuple(registered_cases())).artifact_version != "1":
    raise SystemExit("manual review queue export drifted")
manual_tmp = Path(os.environ["OPENMINION_EVAL_RELEASE_TMP"])
manual_queue = build_manual_review_queue(tuple(registered_cases()))
manual_queue_path = manual_tmp / "manual-python-queue.json"
write_manual_review_queue(manual_queue_path, manual_queue)
if load_manual_review_queue(manual_queue_path) != manual_queue:
    raise SystemExit("manual review queue IO smoke failed")
manual_results = tuple(grade_case(case) for case in registered_cases())
manual_results_path = manual_tmp / "manual-python-results.json"
write_manual_results(manual_results_path, manual_results)
if load_manual_results(manual_results_path) != manual_results:
    raise SystemExit("manual results IO smoke failed")
runtime_report = build_runtime_reliability_report(
    cases=(
        RuntimeReliabilityCase(
            case_id="runtime-smoke",
            capability="dependency_readiness",
            expected_facts={"ready": True},
            required_identifiers=("dependency_id",),
        ),
    ),
    observations={
        "runtime-smoke": RuntimeReliabilityObservation(
            facts={"ready": True},
            identifiers={"dependency_id": "dep-1"},
        )
    },
    now_provider=lambda: "1970-01-01T00:00:00Z",
)
if runtime_report.summary.failed_count:
    raise SystemExit("runtime reliability scoring smoke failed")
threshold_result = EvalScorer().score(
    EvalResult(
        turn_index=0,
        user_input="question",
        expected="answer",
        actual="answer",
        score=0.0,
        scorer_name="pending",
    ),
    scorer_name="exact_match",
    threshold=0.8,
)
if threshold_result.scorer_reason != "passed" or threshold_result.scorer_threshold != 0.8:
    raise SystemExit("threshold-aware scorer metadata drifted")
if {item.name for item in EvalScorer().list_scorers()} != {"exact_match", "substring_match"}:
    raise SystemExit("scorer registry metadata drifted")

dist_files = {str(path) for path in distribution("openminion-eval").files or ()}
if "openminion_eval/py.typed" not in dist_files:
    raise SystemExit("py.typed missing from installed wheel")
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

memory_cases = load_memory_effectiveness_cases()
if len(memory_cases) != 16:
    raise SystemExit("memory effectiveness fixture count drifted")
delegated_cases = load_delegated_memory_cases()
if len(delegated_cases) != 8 or not default_delegated_memory_cases_path().is_file():
    raise SystemExit("delegated memory packaged fixture drifted")
delegated_scorecard = build_delegated_memory_scorecard(
    delegated_cases,
    tuple(
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            retrieved_memory_ids=case.required_recall_ids,
        )
        for case in delegated_cases
    ),
)
if not delegated_scorecard.passed:
    raise SystemExit("delegated memory scoring smoke failed")
if not compare_delegated_memory_scorecards(delegated_scorecard, delegated_scorecard):
    raise SystemExit("delegated memory scorecard diff smoke failed")
delegated_diff = build_delegated_memory_scorecard_diff(
    delegated_scorecard,
    delegated_scorecard,
)
delegated_diff_path = (
    Path(os.environ["OPENMINION_EVAL_RELEASE_TMP"])
    / "delegated-memory-python-diff.json"
)
write_delegated_memory_scorecard_diff(delegated_diff_path, delegated_diff)
if load_delegated_memory_scorecard_diff(delegated_diff_path) != delegated_diff:
    raise SystemExit("delegated memory diff IO smoke failed")
if "Delegated-Memory Diff" not in render_delegated_memory_diff_markdown(
    delegated_diff
):
    raise SystemExit("delegated memory diff report renderer smoke failed")
suite_diff = openminion_eval.build_suite_diff_artifact(
    openminion_eval.EvalSuiteResult(
        suite_name="previous",
        total_transcripts=1,
        passed_transcripts=0,
        failed_transcripts=1,
        summaries=[
            openminion_eval.EvalSummary(
                transcript_name="fixed",
                total_turns=1,
                average_score=0.0,
                min_score=0.0,
                max_score=0.0,
                results=[],
                passed=False,
            )
        ],
        all_passed=False,
    ),
    openminion_eval.EvalSuiteResult(
        suite_name="current",
        total_transcripts=1,
        passed_transcripts=1,
        failed_transcripts=0,
        summaries=[
            openminion_eval.EvalSummary(
                transcript_name="fixed",
                total_turns=1,
                average_score=1.0,
                min_score=1.0,
                max_score=1.0,
                results=[],
                passed=True,
            )
        ],
        all_passed=True,
    ),
)
suite_diff_path = (
    Path(os.environ["OPENMINION_EVAL_RELEASE_TMP"]) / "suite-diff-python.json"
)
write_suite_diff(suite_diff_path, suite_diff)
if load_suite_diff(suite_diff_path) != suite_diff:
    raise SystemExit("suite diff IO smoke failed")
if "Eval Suite Diff" not in render_suite_diff_artifact_markdown(suite_diff):
    raise SystemExit("suite diff report renderer smoke failed")
delegated_scorecard_path = (
    Path(os.environ["OPENMINION_EVAL_RELEASE_TMP"])
    / "delegated-memory-python-scorecard.json"
)
write_delegated_memory_scorecard(delegated_scorecard_path, delegated_scorecard)
if load_delegated_memory_scorecard(delegated_scorecard_path) != delegated_scorecard:
    raise SystemExit("delegated memory scorecard IO smoke failed")
if "Delegated-Memory Scorecard" not in render_delegated_memory_scorecard_markdown(
    delegated_scorecard
):
    raise SystemExit("delegated memory report renderer smoke failed")
scorecard_fixtures = load_memory_context_scorecard_fixtures()
if len(scorecard_fixtures) != 6:
    raise SystemExit("memory context scorecard fixture count drifted")
if not default_memory_context_scorecard_cases_path().is_file():
    raise SystemExit("memory context scorecard packaged fixture missing")
scorecard = build_memory_context_scorecard(
    scorecard_fixtures,
    run_id="smoke",
    generated_at="1970-01-01T00:00:00Z",
)
if (
    scorecard.report_version != "memory-context-scorecard.v1"
    or scorecard.summary["blocking_fail_count"] != 11
):
    raise SystemExit("memory context scorecard smoke failed")
if "Memory/Context Scorecard" not in render_memory_context_scorecard_markdown(
    scorecard
):
    raise SystemExit("memory context scorecard report renderer smoke failed")
if not default_memory_effectiveness_cases_path().is_file():
    raise SystemExit("memory effectiveness packaged fixture missing")
if not default_memory_benchmark_manifest_path("beam").is_file():
    raise SystemExit("benchmark adapter packaged sample missing")
benchmark_sample = load_packaged_memory_benchmark_sample("locomo")
if benchmark_sample.source.benchmark_family != "locomo" or not benchmark_sample.cases:
    raise SystemExit("benchmark adapter packaged sample failed to load")
memory_case = MemoryEffectivenessCase(
    case_id="memory-smoke",
    family="repo_convention",
    prompt="Which command should run?",
    expectations=MemoryExpectation(required_saved_ids=("mem-check",)),
)
memory_result = score_memory_case(
    memory_case,
    MemoryEffectivenessTrace(
        case_id="memory-smoke",
        run_id="smoke",
        memory_mode="enabled",
        saved_memory_ids=("mem-check",),
    ),
)
if build_memory_scorecard(
    suite_id="memory",
    run_id="smoke",
    case_results=(memory_result,),
).overall_score <= 0:
    raise SystemExit("memory effectiveness scoring smoke failed")
memory_smoke_scorecard = build_memory_scorecard(
    suite_id="memory",
    run_id="smoke-render",
    case_results=(memory_result,),
)
if "Memory-Effectiveness Scorecard" not in render_memory_scorecard_markdown(
    memory_smoke_scorecard
):
    raise SystemExit("memory effectiveness report renderer smoke failed")

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
            env["OPENMINION_EVAL_RELEASE_TMP"] = str(tmp_root)
            _run([sys.executable, "-c", _smoke_script()], cwd=tmp_root, env=env)
            _run_eval_cli(["--help"], cwd=tmp_root, env=env)
            _run(
                [
                    str(install_dir / "bin" / "openminion-eval"),
                    "--help",
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(["families", "list"], cwd=tmp_root, env=env)
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
            previous_suite_dataset_path = tmp_root / "previous-suite-dataset.json"
            current_suite_dataset_path = tmp_root / "current-suite-dataset.json"
            previous_suite_path = tmp_root / "previous-suite.json"
            current_suite_path = tmp_root / "current-suite.json"
            suite_diff_path = tmp_root / "suite-diff.json"
            suite_diff_report_path = tmp_root / "suite-diff.md"
            artifact_index_path = tmp_root / "artifact-index.html"
            previous_suite_dataset_path.write_text(
                json.dumps(
                    {
                        "dataset_version": "1",
                        "name": "previous-suite",
                        "cases": [
                            {
                                "id": "fixed",
                                "turns": [
                                    {
                                        "user": "hello",
                                        "expected": "not present",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            current_suite_dataset_path.write_text(
                json.dumps(
                    {
                        "dataset_version": "1",
                        "name": "current-suite",
                        "cases": [
                            {
                                "id": "fixed",
                                "turns": [
                                    {
                                        "user": "hello",
                                        "expected": "Mock response",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            _run_eval_cli(
                [
                    "run",
                    str(previous_suite_dataset_path),
                    "--out",
                    str(previous_suite_path),
                ],
                cwd=tmp_root,
                env=env,
                expected_returncode=1,
            )
            _run_eval_cli(
                [
                    "run",
                    str(current_suite_dataset_path),
                    "--out",
                    str(current_suite_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "diff",
                    str(previous_suite_path),
                    str(current_suite_path),
                    "--out",
                    str(suite_diff_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not suite_diff_path.is_file():
                raise RuntimeError("suite-diff CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "inspect",
                    str(suite_diff_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "report",
                    "suite-diff",
                    str(suite_diff_path),
                    "--out",
                    str(suite_diff_report_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not suite_diff_report_path.is_file():
                raise RuntimeError("suite-diff report CLI artifact missing")
            _run_eval_cli(
                [
                    "report",
                    "bundle",
                    str(current_suite_path),
                    str(suite_diff_path),
                    "--out",
                    str(artifact_index_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not artifact_index_path.is_file():
                raise RuntimeError("artifact bundle CLI index missing")
            bundle_files = tmp_root / "artifact-index-files"
            if not (bundle_files / "01-current-suite.json").is_file():
                raise RuntimeError("artifact bundle copied JSON missing")
            if not (bundle_files / "01-current-suite.html").is_file():
                raise RuntimeError("artifact bundle rendered report missing")

            manual_queue_path = tmp_root / "manual-review-queue.json"
            manual_adjudications_path = tmp_root / "manual-adjudications.json"
            manual_results_path = tmp_root / "manual-results.json"
            manual_adjudications_path.write_text(
                json.dumps(
                    {
                        "artifact_kind": "manual-adjudications",
                        "artifact_version": "1",
                        "adjudications": [
                            {
                                "case_id": "coding_minimax_markdown_table",
                                "outcome": "pass",
                                "detail": "release smoke review",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            _run_eval_cli(
                [
                    "manual",
                    "queue",
                    "--out",
                    str(manual_queue_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not manual_queue_path.is_file():
                raise RuntimeError("manual queue CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(manual_queue_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "manual",
                    "apply",
                    str(manual_adjudications_path),
                    "--out",
                    str(manual_results_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not manual_results_path.is_file():
                raise RuntimeError("manual apply CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(manual_results_path),
                ],
                cwd=tmp_root,
                env=env,
            )

            scorecard_path = tmp_root / "memory-context-scorecard.json"
            scorecard_report_path = tmp_root / "memory-context-scorecard.md"
            _run_eval_cli(
                [
                    "memory-context-scorecard",
                    "--run-id",
                    "release-smoke",
                    "--out",
                    str(scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
                expected_returncode=1,
            )
            if not scorecard_path.is_file():
                raise RuntimeError("memory-context-scorecard CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "report",
                    "memory-context",
                    str(scorecard_path),
                    "--out",
                    str(scorecard_report_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not scorecard_report_path.is_file():
                raise RuntimeError("memory-context report CLI artifact missing")

            memory_cases_path = tmp_root / "memory-effectiveness-cases.json"
            memory_trace_path = tmp_root / "memory-effectiveness-trace.json"
            memory_scorecard_path = tmp_root / "memory-effectiveness-scorecard.json"
            memory_report_path = tmp_root / "memory-effectiveness-scorecard.md"
            memory_cases_path.write_text(
                json.dumps(
                    {
                        "version": "1",
                        "cases": [
                            {
                                "case_id": "release-memory-smoke",
                                "family": "repo_convention",
                                "prompt": "Which release check should run?",
                                "tags": ["positive", "negative"],
                                "expectations": {
                                    "required_saved_ids": ["mem-release-check"],
                                    "required_retrieved_ids": ["mem-release-check"],
                                    "required_used_ids": ["mem-release-check"],
                                    "required_claim_memory_ids": ["mem-release-check"],
                                    "required_tool_memory_ids": ["mem-release-check"],
                                    "critical": True,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            memory_trace_path.write_text(
                json.dumps(
                    {
                        "traces": [
                            {
                                "case_id": "release-memory-smoke",
                                "run_id": "release-smoke",
                                "memory_mode": "enabled",
                                "saved_memory_ids": ["mem-release-check"],
                                "retrieved_memory_ids": ["mem-release-check"],
                                "used_memory_ids": ["mem-release-check"],
                                "supporting_claims": [
                                    {
                                        "claim": "Run make release-check before publishing.",
                                        "memory_id": "mem-release-check",
                                    }
                                ],
                                "tool_calls": [
                                    {
                                        "tool": "shell",
                                        "arguments_ref": "sha256:release-check",
                                        "memory_ids": ["mem-release-check"],
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            _run_eval_cli(
                [
                    "memory-effectiveness",
                    "score",
                    str(memory_trace_path),
                    "--cases",
                    str(memory_cases_path),
                    "--out",
                    str(memory_scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not memory_scorecard_path.is_file():
                raise RuntimeError("memory-effectiveness CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(memory_scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "report",
                    "memory-scorecard",
                    str(memory_scorecard_path),
                    "--out",
                    str(memory_report_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not memory_report_path.is_file():
                raise RuntimeError("memory-effectiveness report CLI artifact missing")

            benchmark_manifest_path = (
                install_dir
                / "openminion_eval"
                / "memory_effectiveness"
                / "resources"
                / "benchmark_locomo_sample.json"
            )
            benchmark_trace_path = tmp_root / "benchmark-memory-trace.json"
            benchmark_scorecard_path = tmp_root / "benchmark-memory-scorecard.json"
            benchmark_trace_path.write_text(
                json.dumps(
                    {
                        "traces": [
                            {
                                "case_id": "locomo-sample-temporal-001",
                                "run_id": "release-benchmark-smoke",
                                "memory_mode": "enabled",
                                "saved_memory_ids": ["locomo-mira-current-city"],
                                "retrieved_memory_ids": ["locomo-mira-current-city"],
                                "used_memory_ids": ["locomo-mira-current-city"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            _run_eval_cli(
                [
                    "memory-effectiveness",
                    "score",
                    str(benchmark_trace_path),
                    "--benchmark",
                    str(benchmark_manifest_path),
                    "--out",
                    str(benchmark_scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not benchmark_scorecard_path.is_file():
                raise RuntimeError("benchmark score CLI artifact missing")

            delegated_cases_payload = json.loads(
                (
                    REPO_ROOT
                    / "src"
                    / "openminion_eval"
                    / "memory_effectiveness"
                    / "resources"
                    / "delegated_multi_agent_memory_cases.json"
                ).read_text(encoding="utf-8")
            )
            delegated_trace_path = tmp_root / "delegated-memory-trace.json"
            delegated_scorecard_path = tmp_root / "delegated-memory-scorecard.json"
            delegated_report_path = tmp_root / "delegated-memory-scorecard.md"
            delegated_diff_path = tmp_root / "delegated-memory-diff.json"
            delegated_diff_report_path = tmp_root / "delegated-memory-diff.md"
            delegated_trace_path.write_text(
                json.dumps(
                    {
                        "traces": [
                            {
                                "case_id": case["case_id"],
                                "retrieved_memory_ids": case.get(
                                    "required_recall_ids",
                                    [],
                                ),
                            }
                            for case in delegated_cases_payload["cases"]
                        ]
                    }
                ),
                encoding="utf-8",
            )
            _run_eval_cli(
                [
                    "memory-effectiveness",
                    "delegated-score",
                    str(delegated_trace_path),
                    "--out",
                    str(delegated_scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not delegated_scorecard_path.is_file():
                raise RuntimeError("delegated-memory CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(delegated_scorecard_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "report",
                    "delegated-memory",
                    str(delegated_scorecard_path),
                    "--out",
                    str(delegated_report_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not delegated_report_path.is_file():
                raise RuntimeError("delegated-memory report CLI artifact missing")
            _run_eval_cli(
                [
                    "memory-effectiveness",
                    "delegated-diff",
                    str(delegated_scorecard_path),
                    str(delegated_scorecard_path),
                    "--out",
                    str(delegated_diff_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not delegated_diff_path.is_file():
                raise RuntimeError("delegated-memory diff CLI artifact missing")
            _run_eval_cli(
                [
                    "artifact",
                    "validate",
                    str(delegated_diff_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            _run_eval_cli(
                [
                    "report",
                    "delegated-diff",
                    str(delegated_diff_path),
                    "--out",
                    str(delegated_diff_report_path),
                ],
                cwd=tmp_root,
                env=env,
            )
            if not delegated_diff_report_path.is_file():
                raise RuntimeError("delegated-memory diff report CLI artifact missing")

            print(f"release-check ok: {sdist.name}, {wheel.name}")
    finally:
        _remove_build_residue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
