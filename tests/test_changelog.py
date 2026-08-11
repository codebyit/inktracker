from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "templates"


def test_in_app_changelog_starts_with_current_release():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    template = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    ).get_template("changelog.html")

    rendered = template.render()
    releases = re.findall(r"v(\d+\.\d+\.\d+)", rendered)

    assert releases, "The in-app changelog has no release entries"
    assert releases[0] == version
    assert f"v{version}" in rendered
