#!/usr/bin/env python3
"""
Create or update AWS Bedrock Data Automation Blueprint
"""

import json
import sys
import argparse
import yaml
from pathlib import Path
from botocore.exceptions import ClientError
from utils import setup_logging, get_aws_clients, validate_config


def load_blueprint_schema(schema_file: str) -> dict:
    """Load blueprint schema from JSON file"""
    with open(schema_file, 'r') as f:
        return json.load(f)


def create_blueprint(client, blueprint_config: dict, schema: dict, logger):
    """Create a new BDA blueprint"""
    blueprint_name = blueprint_config['name']
    logger.info(f"Creating blueprint: {blueprint_name}")

    try:
        # Prepare the schema for BDA API
        # BDA expects a specific schema format
        bda_schema = {
            'documentStandardExtraction': {
                'granularity': {
                    'types': ['DOCUMENT']
                }
            },
            'documentOutputFormat': {
                'customOutputTypes': []
            }
        }

        # Add custom fields to schema
        for field in schema.get('fields', []):
            custom_field = {
                'name': field['fieldName'],
                'description': field['fieldDescription'],
                'type': field['fieldType']
            }
            bda_schema['documentOutputFormat']['customOutputTypes'].append(custom_field)

        # Add extraction instructions as context
        if 'extractionInstructions' in schema:
            bda_schema['documentStandardExtraction']['extractionInstructions'] = schema['extractionInstructions']

        response = client.create_blueprint(
            blueprintName=blueprint_name,
            type='DOCUMENT',
            blueprintStage=blueprint_config.get('stage', 'LIVE'),
            schema=json.dumps(bda_schema)
        )

        logger.info(f"Blueprint created successfully")
        logger.info(f"Blueprint ARN: {response['blueprint']['blueprintArn']}")
        logger.info(f"Blueprint Version: {response['blueprint']['blueprintVersion']}")

        return response['blueprint']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceAlreadyExistsException':
            logger.warning(f"Blueprint {blueprint_name} already exists")
            # Try to get existing blueprint
            try:
                response = client.get_blueprint(blueprintName=blueprint_name)
                logger.info(f"Using existing blueprint: {response['blueprint']['blueprintArn']}")
                return response['blueprint']
            except ClientError as get_error:
                logger.error(f"Could not retrieve existing blueprint: {get_error}")
                raise
        else:
            logger.error(f"Error creating blueprint: {e}")
            raise


def update_blueprint(client, blueprint_name: str, schema: dict, logger):
    """Update an existing blueprint by creating a new version"""
    logger.info(f"Updating blueprint: {blueprint_name}")

    try:
        # First, get the current blueprint
        get_response = client.get_blueprint(blueprintName=blueprint_name)
        current_blueprint = get_response['blueprint']

        logger.info(f"Current blueprint version: {current_blueprint['blueprintVersion']}")

        # Prepare the updated schema
        bda_schema = {
            'documentStandardExtraction': {
                'granularity': {
                    'types': ['DOCUMENT']
                }
            },
            'documentOutputFormat': {
                'customOutputTypes': []
            }
        }

        # Add custom fields to schema
        for field in schema.get('fields', []):
            custom_field = {
                'name': field['fieldName'],
                'description': field['fieldDescription'],
                'type': field['fieldType']
            }
            bda_schema['documentOutputFormat']['customOutputTypes'].append(custom_field)

        # Add extraction instructions
        if 'extractionInstructions' in schema:
            bda_schema['documentStandardExtraction']['extractionInstructions'] = schema['extractionInstructions']

        # Create new blueprint version
        response = client.create_blueprint_version(
            blueprintArn=current_blueprint['blueprintArn'],
            schema=json.dumps(bda_schema)
        )

        logger.info(f"Blueprint updated successfully")
        logger.info(f"New version: {response['blueprint']['blueprintVersion']}")

        return response['blueprint']

    except ClientError as e:
        logger.error(f"Error updating blueprint: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Create or update AWS Bedrock Data Automation Blueprint'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing blueprint instead of creating new one'
    )
    parser.add_argument(
        '--schema',
        help='Path to blueprint schema file (overrides config)'
    )

    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Validate configuration
    validate_config(config)

    # Setup logging
    logger = setup_logging(config)
    logger.info("Starting blueprint creation/update process")

    # Load blueprint schema
    schema_file = args.schema or config['blueprint'].get('schema_file', 'blueprint_schema.json')
    logger.info(f"Loading blueprint schema from: {schema_file}")
    schema = load_blueprint_schema(schema_file)

    # Initialize AWS clients
    logger.info(f"Initializing AWS clients in region: {config['aws']['region']}")
    clients = get_aws_clients(
        region=config['aws']['region'],
        profile=config['aws'].get('profile')
    )
    bda_client = clients['bedrock_data_automation']

    # Create or update blueprint
    try:
        if args.update:
            blueprint = update_blueprint(
                bda_client,
                config['blueprint']['name'],
                schema,
                logger
            )
        else:
            blueprint = create_blueprint(
                bda_client,
                config['blueprint'],
                schema,
                logger
            )

        # Save blueprint info to file
        blueprint_info = {
            'blueprintArn': blueprint['blueprintArn'],
            'blueprintName': blueprint.get('blueprintName'),
            'blueprintVersion': blueprint.get('blueprintVersion'),
            'blueprintStage': blueprint.get('blueprintStage'),
            'createdAt': blueprint.get('createdAt').isoformat() if blueprint.get('createdAt') else None
        }

        output_file = 'blueprint_info.json'
        with open(output_file, 'w') as f:
            json.dump(blueprint_info, f, indent=2)

        logger.info(f"Blueprint information saved to: {output_file}")
        logger.info("Blueprint setup completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"Blueprint setup failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
