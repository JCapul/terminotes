set shell := ["bash", "-lc"]

bootstrap:
	uv sync
	uv run pre-commit install

cli *args="--help":
	uv run python -m terminotes {{args}}

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

test:
	uv run pytest

precommit:
	uv run pre-commit run --all-files

release bump="patch":
	uv run python scripts/prepare_release.py {{bump}}

publish:
	uv publish
