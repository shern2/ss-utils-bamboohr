"""ss-utils-bamboohr: async Python client for the BambooHR ATS API."""

from ._client import BambooHRClient, get_file_extension
from .exceptions import (
    BambooHRAuthError,
    BambooHRError,
    BambooHRHTTPError,
    BambooHRNotFoundError,
    BambooHRRateLimitError,
)
from .models import (
    AddCommentRequest,
    ApplicantDetail,
    ApplicantSummary,
    ApplicationComment,
    ApplicationDetail,
    ApplicationsListResponse,
    ApplicationStatus,
    ApplicationSummary,
    HiringLead,
    JobDetail,
    JobSummary,
    QuestionAnswer,
)

__all__ = [
    "BambooHRClient",
    "get_file_extension",
    "BambooHRError",
    "BambooHRHTTPError",
    "BambooHRAuthError",
    "BambooHRNotFoundError",
    "BambooHRRateLimitError",
    "AddCommentRequest",
    "ApplicationComment",
    "ApplicationDetail",
    "ApplicationsListResponse",
    "ApplicationStatus",
    "ApplicationSummary",
    "ApplicantDetail",
    "ApplicantSummary",
    "HiringLead",
    "JobDetail",
    "JobSummary",
    "QuestionAnswer",
]
