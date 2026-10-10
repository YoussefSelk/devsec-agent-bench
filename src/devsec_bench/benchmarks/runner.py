"""Isolated read-only analyses; fixture code is never executed."""

import hashlib
import random
import shutil
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable
from uuid import uuid4

from devsec_bench.agents.base import Agent
from devsec_bench.agents.reference import ReferenceAgent
from devsec_bench.evaluation.evaluator import evaluate
from devsec_bench.models import AgentConfig, AgentOutput, Run, Scenario, ScenarioResult
from devsec_bench.tools.registry import Registry


def execute(scenario: Scenario, config: AgentConfig, repetition: int, factory: Callable[[], Agent]) -> ScenarioResult:
    start = time.monotonic()
    effective = config.model_copy(update={"timeout": min(config.timeout, scenario.timeout), "max_iterations": min(config.max_iterations, scenario.max_iterations)})
    events = []
    try:
        with tempfile.TemporaryDirectory(prefix="devsec-bench-") as directory:
            from pathlib import Path

            root = Path(directory) / "target"
            # Defense against runtime mutation of canonical trusted fixtures.
            if any(p.is_symlink() for p in scenario.repository.rglob("*")):
                raise ValueError("Fixture symlink detected")
            shutil.copytree(scenario.repository, root)
            registry = Registry(root, scenario.tools, config.max_tool_calls, start + effective.timeout)
            events = registry.events
            output = factory().run(scenario.context(), registry, effective)
            if time.monotonic() - start > effective.timeout:
                output = output.model_copy(update={"status": "timeout", "error": "Execution timeout"})
    except Exception:
        # Exception text can contain provider credentials or source values.
        output = AgentOutput(status="error", error="Scenario execution failed")
    duration = time.monotonic() - start
    return ScenarioResult(scenario=scenario.id, name=scenario.name, repetition=repetition, output=output, metrics=evaluate(scenario.expected, output, events), events=events, duration=duration, estimated_cost=output.usage.cost(config.pricing))


def run_suite(scenarios: list[Scenario], config: AgentConfig, repetitions: int = 1, concurrency: int = 1, on_update: Callable[[Run], None] | None = None, factory: Callable[[], Agent] | None = None) -> Run:
    if not 1 <= repetitions <= 100 or not 1 <= concurrency <= 32:
        raise ValueError("Repetitions must be 1..100 and concurrency 1..32")
    if config.max_cost is not None and (concurrency != 1 or repetitions != 1 or len(scenarios) != 1):
        raise ValueError("Dollar-capped runs require one scenario, one repetition and one worker")
    if factory is None:
        if config.agent == "llm":
            from devsec_bench.agents.llm import LLMAgent

            LLMAgent.validate_config(config)
            factory = LLMAgent
        else:
            factory = ReferenceAgent
    digest = hashlib.sha256()
    for scenario in scenarios:
        digest.update(scenario.model_dump_json().encode())
        for path in sorted(scenario.repository.rglob("*")):
            if path.is_file():
                digest.update(path.relative_to(scenario.repository).as_posix().encode())
                digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    run = Run(id=uuid4().hex, config=config, suite_digest=digest.hexdigest())
    jobs = [(scenario, n) for n in range(1, repetitions + 1) for scenario in scenarios]
    random.Random(config.seed).shuffle(jobs)
    pool = ThreadPoolExecutor(max_workers=concurrency)
    futures: dict[Future[ScenarioResult], tuple[Scenario, int]] = {}
    if on_update:
        on_update(run)
    try:
        for scenario, n in jobs:
            futures[pool.submit(execute, scenario, config, n, factory)] = (scenario, n)
        for future in as_completed(futures):
            run.results.append(future.result())
            run.results.sort(key=lambda r: (r.scenario, r.repetition))
            if on_update:
                on_update(run)
    except KeyboardInterrupt:
        run.interrupted = True
        for future in futures:
            future.cancel()
        if on_update:
            on_update(run)
    finally:
        # Built-in agents have cooperative tool deadlines and bounded HTTP requests.
        pool.shutdown(wait=True, cancel_futures=True)
    return run
