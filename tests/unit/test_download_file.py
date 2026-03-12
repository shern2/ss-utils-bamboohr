"""Unit tests for BambooHRClient.download_file()."""

import httpx
import pytest
import respx

from ss_utils_bamboohr import BambooHRClient

FAKE_PDF_BYTES = b"%PDF-1.4 fake pdf content"


@pytest.mark.unit
@respx.mock
async def test_download_file_requires_session_cookie():
    """download_file raises ValueError if session_cookie is not provided."""
    async with BambooHRClient(company_domain="testco", api_key="testkey") as client:
        with pytest.raises(ValueError, match="Session cookie is required"):
            await client.download_file(9901)


@pytest.mark.unit
@respx.mock
async def test_download_file_with_session_cookie():
    """download_file uses pragmatic endpoint when session_cookie is provided."""
    session_cookie = "PHPSESSID=fake_session"
    file_id = 9901

    # Mock the pragmatic endpoint
    pragmatic_route = respx.get(f"https://testco.bamboohr.com/files/download.php?id={file_id}").mock(
        return_value=httpx.Response(200, content=FAKE_PDF_BYTES)
    )

    async with BambooHRClient(company_domain="testco", api_key="testkey", session_cookie=session_cookie) as client:
        result = await client.download_file(file_id)

    assert result == FAKE_PDF_BYTES
    assert pragmatic_route.called
    # Check if cookie was sent in headers
    last_request = pragmatic_route.calls.last.request
    assert last_request.headers["cookie"] == session_cookie


@pytest.mark.unit
@respx.mock
async def test_download_file_fails_if_pragmatic_fails():
    """download_file raises ValueError if pragmatic endpoint fails (e.g. redirects to login)."""
    session_cookie = "PHPSESSID=fake_session"
    file_id = 9901

    # Mock pragmatic endpoint to fail (e.g. redirect to login)
    respx.get(f"https://testco.bamboohr.com/files/download.php?id={file_id}").mock(
        return_value=httpx.Response(302, headers={"Location": "/login.php"})
    )
    # Mock the login page that it redirects to
    respx.get("https://testco.bamboohr.com/login.php").mock(return_value=httpx.Response(200, text="Login Page"))

    async with BambooHRClient(company_domain="testco", api_key="testkey", session_cookie=session_cookie) as client:
        with pytest.raises(ValueError, match="Pragmatic download failed"):
            await client.download_file(file_id)
