import json
from pathlib import Path

import pytest

from devsec_bench.models import TOOLS
from devsec_bench.tools.registry import Registry


@pytest.fixture
def registry(tmp_path):
    (tmp_path / "app.py").write_text("print('synthetic')\n")
    (tmp_path / ".env").write_text("TOKEN=do-not-read")
    (tmp_path / "requirements.txt").write_text("demo-lib==1.0\n")
    return Registry(tmp_path, list(TOOLS))


@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "/etc/passwd",
        "C:/Windows/win.ini",
        ".env",
        ".git/config",
        "id_rsa",
        "a:stream",
    ],
)
def test_rejects_path_and_secret_access(registry, path):
    assert "error" in registry.call("read_file", {"path": path})
    assert registry.events[-1].authorized is False
    assert "do-not-read" not in json.dumps([e.model_dump() for e in registry.events])


def test_allowlist_unknown_repo_and_no_write(registry):
    registry.allowed = {"list_files"}
    for name, args in [
        ("read_file", {"path": "app.py"}),
        ("write_file", {}),
        ("list_files", {"repository": "host"}),
    ]:
        assert "error" in registry.call(name, args)
    assert (registry.root / "app.py").read_text() == "print('synthetic')\n"


def test_symlink_escape(registry, tmp_path: Path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("private")
    try:
        (tmp_path / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("OS does not allow symlink creation")
    assert "error" in registry.call("read_file", {"path": "link.txt"})
    assert "link.txt" not in registry.call("list_files", {})["files"]


def test_real_reads_search_and_output_limits(registry):
    assert registry.call("read_file", {"path": "app.py"})["content"] == "print('synthetic')\n"
    assert registry.call("search_code", {"query": "synthetic"})["matches"][0]["line"] == 1
    assert ".env" not in registry.call("list_files", {})["files"]
    (registry.root / "large.txt").write_text("x" * 100_000)
    assert "error" in registry.call("read_file", {"path": "large.txt"})
    assert "error" in registry.call("read_file", {"path": "app.py", "execute": True})
    assert [e.sequence for e in registry.events] == list(range(1, len(registry.events) + 1))


def test_bad_arguments_and_budget_are_traced(registry):
    assert "error" in registry.call("search_code", {"query": ""})
    registry.max_calls = len(registry.events)
    assert "error" in registry.call("list_files", {})


def test_untrusted_argument_keys_are_never_retained(registry):
    registry.call("list_files", {"sk-SENSITIVE_PRIVATE_ARGUMENT_KEY": "value"})
    assert "SENSITIVE_PRIVATE" not in registry.events[-1].model_dump_json()
