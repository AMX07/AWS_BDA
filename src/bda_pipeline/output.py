"""Utilities for compiling Bedrock Data Automation results into CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional


class ResultAggregator:
    """Download structured results from S3 and emit a normalized CSV."""

    def __init__(self, s3_client):
        self._s3 = s3_client

    def build_csv(self, output_s3_uri: str, csv_path: str, fieldnames: Iterable[str]) -> Path:
        records = list(self._iter_job_records(output_s3_uri))
        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow({field: record.get(field, "") for field in fieldnames})
        return output_path

    # ------------------------------------------------------------------
    def _iter_job_records(self, output_s3_uri: str) -> Iterator[Dict[str, str]]:
        bucket, prefix = _split_s3_uri(output_s3_uri)
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".jsonl"):
                    yield from self._load_json_lines(bucket, key)
                elif key.endswith(".json"):
                    document = self._load_json_object(bucket, key)
                    if isinstance(document, list):
                        for item in document:
                            if isinstance(item, dict):
                                yield _normalize_record(item)
                    elif isinstance(document, dict):
                        yield _normalize_record(document)

    def _load_json_lines(self, bucket: str, key: str) -> Iterator[Dict[str, str]]:
        response = self._s3.get_object(Bucket=bucket, Key=key)
        body = response["Body"].iter_lines()
        for line in body:
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            if isinstance(data, dict):
                yield _normalize_record(data)

    def _load_json_object(self, bucket: str, key: str):
        response = self._s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))


FIELD_JOIN_RULES = {
    "LogoOnForm": ",",
}


def _normalize_record(record: Dict[str, object]) -> Dict[str, str]:
    return {key: _normalize_value(value, key) for key, value in record.items()}


def _normalize_value(value: object, field_name: Optional[str] = None) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        joiner = FIELD_JOIN_RULES.get(field_name, ", ")
        normalized_items: List[str] = []
        for item in value:
            normalized = _normalize_value(item, field_name)
            if normalized:
                normalized_items.append(normalized)
        return joiner.join(normalized_items)
    return str(value)


def _split_s3_uri(uri: str) -> List[str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    without_scheme = uri[5:]
    parts = without_scheme.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return [bucket, prefix]
