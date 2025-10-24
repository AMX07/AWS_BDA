# AWS Bedrock Data Automation - Intelligent Document Processing Pipeline

A complete, production-ready pipeline for extracting structured data from unstructured insurance documents using AWS Bedrock Data Automation (BDA). This pipeline processes various document formats, extracts key entities, and outputs results in CSV format.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Extracted Fields](#extracted-fields)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [AWS Permissions](#aws-permissions)
- [Best Practices](#best-practices)

## Overview

This pipeline extracts the following entities from insurance documents:

- **Websites** (SiteOnForm) - URLs, domain names, and hyperlinked text
- **Company Names** (NameOnForm) - Insurance companies and organizations
- **Logos** (LogoOnForm) - Detected and categorized logos
- **Email Addresses** (EmailOnForm) - All email addresses found
- **Phone Numbers** (PhoneOnForm) - Phone and fax numbers
- **Physical Addresses** (AddressOnForm) - Street addresses and PO boxes
- **Signatures** (SignatureOnForm) - Detected signatures
- **Line of Business** (LOB) - Categorized based on form ID
- **State** (State) - Two-letter state code
- **Language** (Language) - Primary document language

## Features

- ✅ **Batch Processing** - Process multiple documents in parallel
- ✅ **Comprehensive Extraction** - 10 different entity types
- ✅ **Intelligent Form ID Parsing** - Complex LOB categorization based on 229+ series mappings
- ✅ **Error Handling** - Robust retry logic and error recovery
- ✅ **Progress Tracking** - Real-time progress bars and detailed logging
- ✅ **CSV Export** - Structured output with metadata
- ✅ **S3 Integration** - Direct S3 input/output
- ✅ **Configurable** - YAML-based configuration
- ✅ **Production Ready** - Comprehensive error handling and logging

## Architecture

```
┌─────────────────┐
│   S3 Input      │
│   Bucket        │
│  (Documents)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  BDA Blueprint  │◄─── Blueprint Schema (JSON)
│   Definition    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   BDA Project   │
│  Configuration  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Document       │
│  Processing     │◄─── Parallel Batch Processing
│  (Async)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Result          │
│ Aggregation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CSV Export     │
│  to S3          │
└─────────────────┘
```

## Prerequisites

- **Python 3.8+**
- **AWS Account** with Bedrock Data Automation enabled
- **AWS Credentials** configured (via AWS CLI or environment variables)
- **S3 Buckets** for input documents and output results
- **BDA Available Regions**: `us-east-1` or `us-west-2`

### AWS Service Requirements

- AWS Bedrock Data Automation (BDA)
- Amazon S3
- Appropriate IAM permissions (see [AWS Permissions](#aws-permissions))

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AWS_BDA
```

### 2. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Make scripts executable
- Create configuration templates

### 3. Configure AWS Credentials

```bash
# Option 1: Using AWS CLI
aws configure

# Option 2: Using environment variables
cp .env.example .env
# Edit .env with your credentials
```

### 4. Configure the Pipeline

Edit `config.yaml` to customize:
- AWS region
- Processing batch size
- Output format preferences
- Logging level

## Configuration

### config.yaml

```yaml
# AWS Configuration
aws:
  region: us-east-1  # BDA is available in us-east-1 and us-west-2
  profile: default

# Processing Configuration
processing:
  batch_size: 10         # Parallel processing limit
  max_retries: 3         # Retry attempts for failures
  poll_interval: 10      # Seconds between status checks
  timeout: 3600          # Max seconds per document (1 hour)

# Output Configuration
output:
  csv_filename: document_extraction_results.csv
  include_timestamp: true
  include_metadata: true
```

### blueprint_schema.json

Contains the field definitions for document extraction. Each field includes:
- Field name
- Field type
- Detailed extraction instructions
- Multi-value support
- Anti-hallucination rules

## Usage

### Quick Start (Recommended)

Process documents using the complete pipeline:

```bash
./run_pipeline.sh \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/
```

### Step-by-Step Execution

#### 1. Create Blueprint

```bash
python3 create_blueprint.py --config config.yaml
```

This creates a BDA Blueprint with all field definitions and saves blueprint info to `blueprint_info.json`.

#### 2. Create Project

```bash
python3 create_project.py --config config.yaml
```

This creates a BDA Project linked to the blueprint and saves project info to `project_info.json`.

#### 3. Process Documents

```bash
python3 process_documents.py \
  --config config.yaml \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/
```

### Advanced Usage

#### Dry Run (List Documents Without Processing)

```bash
./run_pipeline.sh \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/ \
  --dry-run
```

#### Skip Setup Steps (If Already Completed)

```bash
./run_pipeline.sh \
  --skip-blueprint \
  --skip-project \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/
```

#### Update Existing Blueprint

```bash
python3 create_blueprint.py --config config.yaml --update
```

#### Custom Output Filename

```bash
python3 process_documents.py \
  --config config.yaml \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/ \
  --output-file my_custom_results.csv
```

## Extracted Fields

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **SiteOnForm** | Multi-value | All websites including URLs and hyperlinked text | `www.example.com, OAM` |
| **NameOnForm** | Multi-value | Company names and organizations | `Indiana Farm Bureau Insurance` |
| **LogoOnForm** | Multi-value | Logo categories (comma-separated, no spaces) | `IFBI,UHL` |
| **EmailOnForm** | Multi-value | Email addresses | `info@example.com` |
| **PhoneOnForm** | Multi-value | Phone and fax numbers | `1-833-327-8787, (317) 555-1234` |
| **AddressOnForm** | Multi-value | Physical addresses or PO boxes | `PO Box 6496, Indianapolis, IN 46206-6496` |
| **SignatureOnForm** | Multi-value | Detected signatures | `John Smith` |
| **LOB** | Single | Line of Business category based on form ID | `P&C Underwriting - Commercial` |
| **State** | Single | Two-letter state code | `IN`, `OH` |
| **Language** | Single | Primary language | `English` |

### Special Field Rules

#### LOB (Line of Business)

The LOB field uses a complex mapping system with 229+ series numbers:

- **Form ID Format**: `XXX-YYY` (e.g., `031-077`, `221-054`)
- **Extraction**: Takes digits BEFORE the first hyphen
- **Padding**: Single/double digits padded to 3 digits with leading zeros
- **Critical Rules**:
  - `03-15-02` → series `003` (NOT `031`)
  - `3-150` → series `003` (NOT `315`)
  - `221-054` → series `221`

**Example Mappings**:
- Series `003` → `P&C Underwriting - Commercial`
- Series `031` → `Advertising & Promotions (Brochures, Flyers, etc.)`
- Series `221` → `ESI P&C Auto & Home Lines Only`

#### State Detection

- **IFBI documents** → `IN` (Indiana)
- **ESI documents** (or ESI logo) → `OH` (Ohio)
- **Others** → Extract from document

#### Address Formatting

- **Single address**: `PO Box 6496, Indianapolis, IN 46206-6496`
- **Multiple addresses**: `[Address 1], [Address 2]` (brackets required)
- **Never include** city/state alone without street/PO Box

## Project Structure

```
AWS_BDA/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── config.yaml                    # Main configuration file
├── .env.example                   # Environment variables template
│
├── blueprint_schema.json          # BDA Blueprint definition
│
├── setup.sh                       # Initial setup script
├── run_pipeline.sh               # Complete pipeline runner
│
├── create_blueprint.py           # Create/update BDA Blueprint
├── create_project.py             # Create BDA Project
├── process_documents.py          # Main document processing script
├── utils.py                      # Utility functions
│
├── blueprint_info.json           # Generated: Blueprint metadata
├── project_info.json             # Generated: Project metadata
├── document_processing.log       # Generated: Processing logs
└── document_extraction_results_*.csv  # Generated: Results
```

## Troubleshooting

### Common Issues

#### 1. BDA Service Not Available

```
Error: BDA service not available in region
```

**Solution**: BDA is only available in `us-east-1` and `us-west-2`. Update `config.yaml`:

```yaml
aws:
  region: us-east-1
```

#### 2. Insufficient Permissions

```
Error: AccessDeniedException
```

**Solution**: Ensure your IAM user/role has required permissions (see [AWS Permissions](#aws-permissions))

#### 3. Blueprint Already Exists

```
Warning: Blueprint already exists
```

**Solution**: This is normal. The script will use the existing blueprint. To update:

```bash
python3 create_blueprint.py --update
```

#### 4. S3 Access Denied

```
Error: Access Denied when accessing S3 bucket
```

**Solution**:
- Verify bucket names are correct
- Ensure S3 permissions are configured
- Check bucket is in the same region or has appropriate CORS settings

#### 5. Document Processing Timeout

```
Error: Job processing exceeded timeout
```

**Solution**: Increase timeout in `config.yaml`:

```yaml
processing:
  timeout: 7200  # 2 hours
```

### Debug Mode

Enable detailed logging:

```yaml
logging:
  level: DEBUG
```

## AWS Permissions

### Required IAM Permissions

Your IAM user or role needs the following permissions:

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

### S3 Bucket Policy (Optional)

If using cross-account access or specific bucket policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

## Best Practices

### 1. Organize Input Documents

```
s3://my-bucket/
  ├── documents/
  │   ├── batch1/
  │   ├── batch2/
  │   └── archive/
  └── results/
      ├── 2025-01/
      └── 2025-02/
```

### 2. Use Descriptive Output Filenames

Enable timestamps in `config.yaml`:

```yaml
output:
  include_timestamp: true
```

This generates: `document_extraction_results_20250124_143022.csv`

### 3. Monitor Processing Logs

```bash
tail -f document_processing.log
```

### 4. Batch Processing Strategy

For large document sets:

```yaml
processing:
  batch_size: 10  # Adjust based on your AWS limits
```

### 5. Error Recovery

The pipeline includes automatic retries. Failed documents are logged with error messages in the CSV output.

### 6. Test with Dry Run

Always test with `--dry-run` first:

```bash
./run_pipeline.sh --dry-run \
  --input-bucket s3://my-bucket/documents/ \
  --output-bucket s3://my-bucket/results/
```

### 7. Version Control

Keep track of blueprint and project versions:

```bash
# Blueprint info saved in blueprint_info.json
# Project info saved in project_info.json
```

## Supported Document Formats

- PDF (`.pdf`)
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- TIFF (`.tiff`, `.tif`)

## Output Format

### CSV Structure

```csv
document,SiteOnForm,NameOnForm,LogoOnForm,EmailOnForm,PhoneOnForm,AddressOnForm,SignatureOnForm,LOB,State,Language,s3_uri,processing_status,error_message
doc1.pdf,www.example.com,Company Name,IFBI,info@example.com,1-833-327-8787,PO Box 123,John Smith,P&C Underwriting - Commercial,IN,English,s3://bucket/doc1.pdf,success,
doc2.pdf,,,,,,,,,,,s3://bucket/doc2.pdf,error,Processing timeout
```

## Performance

- **Parallel Processing**: Configurable batch size for concurrent document processing
- **Async Operations**: Non-blocking BDA invocations
- **Progress Tracking**: Real-time progress bars using tqdm
- **Optimized Polling**: Configurable poll intervals to balance responsiveness and API calls

## Support and Contributing

For issues, questions, or contributions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review AWS BDA documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/bda.html
3. Open an issue with detailed logs and configuration

## License

This project is provided as-is for document processing using AWS Bedrock Data Automation.

## Changelog

### Version 1.0.0 (2025-01-24)
- Initial release
- 10 field extraction types
- 229+ LOB series mappings
- Parallel batch processing
- Complete error handling and logging
- S3 integration
- CSV export with metadata

---

**Built with AWS Bedrock Data Automation** 🚀
