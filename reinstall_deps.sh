#!/bin/bash

echo "========================================="
echo "Clean Reinstall of Python Dependencies"
echo "========================================="

# Check if venv is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Error: Virtual environment not activated!"
    echo "Run: source venv/bin/activate"
    exit 1
fi

echo ""
echo "1. Clearing pip cache..."
pip cache purge

echo ""
echo "2. Uninstalling existing packages..."
pip freeze | xargs pip uninstall -y

echo ""
echo "3. Reinstalling from requirements.txt..."
pip install -r backend/requirements.txt --no-cache-dir

echo ""
echo "========================================="
echo "✓ Dependencies reinstalled successfully!"
echo "========================================="
echo ""
echo "Verify with: pip list"