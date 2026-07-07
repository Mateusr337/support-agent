from dataclasses import dataclass

from app.rag.corpus import LAPTOP_MANUAL_FILENAME, PRINTER_MANUAL_FILENAME


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
        id=2,
        name="ssd_self_repair",
        input="Can I replace the SSD on my OMEN 17 laptop myself?",
        expected_output=(
            "Some parts are Customer Self-Repair; others require an authorized service provider. "
            "SSD replacement is documented under Customer Self-Repair. "
            "Wrong parts can damage the computer or void warranty. "
            "High-level steps: prepare for disassembly, remove bottom cover, "
            "disconnect battery cable, remove SSD."
        ),
        expected_source=LAPTOP_MANUAL_FILENAME,
    ),
    EvalCase(
        id=4,
        name="memory_upgrade",
        input="How much RAM can I install and what type does the OMEN laptop support?",
        expected_output=(
            "Two SODIMM slots, dual-channel. DDR5-5600, 1.1 V. "
            "Supported configs: 16 GB (8×2) and 32 GB (16×2). "
            "Memory is customer accessible and upgradeable. "
            "Handle module by edges only; use ESD-safe container."
        ),
        expected_source=LAPTOP_MANUAL_FILENAME,
    ),
    EvalCase(
        id=6,
        name="printer_wifi_reset",
        input="How do I reset Wi-Fi on my HP ENVY 6000 and put it in setup mode again?",
        expected_output=(
            "Press and hold the Wi-Fi button on the back for at least 3 seconds. "
            "Restores network settings to default and puts the printer in "
            "Auto Wireless Connect (AWC) setup mode. "
            "Use HP Smart app to complete setup."
        ),
        expected_source=PRINTER_MANUAL_FILENAME,
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
