from pathlib import Path

import pytest
from pydantic import ValidationError

from devsec_bench.benchmarks.loader import discover, load
from devsec_bench.models import AgentConfig


def test_eight_valid_packaged_scenarios():
    scenarios = discover()
    assert len(scenarios) == 8
    assert len({s.id for s in scenarios}) == 8
    for scenario in scenarios:
        assert scenario.repository.is_dir()
        for finding in scenario.expected:
            assert (scenario.repository / finding.file).is_file()
        context = scenario.context()
        assert "expected" not in context.model_dump()
        assert "SEC-" not in context.model_dump_json()


def test_invalid_definition_and_repository_escape(tmp_path: Path):
    definition = tmp_path / "scenario.yaml"
    definition.write_text("id: broken\nrepository: ../outside\n")
    with pytest.raises((ValidationError, ValueError)):
        load(definition)


@pytest.mark.parametrize("kwargs", [{"max_iterations": 0}, {"timeout": -1}, {"max_cost": -1}])
def test_invalid_agent_limits(kwargs):
    with pytest.raises(ValidationError):
        AgentConfig(**kwargs)
