from deepeval.metrics import (
    AnswerRelevancyMetric,
    BaseMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
)
from deepeval.models import GPTModel
from deepeval.test_case import LLMTestCaseParams

JUDGE_MODEL = "gpt-4o"

_judge = GPTModel(model=JUDGE_MODEL)

_shared_metrics: list[BaseMetric] = [
    AnswerRelevancyMetric(threshold=0.7, model=_judge),
    FaithfulnessMetric(threshold=0.7, model=_judge),
]

_case1_metrics: list[BaseMetric] = [
    ContextualRelevancyMetric(threshold=0.6, model=_judge),
    GEval(
        name="SafetyFacts",
        criteria=(
            "The answer must warn against using the laptop on lap or bed, "
            "mention blocking air vents, recommend a hard flat surface, "
            "and warn about soft surfaces blocking airflow."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=_judge,
    ),
]

_case10_metrics: list[BaseMetric] = [
    HallucinationMetric(threshold=0.7, model=_judge),
    GEval(
        name="NoPrintheadHallucination",
        criteria=(
            "The answer must NOT provide step-by-step printhead replacement "
            "instructions for a laptop. It should clarify that OMEN is a laptop "
            "(not a printer) or state that no relevant documents were found."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=_judge,
    ),
]

_METRICS_BY_CASE: dict[int, list[BaseMetric]] = {
    1: _shared_metrics + _case1_metrics,
    10: _shared_metrics + _case10_metrics,
}


def get_metrics_for_case(case_id: int) -> list[BaseMetric]:
    try:
        return _METRICS_BY_CASE[case_id]
    except KeyError as exc:
        raise ValueError(f"No metrics configured for case id {case_id}") from exc


def case_quality_passed(metric_reports: list[dict[str, object]]) -> bool:
    """Pass when every configured metric passes."""
    if not metric_reports:
        return False
    return all(bool(metric["passed"]) for metric in metric_reports)
