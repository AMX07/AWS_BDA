# Quick Start Guide - AWS BDA Pipeline

Get started with the AWS Bedrock Data Automation Pipeline in 5 minutes!

## Prerequisites Check

Before starting, ensure you have:

- [ ] AWS Account with BDA access
- [ ] AWS credentials (Access Key + Secret Key)
- [ ] Python 3.8 or higher
- [ ] Documents in an S3 bucket (or ready to upload)
- [ ] Internet connection

## Step-by-Step Setup

### Step 1: Clone and Setup (2 minutes)

```bash
# Navigate to the project directory
cd AWS_BDA

# Run the setup script (creates virtual environment and installs dependencies)
chmod +x setup.sh
./setup.sh

# Activate the virtual environment
source venv/bin/activate
```

**Expected output**: Virtual environment created, dependencies installed.

### Step 2: Configure AWS Credentials (1 minute)

Choose one method:

**Option A: AWS CLI (Recommended)**
```bash
aws configure
# Enter:
#   AWS Access Key ID: your_access_key
#   AWS Secret Access Key: your_secret_key
#   Default region: us-east-1
#   Default output format: json
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

### Step 3: Update Configuration (30 seconds)

Edit `config.yaml` if needed:

```yaml
aws:
  region: us-east-1  # Must be us-east-1 or us-west-2
  profile: default

processing:
  batch_size: 10    # Adjust based on your needs
```

### Step 4: Validate Environment (30 seconds)

```bash
# Make validation script executable
chmod +x validate_environment.py

# Run validation
python3 validate_environment.py
```

**Expected output**: All checks should pass ✓

If any checks fail, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Step 5: Prepare Your Documents (1 minute)

Upload documents to S3 (if not already there):

```bash
# Create a bucket (if needed)
aws s3 mb s3://my-document-bucket

# Upload documents
aws s3 cp /path/to/documents/ s3://my-document-bucket/input/ --recursive

# List to verify
aws s3 ls s3://my-document-bucket/input/
```

**Supported formats**: PDF, PNG, JPEG, TIFF

### Step 6: Run the Pipeline! (Variable time)

```bash
# Make pipeline executable
chmod +x run_pipeline.sh

# Run with your S3 URIs
./run_pipeline.sh \
  --input-bucket s3://my-document-bucket/input/ \
  --output-bucket s3://my-document-bucket/output/
```

**What happens**:
1. ✓ Creates BDA Blueprint with field definitions (~30 seconds)
2. ✓ Creates BDA Project (~30 seconds)
3. ✓ Scans S3 for documents (~5 seconds)
4. ✓ Processes documents in parallel (~1-5 minutes per document)
5. ✓ Exports results to CSV (~5 seconds)
6. ✓ Uploads CSV to S3 (~5 seconds)

## First Run Example

Here's a complete first-time setup:

```bash
# 1. Setup
cd AWS_BDA
./setup.sh
source venv/bin/activate

# 2. Configure AWS
aws configure
# Enter your credentials and region: us-east-1

# 3. Validate
python3 validate_environment.py

# 4. Run pipeline
./run_pipeline.sh \
  --input-bucket s3://my-docs/insurance-forms/ \
  --output-bucket s3://my-docs/results/

# 5. Check results
aws s3 ls s3://my-docs/results/
```

## Expected Results

### Console Output

```
========================================
AWS BDA DOCUMENT PROCESSING PIPELINE
========================================

Input location: s3://my-docs/insurance-forms/
Output location: s3://my-docs/results/

Step 1/3: Creating or updating Blueprint...
Blueprint created successfully
Blueprint ARN: arn:aws:bedrock:us-east-1:123456789012:blueprint/intelligent-document-extraction

Step 2/3: Creating or updating Project...
Project created successfully
Project ARN: arn:aws:bedrock:us-east-1:123456789012:project/document-processing-project

Step 3/3: Processing documents...
Found 10 documents to process
Processing documents: 100%|████████████| 10/10 [00:45<00:00,  4.5s/doc]

Exporting 10 results to CSV...
Results exported successfully to: document_extraction_results_20250124_153022.csv

Uploading results to: s3://my-docs/results/document_extraction_results_20250124_153022.csv
Upload completed successfully

========================================
PIPELINE COMPLETED SUCCESSFULLY
Results available at: s3://my-docs/results/document_extraction_results_20250124_153022.csv
========================================
```

### Output CSV

The pipeline generates a CSV file with columns:

| document | SiteOnForm | NameOnForm | ... | LOB | State | Language | processing_status |
|----------|------------|------------|-----|-----|-------|----------|-------------------|
| form1.pdf | www.example.com | Company A | ... | P&C Underwriting | IN | English | success |
| form2.pdf | | Company B | ... | Life Insurance | OH | English | success |

## Subsequent Runs

After the first run, you can skip blueprint/project creation:

```bash
./run_pipeline.sh \
  --skip-blueprint \
  --skip-project \
  --input-bucket s3://my-docs/new-batch/ \
  --output-bucket s3://my-docs/results/
```

## Dry Run (Test Mode)

Test without actually processing:

```bash
./run_pipeline.sh \
  --dry-run \
  --input-bucket s3://my-docs/insurance-forms/ \
  --output-bucket s3://my-docs/results/
```

This will list all documents that would be processed without actually processing them.

## Common First-Time Issues

### Issue: "No module named 'boto3'"

**Fix**:
```bash
source venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt
```

### Issue: "UnrecognizedClientException"

**Fix**: Wrong AWS region. BDA only works in `us-east-1` or `us-west-2`.

Update `config.yaml`:
```yaml
aws:
  region: us-east-1
```

### Issue: "AccessDeniedException"

**Fix**: Your AWS user needs permissions. Attach this policy to your IAM user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "*"
    }
  ]
}
```

### Issue: "Bucket does not exist"

**Fix**: Create the bucket first:
```bash
aws s3 mb s3://my-document-bucket
```

## Next Steps

Once your first run is successful:

1. **Review Results**: Download and inspect the CSV
   ```bash
   aws s3 cp s3://my-docs/results/document_extraction_results_*.csv ./
   ```

2. **Adjust Configuration**: Fine-tune `config.yaml` for your needs

3. **Process More Documents**: Run pipeline on different document batches

4. **Automate**: Set up scheduled runs using cron or AWS Lambda

5. **Scale Up**: Increase `batch_size` for faster parallel processing

## Getting Help

- **Environment Issues**: Run `python3 validate_environment.py`
- **Pipeline Errors**: Check `document_processing.log`
- **Detailed Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **AWS Issues**: Check AWS CloudTrail logs

## Summary

To get started quickly:

```bash
# One-time setup
./setup.sh && source venv/bin/activate
aws configure
python3 validate_environment.py

# Process documents
./run_pipeline.sh --input-bucket <s3-uri> --output-bucket <s3-uri>
```

That's it! Your intelligent document processing pipeline is ready to use. 🚀
