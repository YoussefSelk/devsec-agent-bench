"""Real local HTTP exchange through the production asynchronous adapter."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from devsec_bench.agents.llm import LLMAgent, OpenAIProvider
from devsec_bench.benchmarks.loader import discover
from devsec_bench.models import AgentConfig
from devsec_bench.tools.registry import Registry


def test_local_http_provider_exchange():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            payload = json.dumps(
                {
                    "choices": [{"message": {"role": "assistant", "content": '{"findings": []}'}}],
                    "usage": {"prompt_tokens": 33, "completion_tokens": 7, "total_tokens": 40},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class LocalTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.transport = httpx.AsyncHTTPTransport()

        async def handle_async_request(self, request):
            request.url = httpx.URL(f"http://127.0.0.1:{server.server_port}/v1/chat/completions")
            return await self.transport.handle_async_request(request)

        async def aclose(self):
            await self.transport.aclose()

    try:
        scenario = discover()[0]
        output = LLMAgent(
            OpenAIProvider(api_key="synthetic", async_transport=LocalTransport())
        ).run(
            scenario.context(),
            Registry(scenario.repository, scenario.tools),
            AgentConfig(agent="llm", model="caller-selected"),
        )
        assert output.status == "completed"
        assert output.usage.total_tokens == 40
        assert requests[0]["model"] == "caller-selected"
        assert requests[0]["max_completion_tokens"] == 2000
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
