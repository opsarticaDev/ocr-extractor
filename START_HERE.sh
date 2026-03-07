#!/bin/bash

echo "============================================"
echo " OCRExtractor by OpsArtica"
echo "============================================"

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    exit 1
fi

if [ ! -f "code/.installed" ]; then
    echo "[First Time Setup]"
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then echo "ERROR: Dependency installation failed."; exit 1; fi
    touch code/.installed
    echo "Setup complete!"
fi

mkdir -p inputs outputs
python3 code/validate_install.py
if [ $? -ne 0 ]; then echo "Setup validation failed."; exit 1; fi

echo "Starting OCRExtractor..."
python3 code/ocrextractor.py
chmod +x "$0"
