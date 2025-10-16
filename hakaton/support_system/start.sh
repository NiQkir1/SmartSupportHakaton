#!/bin/bash
# Universal start script for Linux/Mac

echo "================================"
echo "  T1 SmartSupport System"
echo "================================"
echo ""

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "ERROR: Python not found. Please install Python 3.11+"
    exit 1
fi

echo "Using: $PYTHON_CMD"
echo ""

# Install dependencies
echo "Installing dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt

echo ""
echo "Starting server..."
echo "Open: http://localhost:5000"
echo ""

$PYTHON_CMD app.py

