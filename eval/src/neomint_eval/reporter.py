"""Report generator for the NeoMint evaluation suite.

Produces structured JSON and human-readable markdown reports
from benchmark results.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from neomint_eval.runner import FixtureResult


class BenchmarkReporter:
    """Generates reports from benchmark results.

    Args:
        results: List of FixtureResult from a benchmark run.
    """

    def __init__(self, results: list[FixtureResult]) -> None:
        self.results = results

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total * 100 if self.total > 0 else 0.0

    @property
    def avg_duration_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.duration_ms for r in self.results) / len(self.results)

    def by_category(self) -> dict[str, dict[str, Any]]:
        """Group results by category with pass/fail counts."""
        categories: dict[str, dict[str, Any]] = {}

        for result in self.results:
            cat = result.fixture.category
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "total": 0, "fixtures": []}

            categories[cat]["total"] += 1
            if result.passed:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
            categories[cat]["fixtures"].append(result.fixture.id)

        return categories

    def to_dict(self) -> dict[str, Any]:
        """Generate a machine-readable JSON report."""
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.pass_rate, 1),
                "avg_duration_ms": round(self.avg_duration_ms, 2),
            },
            "by_category": self.by_category(),
            "results": [r.to_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        """Generate a human-readable markdown report."""
        lines: list[str] = []

        lines.append("# NeoMint Evaluation Report")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total fixtures | {self.total} |")
        lines.append(f"| Passed | {self.passed} |")
        lines.append(f"| Failed | {self.failed} |")
        lines.append(f"| Pass rate | {self.pass_rate:.1f}% |")
        lines.append(f"| Avg duration | {self.avg_duration_ms:.2f} ms |")
        lines.append("")

        # By category
        lines.append("## Results by Category")
        lines.append("")
        lines.append("| Category | Passed | Failed | Total | Rate |")
        lines.append("|----------|--------|--------|-------|------|")

        for cat, data in sorted(self.by_category().items()):
            rate = data["passed"] / data["total"] * 100 if data["total"] > 0 else 0
            lines.append(
                f"| {cat} | {data['passed']} | {data['failed']} | {data['total']} | {rate:.0f}% |"
            )

        lines.append("")

        # Failed fixtures detail
        failed_results = [r for r in self.results if not r.passed]
        if failed_results:
            lines.append("## Failed Fixtures")
            lines.append("")
            for result in failed_results:
                lines.append(f"### ❌ {result.fixture.id}")
                lines.append(f"- **Category:** {result.fixture.category}")
                lines.append(f"- **Input:** `{result.fixture.input}`")
                lines.append(f"- **Errors:**")
                for error in result.errors:
                    lines.append(f"  - {error}")
                lines.append("")
        else:
            lines.append("## All fixtures passed ✅")
            lines.append("")

        return "\n".join(lines)
