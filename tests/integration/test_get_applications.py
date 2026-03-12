"""Integration tests for get_applications() — makes real BambooHR API calls."""

import os

import pytest

from ss_utils_bamboohr import ApplicationsListResponse, BambooHRClient


@pytest.mark.integration
async def test_get_applications_returns_list():
    """get_applications returns a valid ApplicationsListResponse from the live API."""
    api_key = os.environ["BAMBOOHR_API_KEY"]
    company_domain = os.environ["BAMBOOHR_COMPANY_DOMAIN"]

    async with BambooHRClient(company_domain=company_domain, api_key=api_key) as client:
        result = await client.get_applications()

    assert isinstance(result, ApplicationsListResponse)
    assert isinstance(result.applications, list)
    # Log the fields we see for model validation
    if result.applications:
        app = result.applications[0]
        print(f"Sample application id={app.id} rating={app.rating} job={app.job.title}")


@pytest.mark.integration
async def test_get_applications_with_job_id():
    """get_applications with BAMBOOHR_JOB_ID filters results."""
    api_key = os.environ["BAMBOOHR_API_KEY"]
    company_domain = os.environ["BAMBOOHR_COMPANY_DOMAIN"]
    job_id = int(os.environ.get("BAMBOOHR_JOB_ID", "0"))
    if not job_id:
        pytest.skip("BAMBOOHR_JOB_ID not set")

    async with BambooHRClient(company_domain=company_domain, api_key=api_key) as client:
        result = await client.get_applications(job_id=job_id)

    assert isinstance(result, ApplicationsListResponse)
    for app in result.applications:
        assert app.job.id == job_id
