#!/bin/bash
# Setup script for AWS Bedrock Data Automation Pipeline

set -e

echo "========================================"
echo "AWS BDA Pipeline Setup"
echo "========================================"

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x create_blueprint.py
chmod +x create_project.py
chmod +x process_documents.py
chmod +x run_pipeline.sh

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your AWS credentials if needed"
fi

echo ""
echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Configure your AWS credentials (aws configure)"
echo "2. Edit config.yaml if needed"
echo "3. Run: ./run_pipeline.sh --help"
echo ""
