"""Unit tests for fetch_candidates_pipeline()."""

import httpx
import orjson
import pytest
import respx
import yaml
from pathlib import Path

from ss_utils_bamboohr import BambooHRClient

MOCK_APPLICATIONS = {
    "paginationComplete": True,
    "applications": [
        {
            "id": 1001,
            "appliedDate": "2024-01-15",
            "status": {"id": 3, "label": "Active"},
            "rating": 5.0,
            "applicant": {"id": 501, "firstName": "Jane", "lastName": "Doe"},
            "job": {"id": 42, "title": "AI Engineer"},
        }
    ],
}

MOCK_DETAIL = {
    "id": 1001,
    "appliedDate": "2024-01-15",
    "status": {"id": 3, "label": "Active"},
    "rating": 5.0,
    "resumeFileId": 999,
    "applicant": {
        "id": 501,
        "firstName": "Jane",
        "lastName": "Doe",
        "avatar": "http://example.com/avatar.jpg",
    },
    "job": {
        "id": 42,
        "title": "AI Engineer",
        "hiringLead": {"employeeId": 1, "firstName": "Boss", "avatar": "http://example.com/boss.jpg"},
    },
    "questionsAndAnswers": [],
    "attachments": [{"id": 888, "fileName": "portfolio.pdf"}],
}


@pytest.mark.unit
@respx.mock
async def test_fetch_candidates_pipeline_success(tmp_path: Path):
    """fetch_candidates_pipeline correctly processes applications and saves files."""
    # Mock list applications
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_APPLICATIONS))
    )
    # Mock application detail
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_DETAIL))
    )
    # Mock file downloads
    respx.get("https://testco.bamboohr.com/files/download.php?id=999").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.4 mock resume")
    )
    respx.get("https://testco.bamboohr.com/files/download.php?id=888").mock(
        return_value=httpx.Response(200, content=b"%PDF-1.4 mock portfolio")
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey", session_cookie="fake_session") as client:
        stats = await client.fetch_candidates_pipeline(output_base=tmp_path, job_ids=[42], rating_min=4.0)

    assert stats["processed"] == 1
    assert stats["errors"] == 0

    # Verify directory structure
    app_dir = tmp_path / "jobs" / "AI Engineer (42)" / "Jane Doe (1001)"
    assert app_dir.exists()
    assert (app_dir / "application.yaml").exists()
    assert (app_dir / "raw" / "resume.pdf").exists()
    assert (app_dir / "raw" / "portfolio.pdf").exists()

    # Verify YAML content (avatars should be stripped)
    with open(app_dir / "application.yaml", "r") as f:
        data = yaml.safe_load(f)
        assert data["id"] == 1001
        assert data["applicant"]["avatar"] is None
        assert data["job"]["hiringLead"]["avatar"] is None


@pytest.mark.unit
@respx.mock
async def test_fetch_candidates_pipeline_skips_existing(tmp_path: Path):
    """fetch_candidates_pipeline skips processing if application.yaml already exists."""
    app_dir = tmp_path / "jobs" / "AI Engineer (42)" / "Jane Doe (1001)"
    app_dir.mkdir(parents=True)
    yaml_path = app_dir / "application.yaml"
    yaml_path.write_text("existing: true")

    # Mock list applications
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_APPLICATIONS))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        stats = await client.fetch_candidates_pipeline(output_base=tmp_path, skip_existing=True)

    assert stats["processed"] == 0
    assert stats["skipped"] == 1
    # Ensure no detail call was made
    assert not respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001").called
