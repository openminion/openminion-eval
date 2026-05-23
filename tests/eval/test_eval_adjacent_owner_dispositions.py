from tests.eval.provider_certification_matrix import (
    ADJACENT_EVAL_DISPOSITION as PCM_DISPOSITION,
)
from tests.eval.memory_quality_eval import (
    ADJACENT_EVAL_DISPOSITION as MQE_DISPOSITION,
)
from openminion_eval.skills import (
    CANONICAL_EVAL_FAMILY,
    NLNamedSkillScenario,
    SkillQualityScenario,
)


def test_skill_quality_eval_is_now_owned_by_canonical_skills_family() -> None:
    assert CANONICAL_EVAL_FAMILY == "skills"
    assert SkillQualityScenario.__module__ == "openminion_eval.skills.quality"


def test_nl_named_skill_eval_is_now_owned_by_canonical_skills_family() -> None:
    assert CANONICAL_EVAL_FAMILY == "skills"
    assert NLNamedSkillScenario.__module__ == "openminion_eval.skills.named_selection"


def test_provider_certification_matrix_disposition_is_cross_family_composite() -> None:
    assert PCM_DISPOSITION == "cross_family_composite_report"


def test_memory_quality_eval_disposition_is_memory_family_adjacent_report() -> None:
    assert MQE_DISPOSITION == "memory_family_adjacent_report"
