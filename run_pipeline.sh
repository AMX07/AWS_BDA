#!/bin/bash
# Complete pipeline runner - Creates blueprint, project, and processes documents

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Complete AWS Bedrock Data Automation Pipeline

OPTIONS:
    --input-bucket BUCKET       S3 URI or bucket for input documents (required)
    --output-bucket BUCKET      S3 URI or bucket for output CSV (required)
    --config FILE               Path to config file (default: config.yaml)
    --skip-blueprint           Skip blueprint creation
    --skip-project             Skip project creation
    --dry-run                  List documents without processing
    --help                     Show this help message

EXAMPLES:
    # Full pipeline with S3 URIs
    $0 --input-bucket s3://my-bucket/documents/ --output-bucket s3://my-bucket/results/

    # Using bucket names only
    $0 --input-bucket my-input-bucket --output-bucket my-output-bucket

    # Skip setup steps if already done
    $0 --skip-blueprint --skip-project --input-bucket my-bucket --output-bucket my-bucket

    # Dry run to see what documents will be processed
    $0 --dry-run --input-bucket my-bucket --output-bucket my-bucket

EOF
    exit 1
}

# Parse command line arguments
INPUT_BUCKET=""
OUTPUT_BUCKET=""
CONFIG="config.yaml"
SKIP_BLUEPRINT=false
SKIP_PROJECT=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-bucket)
            INPUT_BUCKET="$2"
            shift 2
            ;;
        --output-bucket)
            OUTPUT_BUCKET="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --skip-blueprint)
            SKIP_BLUEPRINT=true
            shift
            ;;
        --skip-project)
            SKIP_PROJECT=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [ -z "$INPUT_BUCKET" ] || [ -z "$OUTPUT_BUCKET" ]; then
    print_error "Input and output buckets are required"
    usage
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    print_info "Activating virtual environment..."
    source venv/bin/activate
fi

echo ""
echo "========================================"
echo "AWS BDA DOCUMENT PROCESSING PIPELINE"
echo "========================================"
echo ""
print_info "Input bucket: $INPUT_BUCKET"
print_info "Output bucket: $OUTPUT_BUCKET"
print_info "Config file: $CONFIG"
echo ""

# Step 1: Create Blueprint
if [ "$SKIP_BLUEPRINT" = false ]; then
    print_info "Step 1/3: Creating or updating Blueprint..."
    if python3 create_blueprint.py --config "$CONFIG"; then
        print_info "Blueprint setup completed"
    else
        print_error "Blueprint creation failed"
        exit 1
    fi
    echo ""
else
    print_warning "Skipping blueprint creation"
fi

# Step 2: Create Project
if [ "$SKIP_PROJECT" = false ]; then
    print_info "Step 2/3: Creating or updating Project..."
    if python3 create_project.py --config "$CONFIG"; then
        print_info "Project setup completed"
    else
        print_error "Project creation failed"
        exit 1
    fi
    echo ""
else
    print_warning "Skipping project creation"
fi

# Step 3: Process Documents
print_info "Step 3/3: Processing documents..."

PROCESS_CMD="python3 process_documents.py --config $CONFIG --input-bucket $INPUT_BUCKET --output-bucket $OUTPUT_BUCKET"

if [ "$DRY_RUN" = true ]; then
    PROCESS_CMD="$PROCESS_CMD --dry-run"
fi

if $PROCESS_CMD; then
    echo ""
    echo "========================================"
    echo -e "${GREEN}PIPELINE COMPLETED SUCCESSFULLY${NC}"
    echo "========================================"
    exit 0
else
    echo ""
    echo "========================================"
    echo -e "${RED}PIPELINE FAILED${NC}"
    echo "========================================"
    exit 1
fi
