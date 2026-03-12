"""Pydantic v2 models for BambooHR ATS API request/response schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------


class LabelObject(BaseModel):
    """Generic object with id and label, often used for status, job title, etc."""

    id: int | None = None
    label: str


class ApplicationStatusGroup(StrEnum):
    """A list of application status groups to filter by."""

    ALL = "ALL"
    ALL_ACTIVE = "ALL_ACTIVE"
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    HIRED = "HIRED"


class ApplicationStatus(BaseModel):
    """Application status object."""

    id: int
    label: str
    dateChanged: str | None = None
    changedByUser: int | dict[str, Any] | None = None


class ApplicantSummary(BaseModel):
    """Minimal applicant info returned in list responses."""

    id: int
    firstName: str
    lastName: str
    avatar: str | None = None
    email: str | None = None
    source: str | None = None


class JobSummary(BaseModel):
    """Job/position reference."""

    id: int
    title: str | LabelObject


class HiringLead(BaseModel):
    """Hiring lead information."""

    employeeId: int | None = None
    firstName: str | None = None
    lastName: str | None = None
    avatar: str | None = None
    jobTitle: LabelObject | None = None


class JobDetail(JobSummary):
    """Job detail with hiring lead."""

    hiringLead: HiringLead | None = None


class ApplicationComment(BaseModel):
    """A comment on an application."""

    id: int
    applicationId: int
    userId: int
    userData: dict[str, Any] | None = None
    type: str
    comment: str
    dateCreated: str


# ---------------------------------------------------------------------------
# List endpoint models
# ---------------------------------------------------------------------------


class ApplicationSummary(BaseModel):
    """Single application row returned by GET /applications."""

    id: int
    appliedDate: str
    status: ApplicationStatus
    rating: float | None = None
    applicant: ApplicantSummary
    job: JobSummary


class ApplicationsListResponse(BaseModel):
    """Paginated list of applications."""

    paginationComplete: bool = Field(default=True)
    nextPageUrl: str | None = None
    applications: list[ApplicationSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Detail endpoint models
# ---------------------------------------------------------------------------


class QuestionAnswer(BaseModel):
    """A single question/answer pair from the application form."""

    question: str | LabelObject
    answer: str | LabelObject | None = None


class Address(BaseModel):
    """Applicant address info."""

    addressLine1: str | None = None
    addressLine2: str | None = None
    city: str | None = None
    state: str | None = None
    zipcode: str | None = None
    country: str | None = None


class ApplicantDetail(BaseModel):
    """Full applicant detail returned by GET /applications/{id}."""

    id: int
    firstName: str
    lastName: str
    email: str | None = None
    phoneNumber: str | None = None
    source: str | None = None
    avatar: str | None = None
    address: Address | None = None
    linkedinUrl: str | None = None
    websiteUrl: str | None = None
    availableStartDate: str | None = None
    education: str | None = None


class ApplicationDetail(BaseModel):
    """Full application detail returned by GET /applications/{applicationId}."""

    id: int
    appliedDate: str
    status: ApplicationStatus
    rating: float | None = None
    resumeFileId: int | None = None
    coverLetterFileId: int | None = None
    applicant: ApplicantDetail
    job: JobDetail
    questionsAndAnswers: list[QuestionAnswer] = Field(default_factory=list)
    desiredSalary: str | None = None
    commentCount: int | None = 0
    attachments: list[dict[str, Any]] | None = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AddCommentRequest(BaseModel):
    """Request body for adding a comment to an application."""

    type: Literal["comment"] = "comment"
    comment: str
