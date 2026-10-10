FROM ghcr.io/astral-sh/uv:0.11.26 AS uv
FROM python:3.11-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_CACHE=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable \
    && groupadd --gid 10001 bench \
    && useradd --uid 10001 --gid 10001 --no-create-home bench \
    && mkdir /results && chown bench:bench /results
ENV PATH="/app/.venv/bin:$PATH"
USER 10001:10001
ENTRYPOINT ["devsec-bench"]
CMD ["run", "--agent", "reference", "--home", "/results"]
