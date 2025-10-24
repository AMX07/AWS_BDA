"""
Utility functions for AWS Bedrock Data Automation pipeline
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """Setup logging configuration"""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))

    # Create logger
    logger = logging.getLogger('BDA_Pipeline')
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers = []

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if log_config.get('console_output', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_config.get('log_file'):
        file_handler = logging.FileHandler(log_config['log_file'])
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_aws_clients(region: str, profile: Optional[str] = None) -> Dict[str, Any]:
    """Initialize AWS clients"""
    session_kwargs = {'region_name': region}
    if profile and profile != 'default':
        session_kwargs['profile_name'] = profile

    session = boto3.Session(**session_kwargs)

    return {
        'bedrock_data_automation': session.client('bedrock-data-automation'),
        'bedrock_data_automation_runtime': session.client('bedrock-data-automation-runtime'),
        's3': session.client('s3')
    }


def list_s3_documents(s3_client: Any, bucket: str, prefix: str,
                     supported_formats: List[str], logger: logging.Logger) -> List[str]:
    """List all supported documents in S3 bucket"""
    logger.info(f"Listing documents in s3://{bucket}/{prefix}")

    documents = []
    paginator = s3_client.get_paginator('list_objects_v2')

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                # Check if file has supported extension
                extension = key.split('.')[-1].lower()
                if extension in supported_formats:
                    documents.append(key)

        logger.info(f"Found {len(documents)} documents to process")
        return documents

    except ClientError as e:
        logger.error(f"Error listing S3 objects: {e}")
        raise


def parse_s3_uri(uri: str) -> tuple:
    """Parse S3 URI into bucket and prefix"""
    if uri.startswith('s3://'):
        uri = uri[5:]
    parts = uri.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    return bucket, prefix


def generate_output_filename(base_name: str, include_timestamp: bool = True) -> str:
    """Generate output filename with optional timestamp"""
    if include_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name_parts = base_name.rsplit('.', 1)
        if len(name_parts) == 2:
            return f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
        else:
            return f"{base_name}_{timestamp}"
    return base_name


def wait_for_job_completion(client: Any, invocation_arn: str,
                            poll_interval: int, timeout: int,
                            logger: logging.Logger) -> Dict[str, Any]:
    """Poll for job completion with timeout"""
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.error(f"Job {invocation_arn} timed out after {timeout} seconds")
            raise TimeoutError(f"Job processing exceeded timeout of {timeout} seconds")

        try:
            response = client.get_data_automation_status(invocationArn=invocation_arn)
            status = response.get('status')

            if status == 'SUCCESS':
                logger.debug(f"Job {invocation_arn} completed successfully")
                return response
            elif status == 'FAILED':
                error_msg = response.get('error', 'Unknown error')
                logger.error(f"Job {invocation_arn} failed: {error_msg}")
                raise RuntimeError(f"Job failed: {error_msg}")
            elif status in ['IN_PROGRESS', 'PENDING']:
                logger.debug(f"Job {invocation_arn} status: {status}, waiting...")
                time.sleep(poll_interval)
            else:
                logger.warning(f"Job {invocation_arn} has unknown status: {status}")
                time.sleep(poll_interval)

        except ClientError as e:
            logger.error(f"Error checking job status: {e}")
            time.sleep(poll_interval)


def extract_results_from_response(response: Dict[str, Any], document_key: str,
                                  logger: logging.Logger) -> Dict[str, Any]:
    """Extract and format results from BDA response"""
    try:
        # Initialize result with document identifier
        result = {
            'document': document_key,
            'processing_status': 'success'
        }

        # Extract output location if present
        if 'outputConfiguration' in response:
            output_config = response['outputConfiguration']
            if 's3Uri' in output_config:
                result['output_s3_uri'] = output_config['s3Uri']

        # Extract the actual field values from the response
        # The exact structure depends on BDA's response format
        if 'output' in response:
            output_data = response['output']

            # If output is a string containing JSON, parse it
            if isinstance(output_data, str):
                try:
                    output_data = json.loads(output_data)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse output as JSON for {document_key}")

            # Extract each field
            for field in ['SiteOnForm', 'NameOnForm', 'LogoOnForm', 'EmailOnForm',
                         'PhoneOnForm', 'AddressOnForm', 'SignatureOnForm',
                         'LOB', 'State', 'Language']:
                result[field] = output_data.get(field, '')

        return result

    except Exception as e:
        logger.error(f"Error extracting results for {document_key}: {e}")
        return {
            'document': document_key,
            'processing_status': 'error',
            'error_message': str(e)
        }


def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration has required fields"""
    required_sections = ['aws', 'blueprint', 'project', 's3', 'processing']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # Validate AWS region
    region = config['aws'].get('region')
    if not region:
        raise ValueError("AWS region not specified in configuration")

    # Validate blueprint name
    if not config['blueprint'].get('name'):
        raise ValueError("Blueprint name not specified in configuration")

    # Validate project name
    if not config['project'].get('name'):
        raise ValueError("Project name not specified in configuration")


def retry_with_backoff(func, max_retries: int, delay: int, logger: logging.Logger, *args, **kwargs):
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts: {e}")
                raise
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
