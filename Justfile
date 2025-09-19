set shell := ["bash", "-lc"]

bootstrap:
	uv sync

cli *args="--help":
	uv run python -m terminotes {{args}}

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

test:
	uv run pytest

