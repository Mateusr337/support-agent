from dataclasses import dataclass

from app.rag.corpus import LAPTOP_MANUAL_FILENAME


@dataclass(frozen=True)
class EvalCase:
    id: int
    name: str
    input: str
    expected_output: str
    expected_source: str | None


EVAL_CASES: list[EvalCase] = [
    EvalCase(
        id=1,
        name="laptop_safety",
        input="Can I use my OMEN laptop on my bed or lap for long gaming sessions?",
        expected_output=(
            "Do not place the laptop on your lap or block air vents. "
            "Use it on a hard, flat surface. Avoid soft surfaces like beds, "
            "pillows, rugs, or clothing that block airflow. "
            "The AC adapter should not contact skin or soft surfaces during operation."
        ),
        expected_source=LAPTOP_MANUAL_FILENAME,
    ),
    EvalCase(
        id=10,
        name="no_printhead_hallucination",
        input="How do I replace the printhead on my OMEN gaming laptop?",
        expected_output=(
            "Should NOT provide printhead replacement steps for a laptop. "
            "Should clarify that OMEN is a laptop service guide, not a printer, "
            "or state that no relevant documents were found."
        ),
        expected_source=None,
    ),
]
