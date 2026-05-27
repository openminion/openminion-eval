"""Interface contract tests for the eval module."""

import pytest
from openminion_eval.interfaces import (
    EVAL_INTERFACE_VERSION,
    EvalInterfaceError,
    ensure_eval_runner_compatibility,
    ensure_eval_scorer_compatibility,
    ensure_eval_suite_compatibility,
)
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer
from openminion_eval.suite import EvalSuite


class TestEvalRunnerContractVersion:
    def test_eval_runner_contract_version_declared(self):
        runner = EvalRunner()
        assert hasattr(runner, "contract_version")
        assert runner.contract_version == EVAL_INTERFACE_VERSION


class TestEvalScorerContractVersion:
    def test_eval_scorer_contract_version_declared(self):
        scorer = EvalScorer()
        assert hasattr(scorer, "contract_version")
        assert scorer.contract_version == EVAL_INTERFACE_VERSION


class TestEvalSuiteContractVersion:
    def test_eval_suite_contract_version_declared(self):
        suite = EvalSuite()
        assert hasattr(suite, "contract_version")
        assert suite.contract_version == EVAL_INTERFACE_VERSION


class TestEvalRunnerCompatibilityValidator:
    def test_eval_runner_valid_implementation_passes(self):
        runner = EvalRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_runner_missing_method_fails(self):
        class BrokenRunner:
            contract_version = EVAL_INTERFACE_VERSION

        runner = BrokenRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_runner_version_mismatch_fails(self):
        class WrongVersionRunner:
            contract_version = "v99"

        runner = WrongVersionRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_runner_strict_mode_raises_error(self):
        class BadRunner:
            contract_version = "v99"

        runner = BadRunner()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_runner_compatibility(runner, strict=True)
        assert excinfo.value.code == "EVAL_RUNNER_INTERFACE_VIOLATION"


class TestEvalScorerCompatibilityValidator:
    def test_eval_scorer_valid_implementation_passes(self):
        scorer = EvalScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_scorer_missing_method_fails(self):
        class BrokenScorer:
            contract_version = EVAL_INTERFACE_VERSION

        scorer = BrokenScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_scorer_version_mismatch_fails(self):
        class WrongVersionScorer:
            contract_version = "v99"

        scorer = WrongVersionScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_scorer_strict_mode_raises_error(self):
        class BadScorer:
            contract_version = "v99"

        scorer = BadScorer()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_scorer_compatibility(scorer, strict=True)
        assert excinfo.value.code == "EVAL_SCORER_INTERFACE_VIOLATION"


class TestEvalSuiteCompatibilityValidator:
    def test_eval_suite_valid_implementation_passes(self):
        suite = EvalSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_suite_missing_method_fails(self):
        class BrokenSuite:
            contract_version = EVAL_INTERFACE_VERSION

        suite = BrokenSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_suite_version_mismatch_fails(self):
        class WrongVersionSuite:
            contract_version = "v99"

        suite = WrongVersionSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_suite_strict_mode_raises_error(self):
        class BadSuite:
            contract_version = "v99"

        suite = BadSuite()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_suite_compatibility(suite, strict=True)
        assert excinfo.value.code == "EVAL_SUITE_INTERFACE_VIOLATION"
