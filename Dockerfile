FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency + build files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (no dev deps, no editable install yet)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code (both packages)
COPY espn_api/ espn_api/
COPY mcp_server/ mcp_server/

# Install the project itself
RUN uv sync --frozen --no-dev

ENV MCP_TRANSPORT=sse

CMD ["uv", "run", "espn-mcp"]
