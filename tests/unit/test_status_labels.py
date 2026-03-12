"""Unit tests for status_labels filtering in BambooHRClient."""

import httpx
import orjson
import pytest
import respx

from ss_utils_bamboohr import BambooHRClient

MOCK_RESPONSE = {
    "paginationComplete": True,
    "nextPageUrl": None,
    "applications": [
        {
            "id": 1001,
            "appliedDate": "2024-01-15",
            "status": {"id": 3, "label": "Manager should check CV"},
            "rating": 4.5,
            "applicant": {
                "id": 501,
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "jane.doe@example.com",
                "source": "LinkedIn",
            },
            "job": {"id": 42, "title": "AI Engineer"},
        },
        {
            "id": 1002,
            "appliedDate": "2024-01-16",
            "status": {"id": 4, "label": "New"},
            "rating": 3.0,
            "applicant": {
                "id": 502,
                "firstName": "John",
                "lastName": "Smith",
                "email": "john.smith@example.com",
                "source": "Indeed",
            },
            "job": {"id": 42, "title": "AI Engineer"},
        }
    ],
}


@pytest.mark.unit
@respx.mock
async def test_get_all_applications_with_status_labels_filter():
    """get_all_applications filters by status_labels."""
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_RESPONSE))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        # Filter for only one status
        result = await client.get_all_applications(status_labels=["Manager should check CV"])
        
        assert len(result) == 1
        assert result[0].id == 1001
        assert result[0].status.label == "Manager should check CV"

        # Filter for multiple statuses
        result_multi = await client.get_all_applications(status_labels=["Manager should check CV", "New"])
        assert len(result_multi) == 2

        # Filter for non-existent status
        result_none = await client.get_all_applications(status_labels=["Non-existent"])
        assert len(result_none) == 0
