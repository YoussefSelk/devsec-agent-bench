from typing import Protocol

from devsec_bench.models import AgentConfig, AgentOutput, TaskContext
from devsec_bench.tools.registry import Registry


class Agent(Protocol):
    def run(self, context: TaskContext, registry: Registry, config: AgentConfig) -> AgentOutput: ...
