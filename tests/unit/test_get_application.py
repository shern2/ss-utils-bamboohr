"""Unit tests for BambooHRClient.get_application()."""

import httpx
import orjson
import pytest
import respx

from ss_utils_bamboohr import (
    ApplicationComment,
    ApplicationDetail,
    BambooHRClient,
    BambooHRNotFoundError,
)

MOCK_DETAIL = {
    "id": 1001,
    "appliedDate": "2024-01-15",
    "status": {"id": 3, "label": "Active"},
    "rating": 4.5,
    "resumeFileId": 9901,
    "coverLetterFileId": 9902,
    "applicant": {
        "id": 501,
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "phoneNumber": "+1-555-0100",
        "source": "LinkedIn",
    },
    "job": {
        "id": 42,
        "title": "AI Engineer",
        "hiringLead": {
            "employeeId": 227,
            "firstName": "Shern Shern",
            "lastName": "Yap",
            "avatar": "https://example.com/avatar.jpg",
            "jobTitle": {"id": 18817, "label": "Head of AI"},
        },
    },
    "questionsAndAnswers": [
        {"question": "Years of experience?", "answer": "5"},
    ],
    "desiredSalary": "6500",
    "commentCount": 2,
    "attachments": [{"id": 123, "name": "portfolio.pdf"}],
}

MOCK_COMMENTS = [
    {
        "id": 1,
        "applicationId": 1001,
        "userId": 227,
        "type": "comment",
        "comment": "Great candidate!",
        "dateCreated": "2024-01-16T10:00:00Z",
    }
]


@pytest.mark.unit
@respx.mock
async def test_get_application_returns_detail():
    """get_application returns a parsed ApplicationDetail with file IDs."""
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_DETAIL))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        result = await client.get_application(1001)

    assert isinstance(result, ApplicationDetail)
    assert result.id == 1001
    assert result.resumeFileId == 9901
    assert result.coverLetterFileId == 9902
    assert result.applicant.email == "jane.doe@example.com"
    assert result.applicant.phoneNumber == "+1-555-0100"
    assert len(result.questionsAndAnswers) == 1
    assert result.questionsAndAnswers[0].question == "Years of experience?"
    assert result.desiredSalary == "6500"
    assert result.commentCount == 2
    assert result.job.hiringLead.employeeId == 227


@pytest.mark.unit
@respx.mock
async def test_get_application_comments():
    """get_application_comments returns a list of ApplicationComment."""
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001/comments").mock(
        return_value=httpx.Response(200, content=orjson.dumps(MOCK_COMMENTS))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        result = await client.get_application_comments(1001)

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], ApplicationComment)
    assert result[0].comment == "Great candidate!"


@pytest.mark.unit
@respx.mock
async def test_get_application_null_file_ids():
    """resumeFileId and coverLetterFileId can be null."""
    detail = {**MOCK_DETAIL, "resumeFileId": None, "coverLetterFileId": None}
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001").mock(
        return_value=httpx.Response(200, content=orjson.dumps(detail))
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        result = await client.get_application(1001)

    assert result.resumeFileId is None
    assert result.coverLetterFileId is None


@pytest.mark.unit
@respx.mock
async def test_get_application_404_raises_not_found():
    """404 response raises BambooHRNotFoundError."""
    respx.get("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/9999").mock(
        return_value=httpx.Response(404, text="Not Found")
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        with pytest.raises(BambooHRNotFoundError):
            await client.get_application(9999)
