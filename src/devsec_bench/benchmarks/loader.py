"""Load evaluator-only YAML and constrain repositories to their scenario directory."""

from pathlib import Path

import yaml

from devsec_bench.models import Scenario

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


def load(path: Path) -> Scenario:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    scenario = Scenario.model_validate(data)
    relative = scenario.repository
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Repository must be relative and contained")
    root = path.parent.resolve()
    repository = root / relative
    if repository.is_symlink() or not repository.resolve().is_relative_to(root):
        raise ValueError("Repository escape")
    if not repository.is_dir():
        raise ValueError("Repository not found")
    for entry in repository.rglob("*"):
        if entry.is_symlink():
            raise ValueError("Symlinks are forbidden in fixture sources")
    for expected in scenario.expected:
        location = repository / expected.file
        if not location.resolve().is_relative_to(repository.resolve()) or not location.is_file():
            raise ValueError("Invalid ground-truth location")
        if expected.line > len(location.read_text(encoding="utf-8").splitlines()):
            raise ValueError("Ground-truth line outside file")
    return scenario.model_copy(update={"repository": repository.resolve()})


def discover(root: Path = SCENARIOS) -> list[Scenario]:
    scenarios = [load(path) for path in sorted(root.glob("*/scenario.yaml"))]
    if not scenarios or len({s.id for s in scenarios}) != len(scenarios):
        raise ValueError("Empty suite or duplicate scenario IDs")
    return scenarios
