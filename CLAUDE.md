# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A BambooHR API Python SDK (`ss-utils-bamboohr`) focused on hiring-related API endpoints. The `public-openapi.yaml` at the repo root is the BambooHR OpenAPI spec and is the source of truth for available endpoints/schemas.

Reference: https://documentation.bamboohr.com/docs/getting-started

## Commands

```bash
just setup                          # Install deps + pre-commit hooks
uv sync --dev                       # Sync dependencies

uv run --env-file .env pytest -m unit          # Run unit tests
uv run --env-file .env pytest -m integration   # Run integration tests
uv run --env-file .env pytest tests/path/to/test_file.py::test_name  # Run single test

ruff check .                        # Lint
ruff format .                       # Format

just bump patch                     # Bump patch version, tag, and publish
just publish                        # Publish current version to PyPI
```

> Note: Integration tests require a `.env` file with BambooHR credentials. Use `.env.example` as a template.

## Architecture

- `src/ss_utils_bamboohr/` — main package (src layout, built with hatchling)
- `tests/unit/` — fast mocked tests
- `tests/integration/` — tests making real BambooHR API calls
- `tests/e2e/` — end-to-end workflow tests
- `tests/experimental/` — WIP/development tests

## Development Workflow

Build and test **one feature at a time** — never build a full set of features before testing:

1. Ground the API: Before implementing a new endpoint or fixing a model, use `api_playground/grounding.py` to record real API responses. This ensures models are grounded in reality, not just the (sometimes incomplete) OpenAPI spec.
2. Implement one feature/endpoint
3. Write an integration test to confirm the real API behaves as expected
4. Use that integration test's response to craft a unit test (mock the HTTP layer)
5. Verify the unit test passes

## Grounding Workflow

The `api_playground/` directory is used to explore and record real API interactions.
- `api_playground/grounding.py`: Script to fetch and save raw JSON responses.
- `api_playground/cassettes/`: VCR tapes of real interactions.

Always check `api_playground/` when encountering Pydantic validation errors to see what the API is actually returning.

Use `pytest-vcr` to record real HTTP interactions and replay them in unit tests when mocking manually is too complex or error-prone.

This incremental approach makes failures easy to isolate. The alternative — building everything then testing — makes bugs exponentially harder to debug.

## Key Conventions

- **HTTP**: use `httpx.AsyncClient` with async/await; add retry logic via `backoff` library
- **Models**: Pydantic v2 for all request/response schemas
- **Auth**: BambooHR uses HTTP Basic Auth with API key as the username and `x` as the password
- **Base URL**: `https://{companyDomain}.bamboohr.com`
- **Testing**: always pass `--env-file .env` when running pytest so credentials are available
- **Serialization**: prefer `orjson.loads`/`orjson.dumps` over `json`
