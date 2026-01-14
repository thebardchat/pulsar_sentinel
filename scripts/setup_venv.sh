#!/bin/bash
# PULSAR SENTINEL - Virtual Environment Setup Script

set -e

echo "==================================="
echo "PULSAR SENTINEL Environment Setup"
echo "==================================="

# Determine Python command
if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3.11+ is required"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/asr
mkdir -p logs

# Copy environment template if .env doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Copying .env.template to .env..."
    cp .env.template .env
    echo "Please edit .env with your configuration"
fi

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo ""
echo "To activate the environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run the server:"
echo "  python -m uvicorn api.server:app --reload"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
