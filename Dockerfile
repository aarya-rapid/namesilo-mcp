FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --no-dev

# Expose MCP port (Smithery maps this automatically)
EXPOSE 8000

# Run the MCP server
CMD ["uv", "run", "python", "-m", "src.server"]
