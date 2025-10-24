# Troubleshooting Guide - AWS BDA Pipeline

## Quick Diagnostics

Before running the pipeline, validate your environment:

```bash
python3 validate_environment.py
```

This will check:
- Python version
- Virtual environment
- Python dependencies
- AWS credentials
- Configuration files
- AWS region
- Boto3 BDA client availability

## Common Errors and Solutions

### 1. Blueprint Creation Failed

#### Error: "No module named 'boto3'"

**Cause**: Dependencies not installed

**Solution**:
```bash
# Run the setup script
./setup.sh

# OR manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Error: "UnrecognizedClientException"

**Cause**: BDA service not available in your region

**Solution**: Update `config.yaml`:
```yaml
aws:
  region: us-east-1  # or us-west-2
```

BDA is **only** available in:
- `us-east-1` (US East - N. Virginia)
- `us-west-2` (US West - Oregon)

#### Error: "InvalidSignatureException" or "The security token included in the request is invalid"

**Cause**: AWS credentials not configured or expired

**Solution**:
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_here
export AWS_DEFAULT_REGION=us-east-1
```

#### Error: "AccessDeniedException"

**Cause**: Insufficient IAM permissions

**Solution**: Your IAM user/role needs these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateBlueprint",
        "bedrock:GetBlueprint",
        "bedrock:CreateBlueprintVersion",
        "bedrock:CreateDataAutomationProject",
        "bedrock:GetDataAutomationProject",
        "bedrock:InvokeDataAutomationAsync",
        "bedrock:GetDataAutomationStatus"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-input-bucket/*",
        "arn:aws:s3:::your-output-bucket/*",
        "arn:aws:s3:::your-input-bucket",
        "arn:aws:s3:::your-output-bucket"
      ]
    }
  ]
}
```

#### Error: "ValidationException" or schema errors

**Cause**: Blueprint schema format issue

**Solution**: The schema in `blueprint_schema.json` should have this structure:
```json
{
  "blueprintName": "name",
  "type": "DOCUMENT",
  "fields": [
    {
      "fieldName": "FieldName",
      "fieldType": "STRING",
      "fieldDescription": "Description",
      "required": false,
      "multiValue": true
    }
  ]
}
```

### 2. Project Creation Failed

#### Error: "Blueprint info file not found"

**Cause**: Blueprint wasn't created first

**Solution**:
```bash
# Create blueprint first
python3 create_blueprint.py --config config.yaml
```

This creates `blueprint_info.json` which is needed for project creation.

### 3. Document Processing Failed

#### Error: "Project info file not found"

**Cause**: Project wasn't created first

**Solution**:
```bash
# Create project first
python3 create_project.py --config config.yaml
```

#### Error: "NoSuchBucket" or "Access Denied" on S3

**Cause**: S3 bucket doesn't exist or no permissions

**Solution**:
1. Verify bucket exists:
   ```bash
   aws s3 ls s3://your-bucket-name/
   ```

2. Check bucket permissions:
   ```bash
   aws s3api get-bucket-policy --bucket your-bucket-name
   ```

3. Ensure your IAM user has S3 permissions (see above)

#### Error: "Job processing exceeded timeout"

**Cause**: Document processing taking too long

**Solution**: Increase timeout in `config.yaml`:
```yaml
processing:
  timeout: 7200  # Increase to 2 hours
```

#### Error: "Connection timeout" or network errors

**Cause**: Network connectivity issues

**Solution**:
1. Check internet connection
2. Verify AWS region is reachable
3. Check firewall/proxy settings
4. Try a different AWS region (us-east-1 or us-west-2)

### 4. Virtual Environment Issues

#### Error: "Command not found: python3"

**Cause**: Python not installed or not in PATH

**Solution**:
```bash
# Check Python installation
which python3
python3 --version

# If not found, install Python 3.8+
# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-venv python3-pip

# macOS:
brew install python3
```

#### Error: "venv module not found"

**Cause**: Python venv module not installed

**Solution**:
```bash
# Ubuntu/Debian:
sudo apt install python3-venv

# Then run setup again
./setup.sh
```

#### Virtual environment not activating

**Cause**: Not using correct activation command

**Solution**:
```bash
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Verify activation (should show venv in prompt):
which python3  # Should point to venv/bin/python3
```

### 5. Permission Errors

#### Error: "Permission denied" when running scripts

**Cause**: Scripts not executable

**Solution**:
```bash
chmod +x *.sh *.py
```

#### Error: "Permission denied" when creating files

**Cause**: Directory permissions

**Solution**:
```bash
# Check directory permissions
ls -la

# Fix if needed (be careful with this):
chmod u+w .
```

### 6. Import Errors

#### Error: "ModuleNotFoundError: No module named 'yaml'"

**Cause**: PyYAML not installed

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Error: "ImportError: cannot import name 'ClientError'"

**Cause**: boto3/botocore version mismatch

**Solution**:
```bash
# Update boto3
pip install --upgrade boto3 botocore

# Or reinstall
pip uninstall boto3 botocore
pip install -r requirements.txt
```

## Debugging Steps

### Enable Debug Logging

Edit `config.yaml`:
```yaml
logging:
  level: DEBUG
  log_file: document_processing.log
  console_output: true
```

Then check the log:
```bash
tail -f document_processing.log
```

### Test AWS Connectivity

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls

# Test specific bucket
aws s3 ls s3://your-bucket-name/
```

### Test Boto3 BDA Client

```python
import boto3

# Test client creation
try:
    client = boto3.client('bedrock-data-automation', region_name='us-east-1')
    print("✓ BDA client created successfully")
except Exception as e:
    print(f"✗ Error: {e}")

# Test runtime client
try:
    runtime_client = boto3.client('bedrock-data-automation-runtime', region_name='us-east-1')
    print("✓ BDA runtime client created successfully")
except Exception as e:
    print(f"✗ Error: {e}")
```

### Verify Blueprint Creation Manually

```python
import boto3
import json

client = boto3.client('bedrock-data-automation', region_name='us-east-1')

# Simple test schema
schema = {
    "documentStandardExtraction": {
        "granularity": {
            "types": ["DOCUMENT"]
        }
    },
    "documentOutputFormat": {
        "customOutputTypes": [
            {
                "name": "TestField",
                "description": "Test field",
                "type": "STRING"
            }
        ]
    }
}

try:
    response = client.create_blueprint(
        blueprintName='test-blueprint',
        type='DOCUMENT',
        blueprintStage='DEVELOPMENT',
        schema=json.dumps(schema)
    )
    print("✓ Blueprint created:", response['blueprint']['blueprintArn'])
except Exception as e:
    print(f"✗ Error: {e}")
```

## Getting Help

### Check AWS Service Health

Visit: https://status.aws.amazon.com/

Look for "Amazon Bedrock" in your region.

### AWS Documentation

- [BDA User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/bda.html)
- [BDA API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/)
- [Boto3 BDA Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-data-automation.html)

### Verify Boto3 Version

BDA requires boto3 >= 1.34.0:

```bash
pip show boto3
pip show botocore

# Upgrade if needed
pip install --upgrade boto3 botocore
```

### Clean Start

If all else fails, start fresh:

```bash
# Remove virtual environment
rm -rf venv/

# Remove generated files
rm -f blueprint_info.json project_info.json *.log *.csv

# Run setup again
./setup.sh

# Activate venv
source venv/bin/activate

# Validate environment
python3 validate_environment.py

# Try again
./run_pipeline.sh --input-bucket <uri> --output-bucket <uri>
```

## Still Having Issues?

1. **Run the validation script**:
   ```bash
   python3 validate_environment.py
   ```

2. **Check the logs**:
   ```bash
   cat document_processing.log
   ```

3. **Enable debug mode** in `config.yaml`:
   ```yaml
   logging:
     level: DEBUG
   ```

4. **Test each component separately**:
   ```bash
   # Test blueprint creation only
   python3 create_blueprint.py --config config.yaml

   # Test project creation only
   python3 create_project.py --config config.yaml

   # Test document listing only
   python3 process_documents.py --dry-run --input-bucket <uri> --output-bucket <uri>
   ```

5. **Check AWS CloudTrail** for detailed error logs in AWS Console

6. **Verify BDA service is enabled** in your AWS account (some accounts may need to request access)
