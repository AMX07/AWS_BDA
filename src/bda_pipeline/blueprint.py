"""Blueprint management helpers for AWS Bedrock Data Automation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional

from botocore.exceptions import ClientError

from .config import BlueprintField, PipelineConfig


class BlueprintManager:
    """Create or update a blueprint that instructs BDA how to extract data."""

    def __init__(self, bda_client):
        self._client = bda_client

    def ensure_blueprint(self, config: PipelineConfig) -> Dict[str, Any]:
        """Return blueprint metadata, creating or updating as needed."""

        blueprint_payload = self._build_blueprint_payload(config.ensure_field_definitions())
        existing = self._get_blueprint(config.blueprint_name)

        if existing is None:
            response = self._client.create_blueprint(
                name=config.blueprint_name,
                displayName=config.blueprint_name,
                description=config.blueprint_description,
                blueprint=json.dumps(blueprint_payload),
            )
            return response.get("blueprint", response)

        if not self._blueprint_matches(existing, blueprint_payload):
            response = self._client.update_blueprint(
                name=config.blueprint_name,
                description=config.blueprint_description,
                blueprint=json.dumps(blueprint_payload),
            )
            return response.get("blueprint", response)

        return existing

    # ------------------------------------------------------------------
    def _get_blueprint(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            response = self._client.get_blueprint(name=name)
            return response.get("blueprint", response)
        except ClientError as exc:  # pragma: no cover - depends on AWS state
            error = exc.response["Error"]
            if error.get("Code") in {"ResourceNotFoundException", "NotFoundException"}:
                return None
            raise

    def _blueprint_matches(self, metadata: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        existing_document = metadata.get("blueprint")
        if isinstance(existing_document, str):
            try:
                existing_document = json.loads(existing_document)
            except json.JSONDecodeError:
                return False
        return existing_document == payload

    def _build_blueprint_payload(self, fields: Iterable[BlueprintField]) -> Dict[str, Any]:
        extractions = [field.to_blueprint() for field in fields]
        return {
            "version": "2024-06-01",
            "task": "DOCUMENT_ENTITY_EXTRACTION",
            "documentGroups": [
                {
                    "identifier": "default",
                    "extractions": extractions,
                }
            ],
            "output": {
                "format": "CSV",
                "fieldOrder": [field.name for field in fields],
            },
        }
