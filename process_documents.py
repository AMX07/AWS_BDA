#!/usr/bin/env python3
"""
Main document processing pipeline using AWS Bedrock Data Automation
Processes documents from S3, extracts data using BDA, and exports results to CSV
"""

import json
import sys
import argparse
import yaml
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError
from tqdm import tqdm
from utils import (
    setup_logging, get_aws_clients, validate_config,
    list_s3_documents, parse_s3_uri, generate_output_filename,
    wait_for_job_completion, extract_results_from_response,
    retry_with_backoff
)


def invoke_document_processing(runtime_client, project_arn: str,
                               s3_uri: str, logger) -> dict:
    """Invoke BDA processing for a single document"""
    logger.debug(f"Invoking processing for: {s3_uri}")

    try:
        response = runtime_client.invoke_data_automation_async(
            inputConfiguration={
                's3Uri': s3_uri
            },
            outputConfiguration={
                's3Uri': s3_uri.rsplit('/', 1)[0] + '/output/'
            },
            dataAutomationConfiguration={
                'dataAutomationArn': project_arn,
                'stage': 'LIVE'
            }
        )

        return {
            'invocationArn': response['invocationArn'],
            's3_uri': s3_uri,
            'status': 'submitted'
        }

    except ClientError as e:
        logger.error(f"Error invoking processing for {s3_uri}: {e}")
        return {
            's3_uri': s3_uri,
            'status': 'error',
            'error': str(e)
        }


def process_single_document(runtime_client, project_arn: str,
                           bucket: str, key: str, config: dict,
                           logger) -> dict:
    """Process a single document end-to-end"""
    s3_uri = f"s3://{bucket}/{key}"
    document_name = key.split('/')[-1]

    try:
        # Invoke processing
        logger.info(f"Processing: {document_name}")
        invocation = invoke_document_processing(
            runtime_client,
            project_arn,
            s3_uri,
            logger
        )

        if invocation['status'] == 'error':
            return {
                'document': document_name,
                's3_uri': s3_uri,
                'processing_status': 'error',
                'error_message': invocation['error']
            }

        # Wait for completion
        invocation_arn = invocation['invocationArn']
        logger.debug(f"Waiting for job completion: {invocation_arn}")

        result = wait_for_job_completion(
            runtime_client,
            invocation_arn,
            config['processing']['poll_interval'],
            config['processing']['timeout'],
            logger
        )

        # Extract results
        extracted_data = extract_results_from_response(result, document_name, logger)
        extracted_data['s3_uri'] = s3_uri

        logger.info(f"Successfully processed: {document_name}")
        return extracted_data

    except Exception as e:
        logger.error(f"Error processing {document_name}: {e}")
        return {
            'document': document_name,
            's3_uri': s3_uri,
            'processing_status': 'error',
            'error_message': str(e)
        }


def process_documents_batch(runtime_client, project_arn: str,
                            documents: list, bucket: str,
                            config: dict, logger) -> list:
    """Process a batch of documents in parallel"""
    results = []
    batch_size = config['processing']['batch_size']

    logger.info(f"Processing {len(documents)} documents in batches of {batch_size}")

    # Create progress bar
    with tqdm(total=len(documents), desc="Processing documents") as pbar:
        # Process in parallel batches
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all jobs
            future_to_doc = {
                executor.submit(
                    process_single_document,
                    runtime_client,
                    project_arn,
                    bucket,
                    doc_key,
                    config,
                    logger
                ): doc_key for doc_key in documents
            }

            # Collect results as they complete
            for future in as_completed(future_to_doc):
                doc_key = future_to_doc[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error processing {doc_key}: {e}")
                    results.append({
                        'document': doc_key.split('/')[-1],
                        's3_uri': f"s3://{bucket}/{doc_key}",
                        'processing_status': 'error',
                        'error_message': str(e)
                    })
                finally:
                    pbar.update(1)

    return results


def export_results_to_csv(results: list, output_file: str,
                          include_metadata: bool, logger):
    """Export processing results to CSV"""
    logger.info(f"Exporting {len(results)} results to CSV: {output_file}")

    # Define column order
    base_columns = [
        'document',
        'SiteOnForm',
        'NameOnForm',
        'LogoOnForm',
        'EmailOnForm',
        'PhoneOnForm',
        'AddressOnForm',
        'SignatureOnForm',
        'LOB',
        'State',
        'Language'
    ]

    metadata_columns = [
        's3_uri',
        'processing_status',
        'error_message',
        'output_s3_uri'
    ] if include_metadata else []

    # Create DataFrame
    df = pd.DataFrame(results)

    # Ensure all base columns exist
    for col in base_columns:
        if col not in df.columns:
            df[col] = ''

    # Reorder columns
    columns = base_columns + metadata_columns
    columns = [col for col in columns if col in df.columns]
    df = df[columns]

    # Fill NaN values with empty string
    df = df.fillna('')

    # Export to CSV
    df.to_csv(output_file, index=False)
    logger.info(f"Results exported successfully to: {output_file}")

    # Print summary statistics
    total_docs = len(results)
    successful = sum(1 for r in results if r.get('processing_status') == 'success')
    failed = total_docs - successful

    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total documents processed: {total_docs}")
    logger.info(f"Successful: {successful} ({successful/total_docs*100:.1f}%)")
    logger.info(f"Failed: {failed} ({failed/total_docs*100:.1f}%)")
    logger.info("=" * 60)


def upload_csv_to_s3(s3_client, local_file: str, bucket: str,
                     prefix: str, logger):
    """Upload CSV file to S3"""
    s3_key = f"{prefix.rstrip('/')}/{Path(local_file).name}"
    s3_uri = f"s3://{bucket}/{s3_key}"

    logger.info(f"Uploading results to: {s3_uri}")

    try:
        s3_client.upload_file(local_file, bucket, s3_key)
        logger.info("Upload completed successfully")
        return s3_uri
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Process documents using AWS Bedrock Data Automation'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--input-bucket',
        required=True,
        help='S3 URI or bucket name for input documents (e.g., s3://my-bucket/documents/ or my-bucket)'
    )
    parser.add_argument(
        '--output-bucket',
        required=True,
        help='S3 URI or bucket name for output CSV (e.g., s3://my-bucket/results/ or my-bucket)'
    )
    parser.add_argument(
        '--project-info',
        default='project_info.json',
        help='Path to project info file (default: project_info.json)'
    )
    parser.add_argument(
        '--output-file',
        help='Override output CSV filename'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List documents without processing'
    )

    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Validate configuration
    validate_config(config)

    # Setup logging
    logger = setup_logging(config)
    logger.info("=" * 60)
    logger.info("AWS BEDROCK DATA AUTOMATION - DOCUMENT PROCESSING PIPELINE")
    logger.info("=" * 60)

    # Parse S3 URIs
    input_bucket, input_prefix = parse_s3_uri(args.input_bucket)
    output_bucket, output_prefix = parse_s3_uri(args.output_bucket)

    # Override config with command-line arguments
    config['s3']['input_bucket'] = input_bucket
    config['s3']['input_prefix'] = input_prefix
    config['s3']['output_bucket'] = output_bucket
    if output_prefix:
        config['s3']['output_prefix'] = output_prefix

    logger.info(f"Input location: s3://{input_bucket}/{input_prefix}")
    logger.info(f"Output location: s3://{output_bucket}/{config['s3']['output_prefix']}")

    # Load project info
    logger.info(f"Loading project information from: {args.project_info}")
    try:
        with open(args.project_info, 'r') as f:
            project_info = json.load(f)
        project_arn = project_info['projectArn']
        logger.info(f"Using project: {project_arn}")
    except FileNotFoundError:
        logger.error(f"Project info file not found: {args.project_info}")
        logger.error("Please run create_project.py first")
        return 1
    except KeyError:
        logger.error("Invalid project info file format")
        return 1

    # Initialize AWS clients
    logger.info(f"Initializing AWS clients in region: {config['aws']['region']}")
    clients = get_aws_clients(
        region=config['aws']['region'],
        profile=config['aws'].get('profile')
    )

    # List documents in S3
    logger.info("Scanning S3 bucket for documents...")
    documents = list_s3_documents(
        clients['s3'],
        input_bucket,
        input_prefix,
        config['supported_formats'],
        logger
    )

    if not documents:
        logger.warning("No documents found to process")
        return 0

    if args.dry_run:
        logger.info("DRY RUN - Documents found:")
        for doc in documents:
            logger.info(f"  - {doc}")
        logger.info(f"Total: {len(documents)} documents")
        return 0

    # Process documents
    logger.info("Starting document processing...")
    start_time = time.time()

    results = process_documents_batch(
        clients['bedrock_data_automation_runtime'],
        project_arn,
        documents,
        input_bucket,
        config,
        logger
    )

    processing_time = time.time() - start_time
    logger.info(f"Processing completed in {processing_time:.2f} seconds")

    # Generate output filename
    output_filename = args.output_file or generate_output_filename(
        config['output']['csv_filename'],
        config['output']['include_timestamp']
    )

    # Export results to CSV
    export_results_to_csv(
        results,
        output_filename,
        config['output']['include_metadata'],
        logger
    )

    # Upload CSV to S3
    output_s3_uri = upload_csv_to_s3(
        clients['s3'],
        output_filename,
        output_bucket,
        config['s3']['output_prefix'],
        logger
    )

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info(f"Results available at: {output_s3_uri}")
    logger.info(f"Local copy: {output_filename}")
    logger.info("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
