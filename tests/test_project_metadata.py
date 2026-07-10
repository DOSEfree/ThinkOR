from __future__ import annotations

import tomllib
from pathlib import Path

from ideaos_agent import __version__


def load_pyproject() -> dict[str, object]:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as file:
        return tomllib.load(file)


def test_package_version_matches_pyproject() -> None:
    pyproject = load_pyproject()
    project = pyproject["project"]

    assert isinstance(project, dict)
    assert project["version"] == __version__


def test_dev_dependencies_do_not_include_httpx2() -> None:
    pyproject = load_pyproject()
    project = pyproject["project"]

    assert isinstance(project, dict)
    runtime_dependencies = project["dependencies"]
    assert isinstance(runtime_dependencies, list)
    assert "httpx>=0.27,<1.0" in runtime_dependencies

    optional_dependencies = project["optional-dependencies"]
    assert isinstance(optional_dependencies, dict)
    dev_dependencies = optional_dependencies["dev"]

    assert isinstance(dev_dependencies, list)
    assert "httpx2>=2.5,<3.0" not in dev_dependencies
