"""Command line entry point for the AWS Bedrock Data Automation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .blueprint import BlueprintManager
from .config import PipelineConfig, default_field_definitions
from .job import JobRunner
from .output import ResultAggregator


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_s3_uri", help="S3 URI containing the source documents")
    parser.add_argument("output_s3_uri", help="S3 URI where BDA should store structured output")
    parser.add_argument(
        "output_csv_path", help="Local filesystem path where the aggregated CSV should be saved"
    )
    parser.add_argument(
        "--blueprint-name",
        default="idp-insurance-entity-blueprint",
        help="Name of the Bedrock Data Automation blueprint",
    )
    parser.add_argument("--job-name", help="Optional job name override")
    parser.add_argument(
        "--region", default="us-east-1", help="AWS region hosting the BDA resources"
    )
    parser.add_argument(
        "--role-arn",
        help="IAM role ARN that the BDA job should assume for accessing the S3 buckets",
    )
    parser.add_argument(
        "--tags",
        help="JSON object of key/value tags to apply to the job (e.g. '{\"Project\":\"IDP\"}')",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    tags = None
    if args.tags:
        tags = json.loads(args.tags)

    config = PipelineConfig(
        blueprint_name=args.blueprint_name,
        input_s3_uri=args.input_s3_uri,
        output_s3_uri=args.output_s3_uri,
        output_csv_path=args.output_csv_path,
        region_name=args.region,
        role_arn=args.role_arn,
        job_name=args.job_name,
        job_tags=tags,
        field_definitions=default_field_definitions(),
    )

    session = boto3.Session(region_name=config.region_name)
    bda_client = session.client("bedrock-data-automation")
    s3_client = session.client("s3")

    blueprint_manager = BlueprintManager(bda_client)
    job_runner = JobRunner(bda_client)
    result_aggregator = ResultAggregator(s3_client)

    try:
        blueprint_metadata = blueprint_manager.ensure_blueprint(config)
        job_metadata = job_runner.start_job(config, blueprint_metadata)
        result_aggregator.build_csv(
            output_s3_uri=config.output_s3_uri,
            csv_path=config.output_csv_path,
            fieldnames=[field.name for field in config.ensure_field_definitions()],
        )
    except (BotoCoreError, ClientError, RuntimeError, ValueError) as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    print("Pipeline completed successfully.")
    print(f"Blueprint: {blueprint_metadata.get('name', config.blueprint_name)}")
    print(f"Job status: {job_metadata.get('status')}")
    print(f"CSV generated at: {config.output_csv_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
