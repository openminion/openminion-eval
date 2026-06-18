from openminion_eval import (
    AggregateReport,
    ClosureCase,
    EvalCase,
    EvalCaseResult,
    FamilyCertificationSignal,
    FreshnessCase,
    GoalDriftSignalKind,
    GoalTrajectoryBenchmark,
    GradeMode,
    GradeOutcome,
    NLNamedSkillScenario,
    PolicyCase,
    RoutingCase,
    SkillQualityScenario,
    ToolResultUsageCase,
    ToolSelectionCase,
)


def test_root_eval_exports_new_family_types() -> None:
    assert ToolSelectionCase.__name__ == "ToolSelectionCase"
    assert EvalCase.__name__ == "EvalCase"
    assert EvalCaseResult.__name__ == "EvalCaseResult"
    assert GradeMode.STRUCTURAL.value == "structural"
    assert GradeOutcome.PASS.value == "pass"
    assert ToolResultUsageCase.__name__ == "ToolResultUsageCase"
    assert FreshnessCase.__name__ == "FreshnessCase"
    assert RoutingCase.__name__ == "RoutingCase"
    assert ClosureCase.__name__ == "ClosureCase"
    assert PolicyCase.__name__ == "PolicyCase"
    assert SkillQualityScenario.__name__ == "SkillQualityScenario"
    assert NLNamedSkillScenario.__name__ == "NLNamedSkillScenario"
    assert FamilyCertificationSignal.__name__ == "FamilyCertificationSignal"
    assert GoalDriftSignalKind.__args__ == (
        "actions_diverge_from_criteria",
        "inaction_against_criteria",
        "objective_substitution",
        "mission_type_drift",
    )
    assert GoalTrajectoryBenchmark.__name__ == "GoalTrajectoryBenchmark"
    assert AggregateReport.__name__ == "AggregateReport"
