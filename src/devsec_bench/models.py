"""Validated domain objects; ground truth never enters TaskContext."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TOOLS = frozenset(
    {
        "list_files",
        "read_file",
        "search_code",
        "read_manifest",
        "inspect_dependencies",
        "inspect_git_diff",
        "get_repository_metadata",
    }
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Finding(StrictModel):
    category: str = Field(min_length=1, max_length=80)
    file: str = Field(min_length=1, max_length=256)
    line: int = Field(ge=1)
    explanation: str = Field(min_length=1, max_length=2000)
    remediation: str = Field(min_length=1, max_length=2000)
    action: str = Field(min_length=1, max_length=80)


class GroundTruth(StrictModel):
    id: str
    category: str
    file: str
    line: int = Field(ge=1)
    action: str
    reference: str


class TaskContext(StrictModel):
    instructions: str
    repository: str = "target"
    tools: list[str]


class Scenario(StrictModel):
    id: str = Field(pattern=r"^SEC-\d{3}$")
    name: str
    description: str
    repository: Path
    instructions: str
    tools: list[str]
    timeout: float = Field(default=30, gt=0, le=600)
    max_iterations: int = Field(default=20, ge=1, le=100)
    difficulty: Literal["easy", "medium", "hard"]
    expected: list[GroundTruth] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_tools(self) -> "Scenario":
        if not self.tools or not set(self.tools) <= TOOLS:
            raise ValueError("Unknown or empty tool allowlist")
        if len({e.id for e in self.expected}) != len(self.expected):
            raise ValueError("Duplicate ground-truth identifiers")
        return self

    def context(self) -> TaskContext:
        return TaskContext(instructions=self.instructions, tools=self.tools)


class Pricing(StrictModel):
    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)
    source: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)


class AgentConfig(StrictModel):
    agent: Literal["reference", "llm"] = "reference"
    provider: str = "openai"
    model: str | None = None
    max_iterations: int = Field(default=20, ge=1, le=100)
    max_tool_calls: int = Field(default=100, ge=1, le=1000)
    timeout: float = Field(default=30, gt=0, le=600)
    request_timeout: float = Field(default=20, gt=0, le=600)
    max_output_tokens: int = Field(default=2000, ge=1, le=16000)
    max_input_tokens: int = Field(default=16000, ge=1, le=128000)
    max_cost: float | None = Field(default=None, ge=0)
    pricing: Pricing | None = None
    seed: int = 0


class Usage(StrictModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def consistent(self) -> "Usage":
        if self.input_tokens is not None and self.output_tokens is not None:
            total = self.input_tokens + self.output_tokens
            if self.total_tokens is not None and self.total_tokens != total:
                raise ValueError("Inconsistent token usage")
            self.total_tokens = total
        return self

    def cost(self, pricing: Pricing | None) -> float | None:
        if pricing is None or self.input_tokens is None or self.output_tokens is None:
            return None
        return (
            self.input_tokens * pricing.input_per_million
            + self.output_tokens * pricing.output_per_million
        ) / 1_000_000


class ToolEvent(StrictModel):
    sequence: int
    tool: str
    arguments: dict[str, Any]
    authorized: bool
    error: str | None = None
    bytes_returned: int = 0
    duration: float = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentOutput(StrictModel):
    findings: list[Finding] = Field(default_factory=list, max_length=100)
    usage: Usage = Field(default_factory=Usage)
    error: str | None = None
    status: Literal["completed", "error", "timeout", "budget", "interrupted"] = "completed"
    iterations: int = 0


class Metrics(StrictModel):
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    location_accuracy: float
    remediation_validity: float
    policy_violations: int
    correctness: bool
    safe: bool
    reliable: bool
    passed: bool
    matched_ids: list[str]


class ScenarioResult(StrictModel):
    scenario: str
    name: str
    repetition: int
    output: AgentOutput
    metrics: Metrics
    events: list[ToolEvent]
    duration: float
    estimated_cost: float | None


class Run(StrictModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    config: AgentConfig
    results: list[ScenarioResult] = Field(default_factory=list)
    interrupted: bool = False
    suite_digest: str = ""
