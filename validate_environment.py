#!/usr/bin/env python3
"""
Validate environment and prerequisites for AWS BDA Pipeline
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check Python version"""
    print("1. Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False


def check_virtual_env():
    """Check if virtual environment exists"""
    print("\n2. Checking virtual environment...")
    if Path("venv").exists():
        print("   ✓ Virtual environment exists")

        # Check if activated
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("   ✓ Virtual environment is activated")
            return True
        else:
            print("   ⚠ Virtual environment exists but not activated")
            print("     Run: source venv/bin/activate")
            return False
    else:
        print("   ✗ Virtual environment not found")
        print("     Run: ./setup.sh")
        return False


def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n3. Checking Python dependencies...")
    required = ['boto3', 'botocore', 'yaml', 'pandas', 'tqdm']
    all_installed = True

    for package in required:
        try:
            if package == 'yaml':
                __import__('yaml')
            else:
                __import__(package)
            print(f"   ✓ {package} installed")
        except ImportError:
            print(f"   ✗ {package} not installed")
            all_installed = False

    if not all_installed:
        print("     Run: pip install -r requirements.txt")

    return all_installed


def check_aws_credentials():
    """Check AWS credentials configuration"""
    print("\n4. Checking AWS credentials...")

    # Check environment variables
    has_env_creds = all([
        os.environ.get('AWS_ACCESS_KEY_ID'),
        os.environ.get('AWS_SECRET_ACCESS_KEY')
    ])

    # Check AWS CLI config
    aws_config = Path.home() / '.aws' / 'credentials'
    has_cli_creds = aws_config.exists()

    if has_env_creds:
        print("   ✓ AWS credentials found in environment variables")
        return True
    elif has_cli_creds:
        print("   ✓ AWS credentials found in ~/.aws/credentials")
        return True
    else:
        print("   ✗ No AWS credentials found")
        print("     Run: aws configure")
        print("     Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        return False


def check_aws_cli():
    """Check if AWS CLI is installed"""
    print("\n5. Checking AWS CLI...")
    try:
        result = subprocess.run(['aws', '--version'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            print(f"   ✓ AWS CLI installed: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("   ⚠ AWS CLI not found (optional but recommended)")
    print("     Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html")
    return True  # Not critical


def check_boto3_bda_client():
    """Check if boto3 can create BDA clients"""
    print("\n6. Checking boto3 BDA client availability...")

    try:
        import boto3

        # Try to create clients (without actually calling AWS)
        try:
            session = boto3.Session(region_name='us-east-1')
            client = session.client('bedrock-data-automation')
            print("   ✓ bedrock-data-automation client available")
        except Exception as e:
            print(f"   ✗ bedrock-data-automation client error: {e}")
            return False

        try:
            runtime_client = session.client('bedrock-data-automation-runtime')
            print("   ✓ bedrock-data-automation-runtime client available")
        except Exception as e:
            print(f"   ✗ bedrock-data-automation-runtime client error: {e}")
            return False

        return True
    except ImportError:
        print("   ✗ boto3 not installed")
        return False


def check_config_files():
    """Check if required configuration files exist"""
    print("\n7. Checking configuration files...")

    required_files = {
        'config.yaml': 'Main configuration',
        'blueprint_schema.json': 'Blueprint schema',
        'requirements.txt': 'Python dependencies',
        'create_blueprint.py': 'Blueprint creator',
        'create_project.py': 'Project creator',
        'process_documents.py': 'Document processor',
        'utils.py': 'Utility functions'
    }

    all_exist = True
    for file, description in required_files.items():
        if Path(file).exists():
            print(f"   ✓ {file} ({description})")
        else:
            print(f"   ✗ {file} missing ({description})")
            all_exist = False

    return all_exist


def check_aws_region():
    """Check if AWS region is set to a BDA-supported region"""
    print("\n8. Checking AWS region configuration...")

    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        region = config.get('aws', {}).get('region')
        if region in ['us-east-1', 'us-west-2']:
            print(f"   ✓ Region {region} (BDA is available)")
            return True
        else:
            print(f"   ✗ Region {region} (BDA only available in us-east-1 or us-west-2)")
            print("     Update config.yaml to use us-east-1 or us-west-2")
            return False
    except Exception as e:
        print(f"   ⚠ Could not check region: {e}")
        return False


def main():
    print("=" * 70)
    print("AWS BEDROCK DATA AUTOMATION PIPELINE - ENVIRONMENT VALIDATION")
    print("=" * 70)
    print()

    checks = [
        check_python_version(),
        check_virtual_env(),
        check_dependencies(),
        check_aws_credentials(),
        check_aws_cli(),
        check_config_files(),
        check_aws_region(),
        check_boto3_bda_client()
    ]

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(checks)
    total = len(checks)

    if passed == total:
        print(f"✓ All checks passed ({passed}/{total})")
        print("\nYou're ready to run the pipeline!")
        print("\nNext steps:")
        print("  1. Ensure your AWS credentials have the required permissions")
        print("  2. Run: ./run_pipeline.sh --input-bucket <s3-uri> --output-bucket <s3-uri>")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed ({passed}/{total} passed)")
        print("\nPlease fix the issues above before running the pipeline.")
        print("\nQuick fix:")
        print("  1. Run: ./setup.sh")
        print("  2. Run: source venv/bin/activate")
        print("  3. Run: aws configure")
        print("  4. Run: python3 validate_environment.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())
