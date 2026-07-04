import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

import httpx
from deepeval import evaluate
from deepeval.evaluate.configs import DisplayConfig

from eval.cleanup import delete_eval_user
from eval.dataset import EVAL_CASES, EvalCase
from eval.metrics import JUDGE_MODEL, case_quality_passed, get_metrics_for_case
from eval.runner import (
    EvalRunnerError,
    check_health,
    collect_case_data,
    register_and_login,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run DeepEval LLM quality benchmark against the live API.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output",
        default="eval_report.json",
        help="Path for the JSON report (default: eval_report.json)",
    )
    parser.add_argument(
        "--keep-eval-data",
        action="store_true",
        help="Do not delete the eval user from the database after the run",
    )
    return parser


def _metric_results(metrics_data: list[Any] | None) -> list[dict[str, Any]]:
    if not metrics_data:
        return []

    results = [
        {
            "name": metric.name,
            "score": metric.score,
            "passed": metric.success,
            "reason": metric.reason,
        }
        for metric in metrics_data
    ]
    return results


def _print_summary(case_reports: list[dict[str, Any]]) -> None:
    print("\nSummary")
    print("-" * 72)
    for report in case_reports:
        status = "PASS" if report["passed"] else "FAIL"
        print(
            f"[{status}] Case {report['id']} ({report['name']}) "
            f"- {report['completion_time_ms']} ms"
        )
        for metric in report["metrics"]:
            mark = "PASS" if metric["passed"] else "FAIL"
            score = metric["score"]
            score_text = f"{score:.2f}" if score is not None else "n/a"
            print(f"  - {metric['name']}: {score_text} [{mark}]")
    print("-" * 72)


def _run_case(
    client: httpx.Client,
    base_url: str,
    token: str,
    case: EvalCase,
) -> dict[str, Any]:
    print(f"Running case {case.id}: {case.name}...")
    test_case, retrieved_sources, timing = collect_case_data(
        client, base_url, token, case
    )
    metrics = get_metrics_for_case(case.id)
    evaluation = evaluate(
        test_cases=[test_case],
        metrics=metrics,
        display_config=DisplayConfig(
            show_indicator=False,
            print_results=False,
        ),
    )

    test_result = evaluation.test_results[0]
    metric_reports = _metric_results(test_result.metrics_data)
    passed = case_quality_passed(metric_reports)

    return {
        "id": case.id,
        "name": case.name,
        "passed": passed,
        "completion_time_ms": timing["completion_time_ms"],
        "latency": timing["latency"],
        "retrieved_sources": retrieved_sources,
        "expected_source": case.expected_source,
        "metrics": metric_reports,
        "answer_preview": test_case.actual_output[:300],
    }


def main() -> None:
    args = _build_parser().parse_args()
    base_url = args.base_url.rstrip("/")
    eval_email: str | None = None
    case_reports: list[dict[str, Any]] = []
    runner_error: EvalRunnerError | None = None

    try:
        with httpx.Client() as client:
            check_health(client, base_url)
            token, eval_email = register_and_login(client, base_url)

            for case in EVAL_CASES:
                case_reports.append(_run_case(client, base_url, token, case))

    except EvalRunnerError as exc:
        runner_error = exc
    finally:
        if eval_email and not args.keep_eval_data:
            try:
                if delete_eval_user(eval_email):
                    print(f"Cleaned up eval user: {eval_email}")
            except Exception as exc:
                print(
                    f"Warning: failed to delete eval user {eval_email}: {exc}",
                    file=sys.stderr,
                )

    if runner_error is not None:
        print(f"Error: {runner_error}", file=sys.stderr)
        sys.exit(1)

    passed_cases = sum(1 for report in case_reports if report["passed"])
    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "judge_model": JUDGE_MODEL,
        "total_cases": len(case_reports),
        "passed_cases": passed_cases,
        "cases": case_reports,
    }

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    _print_summary(case_reports)
    print(f"\nReport saved to {args.output}")
    print(f"Result: {passed_cases}/{len(case_reports)} cases passed")

    failed_reports = [report for report in case_reports if not report["passed"]]
    if failed_reports:
        print("Failed cases:")
        for report in failed_reports:
            failed_metrics = [
                metric["name"]
                for metric in report["metrics"]
                if not metric["passed"]
            ]
            metrics_text = ", ".join(failed_metrics) or "unknown"
            print(f"  - Case {report['id']} ({report['name']}): {metrics_text}")

    sys.exit(0 if passed_cases == len(case_reports) else 1)


if __name__ == "__main__":
    main()
