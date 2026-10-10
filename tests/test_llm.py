import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest

from devsec_bench.agents.llm import LLMAgent, OpenAIProvider
from devsec_bench.benchmarks.loader import discover
from devsec_bench.models import AgentConfig, Pricing, Usage
from devsec_bench.tools.registry import Registry


def price():
    return Pricing(
        input_per_million=2,
        output_per_million=4,
        source="unit test synthetic rates",
        timestamp="2026-10-10",
    )


def test_cost_and_unknown_usage():
    assert Usage(input_tokens=1000, output_tokens=500).cost(price()) == 0.004
    assert Usage(input_tokens=1000, output_tokens=500).cost(None) is None
    assert Usage().cost(price()) is None


def response(message, usage=True):
    body = {"choices": [{"message": {"role": "assistant", **message}}]}
    if usage:
        body["usage"] = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}
    return body


def provider(handler):
    return OpenAIProvider(
        api_key="synthetic-test-credential",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_real_provider_request_tool_loop_and_usage():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(
                200,
                json=response(
                    {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "type": "function",
                                "function": {"name": "list_files", "arguments": "{}"},
                            }
                        ],
                        "content": None,
                    }
                ),
            )
        assert requests[-1]["messages"][-1]["role"] == "tool"
        return httpx.Response(200, json=response({"content": '{"findings": []}'}))

    scenario = discover()[0]
    registry = Registry(scenario.repository, scenario.tools)
    output = LLMAgent(provider(handle)).run(
        scenario.context(), registry, AgentConfig(agent="llm", model="test-model")
    )
    assert output.status == "completed"
    assert output.usage.total_tokens == 220
    assert len(registry.events) == 1
    assert requests[0]["model"] == "test-model"
    assert "expected" not in json.dumps(requests)
    assert "F-001" not in json.dumps(requests)


@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        response({"content": "bad json"}),
        response({"content": '{"findings": [], "usage": {"total_tokens": 0}}'}),
    ],
)
def test_malformed_responses_fail_closed(body):
    scenario = discover()[0]
    output = LLMAgent(provider(lambda _: httpx.Response(200, json=body))).run(
        scenario.context(),
        Registry(scenario.repository, scenario.tools),
        AgentConfig(agent="llm", model="test-model"),
    )
    assert output.status == "error"


def test_unknown_usage_and_api_error_do_not_leak():
    scenario = discover()[0]
    config = AgentConfig(agent="llm", model="test-model")
    output = LLMAgent(
        provider(
            lambda _: httpx.Response(
                200, json=response({"content": '{"findings": []}'}, usage=False)
            )
        )
    ).run(scenario.context(), Registry(scenario.repository, scenario.tools), config)
    assert output.usage.total_tokens is None
    error = LLMAgent(provider(lambda _: httpx.Response(401, text="secret-provider-content"))).run(
        scenario.context(), Registry(scenario.repository, scenario.tools), config
    )
    assert error.status == "error"
    assert "secret-provider-content" not in error.model_dump_json()


def test_dollar_budget_refuses_before_request():
    def handle(_):
        pytest.fail("No request should be made when reservation exceeds cap")

    scenario = discover()[0]
    output = LLMAgent(provider(handle)).run(
        scenario.context(),
        Registry(scenario.repository, scenario.tools),
        AgentConfig(agent="llm", model="test-model", max_cost=0, pricing=price()),
    )
    assert output.status == "budget"


def test_denied_llm_tool_is_traced(tmp_path: Path):
    calls = 0

    def handle(_):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json=response(
                    {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path":"../private"}',
                                },
                            }
                        ]
                    }
                ),
            )
        return httpx.Response(200, json=response({"content": '{"findings": []}'}))

    scenario = discover()[0]
    registry = Registry(scenario.repository, scenario.tools)
    LLMAgent(provider(handle)).run(
        scenario.context(), registry, AgentConfig(agent="llm", model="test-model")
    )
    assert not registry.events[0].authorized


def test_provider_drip_stream_obeys_absolute_deadline():
    class Drip(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(100):
                await asyncio.sleep(0.02)
                yield b" "

    adapter = OpenAIProvider(
        api_key="synthetic",
        async_transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=Drip())),
    )
    scenario = discover()[0]
    start = time.monotonic()
    output = LLMAgent(adapter).run(
        scenario.context(),
        Registry(scenario.repository, scenario.tools),
        AgentConfig(agent="llm", model="test", timeout=0.1),
    )
    assert output.status == "timeout"
    assert time.monotonic() - start < 0.5


def test_failed_followup_does_not_report_partial_usage_as_total():
    calls = 0

    def handle(_):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json=response(
                    {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "type": "function",
                                "function": {"name": "list_files", "arguments": "{}"},
                            }
                        ]
                    }
                ),
            )
        return httpx.Response(503, text="provider failure")

    scenario = discover()[0]
    output = LLMAgent(provider(handle)).run(
        scenario.context(),
        Registry(scenario.repository, scenario.tools),
        AgentConfig(agent="llm", model="test"),
    )
    assert output.status == "error"
    assert output.usage.total_tokens is None
