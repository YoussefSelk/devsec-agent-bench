FROM ghcr.io/astral-sh/uv:0.11.26@sha256:3d868e555f8f1dbc324afa005066cd11e1053fc4743b9808ca8025283e65efa5 AS uv
FROM python:3.11-slim@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_CACHE=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv UV_NO_CACHE=0 uv sync --frozen --no-dev --no-editable \
    && groupadd --gid 10001 bench \
    && useradd --uid 10001 --gid 10001 --no-create-home bench \
    && mkdir /results && chown bench:bench /results
ENV PATH="/app/.venv/bin:$PATH"
USER 10001:10001
ENTRYPOINT ["devsec-bench"]
CMD ["run", "--agent", "reference", "--home", "/results"]
