"""Keep production image publication behind the actual regression/startup gates."""
from pathlib import Path

import yaml


def test_image_publication_requires_regression_and_migration_workflow():
    workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
    pipeline = yaml.load((workflows / "public-ci.yml").read_text(encoding="utf-8"),
                         Loader=yaml.BaseLoader)
    tests = yaml.load((workflows / "tests.yml").read_text(encoding="utf-8"),
                      Loader=yaml.BaseLoader)
    assert set(pipeline["jobs"]["build-and-publish"]["needs"]) == {"lint-test", "tests"}
    assert pipeline["jobs"]["tests"]["uses"] == "./.github/workflows/tests.yml"
    assert "workflow_call" in tests["on"]
    assert any("node --test" in step.get("run", "") for step in tests["jobs"]["pytest"]["steps"])
    migration = tests["jobs"]["migrations-postgres"]
    assert migration["services"]["postgres"]["image"] == "postgres:16"
    assert sum("python -m app.migration_runner" in step.get("run", "")
               for step in migration["steps"]) == 2
