#!/bin/bash
echo "Build script для PriceSmart"
pip install -r requirements.txt 2>/dev/null || echo "No requirements to install"