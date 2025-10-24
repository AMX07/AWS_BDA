#!/usr/bin/env python3
"""
Create AWS Bedrock Data Automation Project
"""

import json
import sys
import argparse
import yaml
from pathlib import Path
from botocore.exceptions import ClientError
from utils import setup_logging, get_aws_clients, validate_config


def create_data_automation_project(client, project_config: dict,
                                   blueprint_arn: str, logger):
    """Create a new BDA project"""
    project_name = project_config['name']
    logger.info(f"Creating Data Automation Project: {project_name}")

    try:
        response = client.create_data_automation_project(
            projectName=project_name,
            projectDescription=project_config.get('description', ''),
            projectStage='LIVE',
            standardOutputConfiguration={
                'document': {
                    'extraction': {
                        'granularity': {
                            'types': ['DOCUMENT']
                        },
                        'boundingBox': {
                            'state': 'ENABLED'
                        }
                    },
                    'outputFormat': {
                        'types': ['CSV', 'JSON']
                    }
                }
            },
            customOutputConfiguration={
                'blueprints': [
                    {
                        'blueprintArn': blueprint_arn
                    }
                ]
            }
        )

        logger.info(f"Project created successfully")
        logger.info(f"Project ARN: {response['projectArn']}")

        return response

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceAlreadyExistsException':
            logger.warning(f"Project {project_name} already exists")
            # Try to get existing project
            try:
                response = client.get_data_automation_project(projectName=project_name)
                logger.info(f"Using existing project: {response['project']['projectArn']}")
                return response
            except ClientError as get_error:
                logger.error(f"Could not retrieve existing project: {get_error}")
                raise
        else:
            logger.error(f"Error creating project: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description='Create AWS Bedrock Data Automation Project'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--blueprint-info',
        default='blueprint_info.json',
        help='Path to blueprint info file (default: blueprint_info.json)'
    )

    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Validate configuration
    validate_config(config)

    # Setup logging
    logger = setup_logging(config)
    logger.info("Starting project creation process")

    # Load blueprint info
    logger.info(f"Loading blueprint information from: {args.blueprint_info}")
    try:
        with open(args.blueprint_info, 'r') as f:
            blueprint_info = json.load(f)
        blueprint_arn = blueprint_info['blueprintArn']
        logger.info(f"Using blueprint: {blueprint_arn}")
    except FileNotFoundError:
        logger.error(f"Blueprint info file not found: {args.blueprint_info}")
        logger.error("Please run create_blueprint.py first")
        return 1
    except KeyError:
        logger.error("Invalid blueprint info file format")
        return 1

    # Initialize AWS clients
    logger.info(f"Initializing AWS clients in region: {config['aws']['region']}")
    clients = get_aws_clients(
        region=config['aws']['region'],
        profile=config['aws'].get('profile')
    )
    bda_client = clients['bedrock_data_automation']

    # Create project
    try:
        response = create_data_automation_project(
            bda_client,
            config['project'],
            blueprint_arn,
            logger
        )

        # Save project info to file
        project_info = {
            'projectArn': response.get('projectArn') or response['project']['projectArn'],
            'projectName': config['project']['name'],
            'blueprintArn': blueprint_arn
        }

        output_file = 'project_info.json'
        with open(output_file, 'w') as f:
            json.dump(project_info, f, indent=2)

        logger.info(f"Project information saved to: {output_file}")
        logger.info("Project setup completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"Project setup failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
