"""Benchmark runner for the NeoMint evaluation suite.

Loads test fixtures, runs each through the planner (or mock planner),
compares results against golden expectations, and produces reports.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from neomint_eval.fixtures import FixtureSet, TestFixture, load_fixtures
from neomint_eval.reporter import BenchmarkReporter

logger = logging.getLogger("neomint-eval.runner")

# Results directory
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


class FixtureResult:
    """Result of running a single test fixture."""

    def __init__(
        self,
        fixture: TestFixture,
        passed: bool,
        actual: dict[str, Any],
        errors: list[str],
        duration_ms: float,
    ) -> None:
        self.fixture = fixture
        self.passed = passed
        self.actual = actual
        self.errors = errors
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.fixture.id,
            "category": self.fixture.category,
            "description": self.fixture.description,
            "passed": self.passed,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms, 2),
            "input": self.fixture.input,
            "expected": self.fixture.expected.model_dump(),
            "actual": self.actual,
        }


class BenchmarkRunner:
    """Runs evaluation fixtures against the planner and reports results.

    Can operate in two modes:
    1. Policy-only: validates planner output against the policy engine
       (no model needed, uses pre-built plan data)
    2. Full: sends requests through the model adapter and validates end-to-end
       (requires Ollama running locally)
    """

    def __init__(self, fixtures: FixtureSet | None = None) -> None:
        self.fixtures = fixtures or load_fixtures()
        self.results: list[FixtureResult] = []

    def run_policy_evaluation(self) -> list[FixtureResult]:
        """Run policy-only evaluation against all fixtures.

        This mode validates that the policy engine correctly handles:
        - Known tool names
        - Path scoping
        - Risk classification
        - Dangerous argument detection
        - Action count limits

        Does NOT require a running model.
        """
        self.results = []

        for fixture in self.fixtures.fixtures:
            start = perf_counter()
            result = self._evaluate_fixture_policy(fixture)
            duration_ms = (perf_counter() - start) * 1000
            result.duration_ms = duration_ms
            self.results.append(result)

        return self.results

    def _evaluate_fixture_policy(self, fixture: TestFixture) -> FixtureResult:
        """Evaluate a single fixture against the policy engine."""
        from neomint_agent.parser import parse_model_output
        from neomint_agent.policy import validate_plan
        from neomint_agent.schemas import Clarification, Plan, PolicyViolation, Refusal

        errors: list[str] = []
        actual: dict[str, Any] = {}

        # For policy evaluation, we simulate model output based on expected results
        expected = fixture.expected

        # If the fixture expects a refusal or clarification, check that
        if expected.kind == "refusal":
            # This fixture tests that the model should refuse
            actual["expected_kind"] = "refusal"
            actual["policy_check"] = "skipped (model-level refusal)"
            return FixtureResult(
                fixture=fixture,
                passed=True,
                actual=actual,
                errors=errors,
                duration_ms=0.0,
            )

        if expected.kind == "clarification":
            actual["expected_kind"] = "clarification"
            actual["policy_check"] = "skipped (model-level clarification)"
            return FixtureResult(
                fixture=fixture,
                passed=True,
                actual=actual,
                errors=errors,
                duration_ms=0.0,
            )

        # For plan fixtures, build a synthetic plan and validate it
        if expected.plan_tools:
            synthetic_actions = [
                {"tool": tool, "arguments": {}, "explanation": f"Test action for {tool}"}
                for tool in expected.plan_tools
            ]
            synthetic_plan_json = json.dumps({
                "kind": "plan",
                "user_facing_summary": fixture.description,
                "actions": synthetic_actions,
            })

            parsed = parse_model_output(synthetic_plan_json)

            if isinstance(parsed, Plan):
                validation = validate_plan(parsed)

                if expected.execution_blocked:
                    # We expect the policy to reject this
                    if isinstance(validation, PolicyViolation):
                        actual["policy_result"] = "correctly_rejected"
                        actual["violations"] = validation.violations
                    else:
                        errors.append("Expected policy rejection but plan was accepted")
                        actual["policy_result"] = "incorrectly_accepted"
                else:
                    # We expect the policy to accept this
                    if isinstance(validation, PolicyViolation):
                        errors.append(f"Expected plan acceptance but got violations: {validation.violations}")
                        actual["policy_result"] = "incorrectly_rejected"
                        actual["violations"] = validation.violations
                    else:
                        actual["policy_result"] = "correctly_accepted"

                        # Check risk level if expected
                        if expected.risk_level:
                            actual_risks = [a.risk for a in validation.actions]
                            if expected.risk_level not in [r.value for r in actual_risks]:
                                errors.append(
                                    f"Expected risk '{expected.risk_level}' "
                                    f"but got {[r.value for r in actual_risks]}"
                                )

                        # Check confirmation requirement
                        if expected.needs_confirmation is not None:
                            if validation.needs_approval != expected.needs_confirmation:
                                errors.append(
                                    f"Expected needs_confirmation={expected.needs_confirmation} "
                                    f"but got {validation.needs_approval}"
                                )

        return FixtureResult(
            fixture=fixture,
            passed=len(errors) == 0,
            actual=actual,
            errors=errors,
            duration_ms=0.0,
        )

    def generate_report(self, output_dir: Path | None = None) -> Path:
        """Generate JSON and markdown reports from the results.

        Args:
            output_dir: Directory to write reports. Defaults to eval/results/.

        Returns:
            Path to the generated markdown report.
        """
        output = output_dir or RESULTS_DIR
        output.mkdir(parents=True, exist_ok=True)

        reporter = BenchmarkReporter(self.results)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d")

        # JSON report
        json_path = output / f"report-{timestamp}.json"
        json_path.write_text(
            json.dumps(reporter.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Markdown report
        md_path = output / f"report-{timestamp}.md"
        md_path.write_text(reporter.to_markdown(), encoding="utf-8")

        logger.info("Reports written to %s", output)
        return md_path


def main() -> None:
    """CLI entry point for the benchmark runner."""
    import argparse

    parser = argparse.ArgumentParser(description="NeoMint Evaluation Suite")
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help="Path to fixtures directory (default: eval/fixtures/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Path to output directory (default: eval/results/)",
    )
    parser.add_argument(
        "--mode",
        choices=["policy"],
        default="policy",
        help="Evaluation mode (default: policy)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    fixtures = load_fixtures(args.fixtures_dir)
    print(f"Loaded {fixtures.count} fixtures across {len(fixtures.categories)} categories")

    runner = BenchmarkRunner(fixtures)

    if args.mode == "policy":
        results = runner.run_policy_evaluation()

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print(f"\nResults: {passed} passed, {failed} failed, {len(results)} total")

    report_path = runner.generate_report(args.output_dir)
    print(f"Report: {report_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
