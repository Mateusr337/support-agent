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

_case2_metrics: list[BaseMetric] = [
    ContextualRelevancyMetric(threshold=0.6, model=_judge),
    GEval(
        name="SsdSelfRepairFacts",
        criteria=(
            "The answer must explain that some parts are Customer Self-Repair "
            "while others require authorized service, that SSD replacement is "
            "documented under Customer Self-Repair, warn that wrong parts can "
            "damage the computer or void warranty, and mention high-level steps "
            "such as removing the bottom cover and disconnecting the battery."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=_judge,
    ),
]

_case4_metrics: list[BaseMetric] = [
    ContextualRelevancyMetric(threshold=0.6, model=_judge),
    GEval(
        name="MemoryUpgradeFacts",
        criteria=(
            "The answer must mention two SODIMM slots and dual-channel support, "
            "DDR5-5600 memory at 1.1 V, supported configs of 16 GB and 32 GB, "
            "and that memory is customer accessible or upgradeable."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
        model=_judge,
    ),
]

_case6_metrics: list[BaseMetric] = [
    ContextualRelevancyMetric(threshold=0.6, model=_judge),
    GEval(
        name="WifiResetFacts",
        criteria=(
            "The answer must describe holding the Wi-Fi button on the back for "
            "at least 3 seconds, restoring network settings to default, putting "
            "the printer in Auto Wireless Connect (AWC) setup mode, and using "
            "the HP Smart app to complete setup."
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
    2: _shared_metrics + _case2_metrics,
    4: _shared_metrics + _case4_metrics,
    6: _shared_metrics + _case6_metrics,
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
