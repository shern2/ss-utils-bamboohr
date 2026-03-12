"""Integration tests for download_file() — HIGHEST RISK, tests undocumented ATS endpoint."""

import os

import pytest

from ss_utils_bamboohr import BambooHRAuthError, BambooHRClient, BambooHRNotFoundError


@pytest.mark.integration
async def test_download_resume_file():
    """download_file works with a real ATS resumeFileId.

    This test validates the critical unknown: whether /api/v1/files/{fileId}
    works for ATS resume file IDs (the spec only documents it for company files).
    """
    api_key = os.environ["BAMBOOHR_API_KEY"]
    company_domain = os.environ["BAMBOOHR_COMPANY_DOMAIN"]
    session_cookie = os.environ.get("BAMBOOHR_SESSION_COOKIE")

    async with BambooHRClient(
        company_domain=company_domain, api_key=api_key, session_cookie=session_cookie
    ) as client:
        # Get a real resumeFileId from the first application with one
        apps = await client.get_applications()
        resume_file_id = None
        for app in apps.applications:
            detail = await client.get_application(app.id)
            if detail.resumeFileId:
                resume_file_id = detail.resumeFileId
                break

        if not resume_file_id:
            pytest.skip("No applications with a resumeFileId found")

        print(f"Attempting to download file_id={resume_file_id}")
        try:
            result = await client.download_file(resume_file_id)
            assert isinstance(result, bytes)
            assert len(result) > 0
            print(f"SUCCESS: downloaded {len(result)} bytes, header={result[:8]!r}")
        except (BambooHRNotFoundError, BambooHRAuthError) as e:
            pytest.fail(
                f"CRITICAL: /api/v1/files/{resume_file_id} returned {e.status_code}. "
                "ATS resume files are NOT accessible via the company files endpoint. "
                "Need to find the real ATS file download URL."
            )
