"""BambooHR async HTTP client."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import backoff
import httpx
import orjson
import yaml

from .exceptions import raise_for_status
from .models import (
    AddCommentRequest,
    ApplicationComment,
    ApplicationDetail,
    ApplicationsListResponse,
    ApplicationStatusGroup,
    ApplicationSummary,
)

logger = logging.getLogger(__name__)


def get_file_extension(data: bytes) -> str:
    """Detect file extension by magic bytes.

    Args:
        data: Raw file bytes.

    Returns:
        Detected extension (pdf, docx, txt, rtf, or bin).
    """
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:2] == b"PK":
        return "docx"
    if data[:5] == b"{\\rtf":
        return "rtf"
    try:
        data.decode("utf-8")
        return "txt"
    except UnicodeDecodeError:
        return "bin"


class BambooHRClient:
    """Async client for the BambooHR ATS API.

    Args:
        company_domain: Your BambooHR subdomain (e.g. "acme" for acme.bamboohr.com).
        api_key: BambooHR API key used as HTTP Basic Auth username.
    """

    def __init__(self, company_domain: str, api_key: str, session_cookie: str | None = None) -> None:
        self._base_url = f"https://{company_domain}.bamboohr.com"
        self._session_cookie = session_cookie
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=httpx.BasicAuth(api_key, "x"),
            headers={"Accept": "application/json"},
            timeout=30.0,
        )

    async def __aenter__(self) -> BambooHRClient:
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Context manager exit."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @backoff.on_exception(backoff.expo, httpx.TransportError, max_tries=3)
    async def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        """GET request with retry on transient errors.

        Args:
            path: URL path relative to base URL.
            **kwargs: Additional arguments forwarded to httpx.

        Returns:
            The httpx response.
        """
        logger.debug("GET %s %s", path, kwargs)
        response = await self._client.get(path, **kwargs)
        raise_for_status(response)
        return response

    @backoff.on_exception(backoff.expo, httpx.TransportError, max_tries=3)
    async def _post_json(self, path: str, body: object) -> httpx.Response:
        """POST JSON body with retry on transient errors.

        Args:
            path: URL path relative to base URL.
            body: JSON-serialisable object.

        Returns:
            The httpx response.
        """
        logger.debug("POST %s", path)
        response = await self._client.post(
            path,
            content=orjson.dumps(body),
            headers={"Content-Type": "application/json"},
        )
        raise_for_status(response)
        return response

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_applications(
        self,
        job_id: int | None = None,
        status_groups: str | ApplicationStatusGroup | list[str | ApplicationStatusGroup] = ApplicationStatusGroup.ALL,
        page: int | None = None,
    ) -> ApplicationsListResponse:
        """List ATS applications with optional filters.

        Args:
            job_id: Filter by BambooHR job opening ID.
            status_groups: Comma-separated status groups (e.g. "ALL", "active").
            page: Page number for pagination (1-based).

        Returns:
            Paginated list of application summaries.
        """
        if isinstance(status_groups, (str, ApplicationStatusGroup)):
            status_groups_str = str(status_groups)
        else:
            status_groups_str = ",".join(str(s) for s in status_groups)

        params: dict[str, object] = {"statusGroups": status_groups_str}
        if job_id is not None:
            params["jobId"] = job_id
        if page is not None:
            params["page"] = page

        response = await self._get("/api/v1/applicant_tracking/applications", params=params)
        data = orjson.loads(response.content)
        return ApplicationsListResponse.model_validate(data)

    async def get_application(self, application_id: int) -> ApplicationDetail:
        """Fetch full detail for a single application.

        Args:
            application_id: BambooHR application ID.

        Returns:
            Full application detail including resumeFileId.
        """
        response = await self._get(f"/api/v1/applicant_tracking/applications/{application_id}")
        data = orjson.loads(response.content)
        return ApplicationDetail.model_validate(data)

    async def download_file(self, file_id: int) -> bytes:
        """Download a file by its BambooHR file ID.

        Args:
            file_id: BambooHR file ID (e.g. from ApplicationDetail.resumeFileId).

        Returns:
            Raw file bytes (PDF, DOCX, etc.).

        Raises:
            ValueError: If session_cookie is missing or download fails.
        """
        if not self._session_cookie:
            raise ValueError(
                "Session cookie is required to download ATS files. "
                "BambooHR does not provide an API endpoint for downloading these files, "
                "so a valid session cookie must be provided to the client."
            )

        url = "/files/download.php"
        params = {"id": str(file_id)}
        headers = {
            "Cookie": self._session_cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        }
        # We use a separate client or bypass the default auth for this request
        # because the .php endpoint doesn't like Basic Auth + Cookie usually,
        # and it's not under /api/v1/
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            response = await client.get(url, params=params, headers=headers, follow_redirects=True)
            if response.status_code == 200 and "login" not in str(response.url).lower():
                return response.content

            raise ValueError(
                f"Pragmatic download failed for file {file_id} (status {response.status_code}). "
                "The session cookie might be invalid or expired."
            )

    async def add_application_comment(self, application_id: int, comment: str) -> None:
        """Add a comment to an application.

        Args:
            application_id: BambooHR application ID.
            comment: Comment text to post.
        """
        body = AddCommentRequest(comment=comment)
        await self._post_json(
            f"/api/v1/applicant_tracking/applications/{application_id}/comments",
            body.model_dump(),
        )

    async def get_application_comments(self, application_id: int) -> list[ApplicationComment]:
        """Fetch all comments for a single application.

        Args:
            application_id: BambooHR application ID.

        Returns:
            List of application comments.
        """
        response = await self._get(f"/api/v1/applicant_tracking/applications/{application_id}/comments")
        data = orjson.loads(response.content)
        return [ApplicationComment.model_validate(c) for c in data]

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    async def get_all_applications(
        self,
        job_id: int | None = None,
        rating_min: float | None = None,
        status_groups: str | ApplicationStatusGroup | list[str | ApplicationStatusGroup] = ApplicationStatusGroup.ALL,
        status_labels: list[str] | None = None,
    ) -> list[ApplicationSummary]:
        """Fetch all applications across all pages, optionally filtered by rating or status labels.

        Args:
            job_id: Filter by BambooHR job opening ID.
            rating_min: Minimum rating to include (inclusive).
            status_groups: Comma-separated status groups (e.g. "ALL", "active").
            status_labels: List of status labels to filter by (e.g. ["Manager should check CV"]).

        Returns:
            Flat list of ApplicationSummary objects.
        """
        all_apps: list[ApplicationSummary] = []
        page = 1
        while True:
            result = await self.get_applications(job_id=job_id, status_groups=status_groups, page=page)
            apps = result.applications
            if rating_min is not None:
                apps = [a for a in apps if (a.rating or 0) >= rating_min]

            if status_labels is not None:
                apps = [a for a in apps if a.status.label in status_labels]

            all_apps.extend(apps)

            if result.paginationComplete or not result.nextPageUrl:
                break
            page += 1
        return all_apps

    async def download_resume(self, application_id: int) -> bytes | None:
        """High-level helper to download the resume for an application.

        Args:
            application_id: BambooHR application ID.

        Returns:
            Raw file bytes if resume exists, else None.
        """
        detail = await self.get_application(application_id)
        if not detail.resumeFileId:
            return None
        return await self.download_file(detail.resumeFileId)

    async def fetch_candidates_pipeline(
        self,
        output_base: str | Path,
        job_ids: int | list[int] | None = None,
        rating_min: float | None = None,
        status_groups: str | ApplicationStatusGroup | list[str | ApplicationStatusGroup] = ApplicationStatusGroup.ALL,
        status_labels: list[str] | None = None,
        skip_existing: bool = True,
    ) -> dict[str, int]:
        """Convenience function to implement the candidate data pipeline for one or more jobs.

        This implements Milestone 2 & 3 of the PRD:
        1. Fetches applications matching criteria for all specified jobs.
        2. Creates a hierarchical directory structure:
           jobs/{Job Title} ({Job ID})/{Applicant Name} ({Application ID})/
        3. Saves application.yaml (Agent Context).
        4. Downloads and saves all attachments into a raw/ subfolder.

        Args:
            output_base: Base directory for output.
            job_ids: Filter by one or more BambooHR job opening IDs. If None, fetches all.
            rating_min: Minimum rating to include.
            status_groups: Comma-separated status groups.
            status_labels: List of status labels to filter by.
            skip_existing: If True, skip candidates that already have application.yaml.

        Returns:
            Summary dict with 'processed', 'skipped', and 'errors' counts.
        """
        output_base = Path(output_base)
        stats = {"processed": 0, "skipped": 0, "errors": 0}

        # Normalize job_ids to a list
        if job_ids is None:
            job_list = [None]
        elif isinstance(job_ids, int):
            job_list = [job_ids]
        else:
            job_list = job_ids

        all_applications = []
        for jid in job_list:
            logger.info(
                "Fetching applications (job_id=%s, rating_min=%s, status_labels=%s)...",
                jid,
                rating_min,
                status_labels,
            )
            apps = await self.get_all_applications(
                job_id=jid,
                rating_min=rating_min,
                status_groups=status_groups,
                status_labels=status_labels,
            )
            all_applications.extend(apps)

        for app_summary in all_applications:
            try:
                # 1. Prepare directory structure
                job_title = (
                    app_summary.job.title if isinstance(app_summary.job.title, str) else app_summary.job.title.label
                )
                job_dir_name = f"{job_title} ({app_summary.job.id})"
                applicant_name = f"{app_summary.applicant.firstName} {app_summary.applicant.lastName}"
                app_dir_name = f"{applicant_name} ({app_summary.id})"

                app_dir = output_base / "jobs" / job_dir_name / app_dir_name
                yaml_path = app_dir / "application.yaml"
                raw_dir = app_dir / "raw"

                # 2. Idempotency check
                if skip_existing and yaml_path.exists():
                    logger.info("Skipping existing candidate: %s", app_dir_name)
                    stats["skipped"] += 1
                    continue

                # 3. Fetch full detail
                detail = await self.get_application(app_summary.id)

                # 4. Create directories
                app_dir.mkdir(parents=True, exist_ok=True)
                raw_dir.mkdir(parents=True, exist_ok=True)

                # 5. Save application.yaml (Agent Context)
                # Strip out noisy fields like avatar
                data = detail.model_dump()
                if "applicant" in data and "avatar" in data["applicant"]:
                    data["applicant"]["avatar"] = None
                if "job" in data and "hiringLead" in data["job"] and data["job"]["hiringLead"]:
                    data["job"]["hiringLead"]["avatar"] = None

                yaml_content = yaml.dump(data, sort_keys=False, allow_unicode=True)
                yaml_path.write_text(yaml_content, encoding="utf-8")

                # 6. Download attachments (resume, cover letter, and extra attachments)
                file_tasks = []
                if detail.resumeFileId:
                    file_tasks.append(("resume", detail.resumeFileId))
                if detail.coverLetterFileId:
                    file_tasks.append(("cover_letter", detail.coverLetterFileId))
                if detail.attachments:
                    for attachment in detail.attachments:
                        if "id" in attachment:
                            # Use original filename if available, otherwise fallback to 'attachment_{id}'
                            name_hint = attachment.get("fileName", f"attachment_{attachment['id']}")
                            file_tasks.append((name_hint, attachment["id"]))

                for filename_base, file_id in file_tasks:
                    try:
                        file_bytes = await self.download_file(file_id)
                        ext = get_file_extension(file_bytes)
                        # If filename_base already has an extension that matches or is common, use it
                        # but for resume/cover_letter we prefer our detected extension
                        if filename_base in ("resume", "cover_letter"):
                            final_filename = f"{filename_base}.{ext}"
                        else:
                            # For other attachments, try to preserve name but ensure extension
                            if "." in filename_base:
                                final_filename = filename_base
                            else:
                                final_filename = f"{filename_base}.{ext}"

                        (raw_dir / final_filename).write_bytes(file_bytes)
                    except Exception as e:
                        logger.warning("Failed to download file %s (ID %s): %s", filename_base, file_id, e)

                logger.info("Processed: %s", app_dir_name)
                stats["processed"] += 1

            except Exception as e:
                logger.error("Failed to process application %s: %s", app_summary.id, e, exc_info=True)
                stats["errors"] += 1

        return stats
