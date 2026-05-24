"""Interface contract tests for eval module with positive and negative path validation."""

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
    """Test contract version for eval runner is declared and correct."""

    def test_eval_runner_contract_version_declared(self):
        """Verify EvalRunner declares interface version."""
        runner = EvalRunner()
        assert hasattr(runner, "contract_version")
        assert runner.contract_version == EVAL_INTERFACE_VERSION


class TestEvalScorerContractVersion:
    """Test contract version for eval scorer is declared and correct."""

    def test_eval_scorer_contract_version_declared(self):
        """Verify EvalScorer declares interface version."""
        scorer = EvalScorer()
        assert hasattr(scorer, "contract_version")
        assert scorer.contract_version == EVAL_INTERFACE_VERSION


class TestEvalSuiteContractVersion:
    """Test contract version for eval suite is declared and correct."""

    def test_eval_suite_contract_version_declared(self):
        """Verify EvalSuite declares interface version."""
        suite = EvalSuite()
        assert hasattr(suite, "contract_version")
        assert suite.contract_version == EVAL_INTERFACE_VERSION


class TestEvalRunnerCompatibilityValidator:
    """Test eval runner compatibility validator catches drift."""

    def test_eval_runner_valid_implementation_passes(self):
        """Test that valid runner implementation passes compatibility check."""
        runner = EvalRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_runner_missing_method_fails(self):
        """Test that missing method causes validation to fail."""

        class BrokenRunner:
            contract_version = EVAL_INTERFACE_VERSION
            # Missing required methods like replay, replay_sync

        runner = BrokenRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_runner_version_mismatch_fails(self):
        """Test that wrong version causes validation error."""

        class WrongVersionRunner:
            contract_version = "v99"  # Wrong version

        runner = WrongVersionRunner()
        success, errors = ensure_eval_runner_compatibility(runner, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_runner_strict_mode_raises_error(self):
        """Test that strict mode raises exception on validation failure."""

        class BadRunner:
            contract_version = "v99"  # Wrong version

        runner = BadRunner()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_runner_compatibility(runner, strict=True)
        assert excinfo.value.code == "EVAL_RUNNER_INTERFACE_VIOLATION"


class TestEvalScorerCompatibilityValidator:
    """Test eval scorer compatibility validator catches drift."""

    def test_eval_scorer_valid_implementation_passes(self):
        """Test that valid scorer implementation passes compatibility check."""
        scorer = EvalScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_scorer_missing_method_fails(self):
        """Test that missing method causes validation to fail."""

        class BrokenScorer:
            contract_version = EVAL_INTERFACE_VERSION
            # Missing required methods like score, score_results, register_scorer

        scorer = BrokenScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_scorer_version_mismatch_fails(self):
        """Test that wrong version causes validation error."""

        class WrongVersionScorer:
            contract_version = "v99"  # Wrong version

        scorer = WrongVersionScorer()
        success, errors = ensure_eval_scorer_compatibility(scorer, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_scorer_strict_mode_raises_error(self):
        """Test that strict mode raises exception on validation failure."""

        class BadScorer:
            contract_version = "v99"  # Wrong version

        scorer = BadScorer()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_scorer_compatibility(scorer, strict=True)
        assert excinfo.value.code == "EVAL_SCORER_INTERFACE_VIOLATION"


class TestEvalSuiteCompatibilityValidator:
    """Test eval suite compatibility validator catches drift."""

    def test_eval_suite_valid_implementation_passes(self):
        """Test that valid suite implementation passes compatibility check."""
        suite = EvalSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is True
        assert len(errors) == 0

    def test_eval_suite_missing_method_fails(self):
        """Test that missing method causes validation to fail."""

        class BrokenSuite:
            contract_version = EVAL_INTERFACE_VERSION
            # Missing required methods like run, run_single

        suite = BrokenSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is False
        assert len(errors) > 0
        assert any("Missing required method" in error for error in errors)

    def test_eval_suite_version_mismatch_fails(self):
        """Test that wrong version causes validation error."""

        class WrongVersionSuite:
            contract_version = "v99"  # Wrong version

        suite = WrongVersionSuite()
        success, errors = ensure_eval_suite_compatibility(suite, strict=False)
        assert success is False
        assert len(errors) > 0
        assert "Version mismatch" in str(errors[0])

    def test_eval_suite_strict_mode_raises_error(self):
        """Test that strict mode raises exception on validation failure."""

        class BadSuite:
            contract_version = "v99"  # Wrong version

        suite = BadSuite()
        with pytest.raises(EvalInterfaceError) as excinfo:
            ensure_eval_suite_compatibility(suite, strict=True)
        assert excinfo.value.code == "EVAL_SUITE_INTERFACE_VIOLATION"
