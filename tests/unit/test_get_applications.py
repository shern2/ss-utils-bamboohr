"""Unit tests for BambooHRClient.get_applications()."""

import httpx
import orjson
import pytest
import respx

from ss_utils_bamboohr import ApplicationsListResponse, BambooHRClient

MOCK_RESPONSE = {
    "paginationComplete": True,
    "nextPageUrl": None,
    "applications": [
        {
            "id": 1001,
            "appliedDate": "2024-01-15",
            "status": {"id": 3, "label": "Active"},
            "rating": 4.5,
            "applicant": {
                "id": 501,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane.doe@example.com",
                "source": "LinkedIn",
            },
            "job": {"id": 42, "title": "AI Engineer"},
        }
    ],
}


@pytest.mark.unit
@respx.mock
async def test_get_applications_returns_list():
    """get_applications returns a parsed ApplicationsListResponse."""
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_RESPONSE))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        result = await client.get_applications()

    assert isinstance(result, ApplicationsListResponse)
    assert len(result.applications) == 1
    app = result.applications[0]
    assert app.id == 1001
    assert app.applicant.lastName == "Doe"
    assert app.rating == 4.5
    assert app.job.title == "AI Engineer"
    assert result.paginationComplete is True


@pytest.mark.unit
@respx.mock
async def test_get_applications_with_job_id_filter():
    """job_id is passed as 'jobId' query param."""
    route = respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps({**MOCK_RESPONSE, "applications": []}))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        await client.get_applications(job_id=42)

    assert route.called
    request = route.calls.last.request
    assert "jobId=42" in str(request.url)


@pytest.mark.unit
@respx.mock
async def test_get_applications_pagination():
    """page param is forwarded correctly."""
    route = respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps({**MOCK_RESPONSE, "applications": []}))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        await client.get_applications(page=2)

    assert "page=2" in str(route.calls.last.request.url)


@pytest.mark.unit
@respx.mock
async def test_get_applications_401_raises_auth_error():
    """401 response raises BambooHRAuthError."""
    from ss_utils_bamboohr import BambooHRAuthError

    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )

    async with BambooHRClient(company_domain="testco", api_key="badkey") as client:
        with pytest.raises(BambooHRAuthError):
            await client.get_applications()
