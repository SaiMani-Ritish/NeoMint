"""Test fixture loader for the NeoMint evaluation suite.

Loads JSON/YAML test fixtures from eval/fixtures/ and validates
them against the fixture schema.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger("neomint-eval.fixtures")

# Default fixtures directory
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


class ExpectedResult(BaseModel):
    """Expected outcome of a test fixture."""

    plan_tools: list[str] = Field(default_factory=list)
    needs_confirmation: bool | None = None
    risk_level: str | None = None
    clarification: str | None = None
    execution_blocked: bool = False
    kind: str | None = None  # expected kind: plan, clarification, refusal


class TestFixture(BaseModel):
    """A single evaluation test case."""

    id: str
    category: str
    description: str
    input: str
    expected: ExpectedResult
    tags: list[str] = Field(default_factory=list)


class FixtureSet(BaseModel):
    """A collection of test fixtures."""

    fixtures: list[TestFixture]

    @property
    def count(self) -> int:
        return len(self.fixtures)

    def filter_by_category(self, category: str) -> list[TestFixture]:
        return [f for f in self.fixtures if f.category == category]

    def filter_by_tag(self, tag: str) -> list[TestFixture]:
        return [f for f in self.fixtures if tag in f.tags]

    @property
    def categories(self) -> set[str]:
        return {f.category for f in self.fixtures}


def load_fixtures(fixtures_dir: Path | None = None) -> FixtureSet:
    """Load all test fixtures from the fixtures directory.

    Supports JSON and YAML files. Files are loaded from the root of
    the fixtures directory and all subdirectories.

    Args:
        fixtures_dir: Path to the fixtures directory. Defaults to eval/fixtures/.

    Returns:
        FixtureSet with all loaded and validated fixtures.
    """
    root = fixtures_dir or FIXTURES_DIR

    if not root.exists():
        logger.warning("Fixtures directory not found: %s", root)
        return FixtureSet(fixtures=[])

    all_fixtures: list[TestFixture] = []

    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text("utf-8"))
            if isinstance(data, list):
                for item in data:
                    all_fixtures.append(TestFixture.model_validate(item))
            elif isinstance(data, dict):
                all_fixtures.append(TestFixture.model_validate(data))
        except Exception as exc:
            logger.error("Failed to load fixture %s: %s", path, exc)

    # Also support YAML
    for path in sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml")):
        try:
            import yaml
            data = yaml.safe_load(path.read_text("utf-8"))
            if isinstance(data, list):
                for item in data:
                    all_fixtures.append(TestFixture.model_validate(item))
            elif isinstance(data, dict):
                all_fixtures.append(TestFixture.model_validate(data))
        except ImportError:
            logger.warning("PyYAML not installed — skipping YAML fixtures")
            break
        except Exception as exc:
            logger.error("Failed to load fixture %s: %s", path, exc)

    logger.info("Loaded %d fixtures from %s", len(all_fixtures), root)
    return FixtureSet(fixtures=all_fixtures)
