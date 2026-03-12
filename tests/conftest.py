"""Shared pytest fixtures for ss-utils-bamboohr tests."""

import os
from collections.abc import AsyncGenerator

import pytest

from ss_utils_bamboohr import BambooHRClient


@pytest.fixture
async def client() -> AsyncGenerator[BambooHRClient, None]:
    """BambooHRClient configured from environment variables.

    Requires BAMBOOHR_API_KEY and BAMBOOHR_COMPANY_DOMAIN to be set
    (pass --env-file .env when running pytest).
    """
    api_key = os.environ["BAMBOOHR_API_KEY"]
    company_domain = os.environ["BAMBOOHR_COMPANY_DOMAIN"]
    session_cookie = os.environ.get("BAMBOOHR_SESSION_COOKIE")
    async with BambooHRClient(company_domain=company_domain, api_key=api_key, session_cookie=session_cookie) as c:
        yield c


@pytest.fixture(scope="module")
def vcr_config():
    """pytest-vcr configuration: strip auth headers from cassettes."""
    return {
        "filter_headers": ["authorization"],
        "record_mode": "none",  # use existing cassettes; set to "new_episodes" to re-record
    }
