"""Integration tests for get_application() — makes real BambooHR API calls."""

import os

import pytest

from ss_utils_bamboohr import ApplicationDetail, BambooHRClient


@pytest.mark.integration
async def test_get_application_returns_detail():
    """get_application returns full ApplicationDetail with file IDs from live API."""
    api_key = os.environ["BAMBOOHR_API_KEY"]
    company_domain = os.environ["BAMBOOHR_COMPANY_DOMAIN"]

    # First get an application ID from the list
    async with BambooHRClient(company_domain=company_domain, api_key=api_key) as client:
        apps = await client.get_applications()
        if not apps.applications:
            pytest.skip("No applications available")

        app_id = apps.applications[0].id
        result = await client.get_application(app_id)

        assert isinstance(result, ApplicationDetail)
        assert result.id == app_id
        print(f"resumeFileId={result.resumeFileId} coverLetterFileId={result.coverLetterFileId}")
        print(f"questionsAndAnswers count={len(result.questionsAndAnswers)}")
        print(f"desiredSalary={result.desiredSalary}")
        print(f"commentCount={result.commentCount}")
        print(f"hiringLead={result.job.hiringLead}")

        # Test get_application_comments
        comments = await client.get_application_comments(app_id)
        assert isinstance(comments, list)
        print(f"comments count={len(comments)}")
