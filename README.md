# AWS_BDA

AWS Bedrock Data Automation (BDA) intelligent document processing pipeline.

## Overview

This project provisions a reusable pipeline that extracts structured data from unstructured
insurance documents. It creates or updates a BDA blueprint covering the required fields,
launches a document processing job for all files in an input S3 bucket, and aggregates the
output into a CSV that conforms to the specified schema.

### Extracted Fields

The blueprint is configured to capture the following entities:

- `SiteOnForm`
- `NameOnForm`
- `LogoOnForm`
- `EmailOnForm`
- `PhoneOnForm`
- `AddressOnForm`
- `SignatureOnForm`
- `LOB`
- `State`
- `Language`

Each field follows the extraction and formatting rules described in the specification.

## Requirements

- Python 3.10+
- Access to AWS with permissions for:
  - Bedrock Data Automation blueprints and document processing jobs
  - S3 read permissions on the input bucket and write permissions on the output bucket
- `boto3` and `botocore` Python packages

## Usage

Install the package locally (editable installation recommended):

```bash
pip install -e .
```

Run the pipeline:

```bash
run-bda-pipeline \
  s3://input-bucket/path/to/documents \
  s3://output-bucket/path/for/results \
  ./output/results.csv \
  --blueprint-name idp-insurance-entity-blueprint \
  --region us-east-1
```

Optional parameters:

- `--job-name` – friendly name for the processing job
- `--role-arn` – IAM role ARN that BDA should assume for cross-account bucket access
- `--tags` – JSON object containing resource tags (e.g. `'{"Env":"Dev"}'`)

The CLI automatically provisions the blueprint (creating or updating as needed) and injects
the correct blueprint ARN into the document processing job request, so providing AWS
credentials is sufficient for most environments.

## Output

After the job succeeds, the script downloads all structured outputs from the configured S3
prefix, normalizes them, and writes a CSV file at the specified local path. The CSV columns
match the required field names exactly and cells are normalized to string values.

## Development Notes

- Blueprint definitions are idempotent; running the script multiple times keeps the latest
  blueprint instructions in sync.
- The job runner polls every 15 seconds until the Bedrock Data Automation job reaches a
  terminal state.
- Result aggregation accepts either JSONL or JSON outputs from BDA and merges them into the
  final CSV.
