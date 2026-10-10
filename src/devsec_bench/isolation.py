"""Restricted offline container launch. Docker is a boundary, not a complete sandbox."""

import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4


def docker_command(home: Path, arguments: list[str], name: str = "devsec-bench") -> list[str]:
    if not arguments or arguments[0] != "run":
        raise ValueError("Only benchmark execution is permitted in the restricted wrapper")
    if home.is_symlink():
        raise ValueError("Artifact directory must not be a symlink")
    uid = os.getuid() if hasattr(os, "getuid") else 10001
    gid = os.getgid() if hasattr(os, "getgid") else 10001
    if uid == 0:
        uid, gid = 10001, 10001
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--read-only",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=64",
        "--memory=512m",
        "--cpus=1",
        f"--user={uid}:{gid}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--mount",
        f"type=bind,source={home.resolve()},target=/results",
        "devsec-agent-bench:local",
        *arguments,
        "--home",
        "/results",
    ]


def docker_run(home: Path, arguments: list[str], timeout: float) -> int:
    if hasattr(os, "getuid") and os.getuid() == 0:
        raise ValueError(
            "Launch Docker benchmarking from a non-root host account so artifact ownership is preserved"
        )
    if not shutil.which("docker"):
        raise ValueError("Docker isolation requested but Docker is unavailable; no local fallback")
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Docker isolation cannot be established; no local fallback") from exc
    home.mkdir(parents=True, exist_ok=True)
    name = f"devsec-bench-{uuid4().hex}"
    try:
        return subprocess.run(
            docker_command(home, arguments, name), timeout=timeout, check=False
        ).returncode
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=10, check=False)
        raise ValueError(
            "Container execution timed out; completed results remain in artifact directory"
        ) from exc
    except OSError as exc:
        raise ValueError("Container execution could not start") from exc
