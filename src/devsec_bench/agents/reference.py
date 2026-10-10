"""Source-pattern reference agent; deliberately limited to synthetic fixture idioms."""

import time

from devsec_bench.models import AgentConfig, AgentOutput, Finding, TaskContext
from devsec_bench.tools.registry import Registry

# Category, source pattern, structured remediation action, risk, correction.
# These rules do not receive scenario IDs, expected findings, or evaluator metadata.
RULES = [
    ("hardcoded_credentials", "API_PASSWORD =", "use_environment", "Embedded credentials can leak through source control.", "Load credentials from environment or a secret store."),
    ("input_validation", 'age = request["age"]', "validate_input", "Unvalidated input can violate domain constraints.", "Validate integer type and an explicit allowed age range."),
    ("sensitive_logging", 'logging.info("token=', "redact_logs", "Logs expose authentication material.", "Remove token values; log only non-sensitive metadata."),
    ("permissive_config", 'allowed_origins: ["*"]', "restrict_origins", "Wildcard origins allow untrusted browser clients.", "Configure trusted origins explicitly and disable production debug."),
    ("unsafe_path", 'Path("uploads") / request["filename"]', "confine_path", "Untrusted paths may escape the upload directory.", "Resolve paths and verify containment under the authorized root."),
    ("missing_authorization", 'store.delete(request["account_id"])', "check_ownership", "Deletion lacks a caller ownership check.", "Authenticate and verify ownership or administrative permission."),
    ("ci_secret_handling", 'echo "$DEPLOY_TOKEN"', "protect_ci_secret", "CI output discloses a deployment credential.", "Remove echo, use masked protected variables and disable tracing."),
]


class ReferenceAgent:
    def run(self, context: TaskContext, registry: Registry, config: AgentConfig) -> AgentOutput:
        start = time.monotonic()
        iterations = 0
        findings: list[Finding] = []

        def call(name: str, args: dict[str, str]) -> dict[str, object]:
            nonlocal iterations
            if time.monotonic() - start >= config.timeout:
                raise TimeoutError
            if iterations >= config.max_iterations:
                raise RuntimeError("Iteration budget exhausted")
            iterations += 1
            result = registry.call(name, args)
            if "error" in result:
                raise ValueError("Repository tool failed")
            return result

        try:
            listing = call("list_files", {})
            files = listing["files"]
            assert isinstance(files, list)
            for file in files:
                text = str(call("read_file", {"path": file})["content"])
                for line, source in enumerate(text.splitlines(), 1):
                    for category, pattern, action, risk, correction in RULES:
                        if pattern in source:
                            findings.append(Finding(category=category, file=file, line=line, action=action, explanation=risk, remediation=correction))
            if "requirements.txt" in files:
                dependencies = call("inspect_dependencies", {})["dependencies"]
                assert isinstance(dependencies, list)
                requirements = str(call("read_manifest", {"path": "requirements.txt"})["content"])
                for dependency in dependencies:
                    if dependency["vulnerable"]:
                        line = requirements.splitlines().index(f'{dependency["name"]}=={dependency["version"]}') + 1
                        findings.append(Finding(category="vulnerable_dependency", file="requirements.txt", line=line, action="upgrade_dependency", explanation="The pinned local advisory marks this version affected.", remediation=f'Upgrade {dependency["name"]} to {dependency["fixed"]} or a reviewed later version.'))
            return AgentOutput(findings=findings, iterations=iterations)
        except TimeoutError:
            return AgentOutput(findings=findings, iterations=iterations, status="timeout", error="Execution timeout")
        except RuntimeError:
            return AgentOutput(findings=findings, iterations=iterations, status="budget", error="Iteration budget exhausted")
        except (ValueError, KeyError):
            return AgentOutput(findings=findings, iterations=iterations, status="error", error="Repository analysis failed")
