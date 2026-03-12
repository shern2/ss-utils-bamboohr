"""BambooHR exception hierarchy."""

import httpx

_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_RATE_LIMIT = 429


class BambooHRError(Exception):
    """Base exception for all BambooHR SDK errors."""


class BambooHRHTTPError(BambooHRError):
    """Raised when the BambooHR API returns an error HTTP status."""

    def __init__(self, response: httpx.Response) -> None:
        self.status_code = response.status_code
        self.response = response
        super().__init__(f"BambooHR API error {response.status_code}: {response.text}")


class BambooHRNotFoundError(BambooHRHTTPError):
    """Raised on 404 responses."""


class BambooHRAuthError(BambooHRHTTPError):
    """Raised on 401/403 responses."""


class BambooHRRateLimitError(BambooHRHTTPError):
    """Raised on 429 responses."""


def raise_for_status(response: httpx.Response) -> None:
    """Raise appropriate BambooHRError for non-2xx responses.

    Args:
        response: The httpx response to check.

    Raises:
        BambooHRAuthError: On 401 or 403.
        BambooHRNotFoundError: On 404.
        BambooHRRateLimitError: On 429.
        BambooHRHTTPError: On any other non-2xx status.
    """
    if response.is_success:
        return
    status = response.status_code
    if status in (_HTTP_UNAUTHORIZED, _HTTP_FORBIDDEN):
        raise BambooHRAuthError(response)
    if status == _HTTP_NOT_FOUND:
        raise BambooHRNotFoundError(response)
    if status == _HTTP_RATE_LIMIT:
        raise BambooHRRateLimitError(response)
    raise BambooHRHTTPError(response)
