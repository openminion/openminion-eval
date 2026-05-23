from openminion_eval import (
    ClosureCase,
    FamilyCertificationSignal,
    FreshnessCase,
    NLNamedSkillScenario,
    PolicyCase,
    RoutingCase,
    SkillQualityScenario,
    ToolResultUsageCase,
    ToolSelectionCase,
)


def test_root_eval_exports_new_family_types() -> None:
    assert ToolSelectionCase.__name__ == "ToolSelectionCase"
    assert ToolResultUsageCase.__name__ == "ToolResultUsageCase"
    assert FreshnessCase.__name__ == "FreshnessCase"
    assert RoutingCase.__name__ == "RoutingCase"
    assert ClosureCase.__name__ == "ClosureCase"
    assert PolicyCase.__name__ == "PolicyCase"
    assert SkillQualityScenario.__name__ == "SkillQualityScenario"
    assert NLNamedSkillScenario.__name__ == "NLNamedSkillScenario"
    assert FamilyCertificationSignal.__name__ == "FamilyCertificationSignal"
