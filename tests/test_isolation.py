from pathlib import Path

import pytest

from devsec_bench.isolation import docker_command, docker_run


def test_restricted_container_command(tmp_path: Path):
    command = docker_command(tmp_path, ["run", "--agent", "reference"])
    for flag in [
        "--read-only",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=512m",
        "--cpus=1",
    ]:
        assert flag in command
    assert any(arg.startswith("--user=") and not arg.startswith("--user=0:") for arg in command)
    assert not any("docker.sock" in arg or "privileged" in arg for arg in command)
    assert "--home" in command and "/results" in command


def test_isolation_refuses_without_docker(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("devsec_bench.isolation.shutil.which", lambda _: None)
    with pytest.raises(ValueError, match="Docker"):
        docker_run(tmp_path, ["run"], 30)


def test_isolation_rejects_external_command(tmp_path: Path):
    with pytest.raises(ValueError):
        docker_command(tmp_path, ["dashboard"])


def test_linux_artifacts_use_host_nonroot_uid(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("devsec_bench.isolation.os.getuid", lambda: 1000, raising=False)
    monkeypatch.setattr("devsec_bench.isolation.os.getgid", lambda: 1000, raising=False)
    assert "--user=1000:1000" in docker_command(tmp_path, ["run"])
