"""Job orchestration for the Bedrock Data Automation pipeline."""

from __future__ import annotations

import time
from typing import Any, Dict

from botocore.exceptions import ClientError

from .config import PipelineConfig

TERMINAL_STATES = {"SUCCEEDED", "FAILED", "STOPPED"}


class JobRunner:
    """Start and monitor document processing jobs."""

    def __init__(self, bda_client):
        self._client = bda_client

    def start_job(self, config: PipelineConfig, blueprint_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Start a document processing job and wait for completion."""

        job_request = self._build_job_request(config, blueprint_metadata)
        response = self._client.start_document_processing_job(**job_request)
        job = response.get("job", response)

        job_identifier = job.get("id") or job.get("jobId") or job.get("name")
        if not job_identifier:
            raise RuntimeError("Unable to determine job identifier from response: %s" % job)

        return self._wait_for_completion(job_identifier, poll_seconds=15)

    # ------------------------------------------------------------------
    def _build_job_request(
        self, config: PipelineConfig, blueprint_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        blueprint_id = (
            blueprint_metadata.get("id")
            or blueprint_metadata.get("blueprintId")
            or blueprint_metadata.get("name")
            or config.blueprint_name
        )
        request: Dict[str, Any] = {
            "blueprintIdentifier": blueprint_id,
            "inputDataConfig": {"s3Uri": config.input_s3_uri},
            "outputDataConfig": {
                "s3Uri": config.output_s3_uri,
                "format": "CSV",
            },
        }
        if config.job_name:
            request["name"] = config.job_name
        if config.job_tags:
            request["tags"] = [{"key": k, "value": v} for k, v in config.job_tags.items()]
        if config.role_arn:
            request["roleArn"] = config.role_arn
        return request

    def _wait_for_completion(self, job_identifier: str, poll_seconds: int) -> Dict[str, Any]:
        while True:
            response = self._client.get_document_processing_job(id=job_identifier)
            job = response.get("job", response)
            status = job.get("status")
            if status in TERMINAL_STATES:
                if status != "SUCCEEDED":
                    raise RuntimeError(f"Job {job_identifier} ended with status {status}")
                return job
            time.sleep(poll_seconds)

    def safe_stop(self, job_identifier: str) -> None:
        """Attempt to stop a running job."""

        try:
            self._client.stop_document_processing_job(id=job_identifier)
        except ClientError as exc:  # pragma: no cover - network dependent
            error = exc.response["Error"]
            if error.get("Code") not in {"ConflictException", "ValidationException"}:
                raise
