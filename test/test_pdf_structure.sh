#!/bin/bash

# Test PDF structure extraction

echo "=== Testing PDF Document Structure Extraction ==="
echo ""

PORT=${PORT:-8001}

# 1. Change to finance directory
echo "1. Changing to finance directory..."
curl -s -X POST "http://localhost:$PORT/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance"}' | python -m json.tool
echo ""

# 2. Check current directory
echo "2. Current directory:"
curl -s "http://localhost:$PORT/local-analysis/config/current-directory" | python -m json.tool | head -20
echo ""

# 3. Extract metadata from PDF
echo "3. Extracting metadata from KIFVIP2013-10.pdf:"
curl -s "http://localhost:$PORT/local-analysis/metadata?file_path=KIFVIP2013-10.pdf" | python -m json.tool | grep -A 30 '"document_structure"'
echo ""

echo "=== Test Complete ==="