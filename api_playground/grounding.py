import asyncio
import os
from pathlib import Path

import vcr
from dotenv import load_dotenv

from ss_utils_bamboohr import BambooHRClient

# Load environment variables
load_dotenv()

BAMBOOHR_API_KEY = os.environ.get("BAMBOOHR_API_KEY")
BAMBOOHR_COMPANY_DOMAIN = os.environ.get("BAMBOOHR_COMPANY_DOMAIN")
BAMBOOHR_JOB_ID = int(os.environ.get("BAMBOOHR_JOB_ID", "0")) or None

# Configure VCR
my_vcr = vcr.VCR(
    cassette_library_dir="api_playground/cassettes",
    record_mode="once",
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=["Authorization"],
)


async def ground_api():
    """Record real API responses to ground our models."""
    if not BAMBOOHR_API_KEY or not BAMBOOHR_COMPANY_DOMAIN:
        print("Error: BAMBOOHR_API_KEY and BAMBOOHR_COMPANY_DOMAIN must be set in .env")
        return

    async with BambooHRClient(company_domain=BAMBOOHR_COMPANY_DOMAIN, api_key=BAMBOOHR_API_KEY) as client:
        # 1. Ground get_applications
        print("Grounding get_applications...")
        with my_vcr.use_cassette("get_applications.yaml"):
            try:
                # We use raw request to see what's actually coming back before validation
                response = await client._client.get(
                    "/api/v1/applicant_tracking/applications",
                    params={"jobId": BAMBOOHR_JOB_ID} if BAMBOOHR_JOB_ID else {},
                )
                print(f"get_applications status: {response.status_code}")
                # Save raw JSON for inspection
                with open("api_playground/get_applications.json", "wb") as f:
                    f.write(response.content)
            except Exception as e:
                print(f"Error grounding get_applications: {e}")

        # 2. Ground get_application (detail)
        # We need an application ID. We'll try to get one from the previous response if possible,
        # or use a known one if provided.
        app_id = None
        try:
            data = response.json()
            if data.get("applications"):
                app_id = data["applications"][0]["id"]
        except Exception:
            pass

        if app_id:
            print(f"Grounding get_application for ID {app_id}...")
            with my_vcr.use_cassette("get_application_detail.yaml"):
                try:
                    response = await client._client.get(f"/api/v1/applicant_tracking/applications/{app_id}")
                    print(f"get_application status: {response.status_code}")
                    # Save raw JSON for inspection
                    with open("api_playground/get_application_detail.json", "wb") as f:
                        f.write(response.content)

                    # 3. Ground get_application_comments
                    print(f"Grounding get_application_comments for ID {app_id}...")
                    with my_vcr.use_cassette("get_application_comments.yaml"):
                        response_comments = await client._client.get(
                            f"/api/v1/applicant_tracking/applications/{app_id}/comments"
                        )
                        print(f"get_application_comments status: {response_comments.status_code}")
                        with open("api_playground/get_application_comments.json", "wb") as f:
                            f.write(response_comments.content)
                except Exception as e:
                    print(f"Error grounding get_application: {e}")
        else:
            print("No application ID found to ground get_application detail.")


if __name__ == "__main__":
    asyncio.run(ground_api())
