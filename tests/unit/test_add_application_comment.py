"""Unit tests for BambooHRClient.add_application_comment()."""

import httpx
import orjson
import pytest
import respx

from ss_utils_bamboohr import BambooHRClient


@pytest.mark.unit
@respx.mock
async def test_add_comment_posts_correct_body():
    """add_application_comment POSTs type+comment JSON body."""
    route = respx.post("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001/comments").mock(
        return_value=httpx.Response(200, content=b"")
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        await client.add_application_comment(1001, "Looks great!")

    assert route.called
    body = orjson.loads(route.calls.last.request.content)
    assert body["type"] == "comment"
    assert body["comment"] == "Looks great!"


@pytest.mark.unit
@respx.mock
async def test_add_comment_returns_none():
    """add_application_comment returns None on success."""
    respx.post("https://testco.bamboohr.com/api/v1/applicant_tracking/applications/1001/comments").mock(
        return_value=httpx.Response(200, content=b"")
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        result = await client.add_application_comment(1001, "LGTM")

    assert result is None
