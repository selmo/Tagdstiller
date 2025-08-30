#!/bin/bash

# Document Structure Extraction Test

echo "=== Document Structure Extraction Test ==="
echo ""

PORT=${PORT:-8001}
echo "Port: $PORT"
echo ""

# 1. Create a test document with clear structure
echo "Creating test document with structure..."
cat > /tmp/test_structure.md << 'EOF'
# 1. Introduction

This document demonstrates structure extraction capabilities.

## 1.1 Background

Some background information here.

### 1.1.1 Historical Context

Detailed historical information.

## 1.2 Objectives

The main objectives are:
- First objective
- Second objective
- Third objective

# 2. Methodology

## 2.1 Data Collection

Table 1: Sample Data
| Column A | Column B | Column C |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |

## 2.2 Analysis Methods

Figure 1: Analysis Flow Chart
(Imagine a flow chart here)

# 3. Results

The results show significant findings[1].

## 3.1 Main Findings

As shown in Table 2 and Figure 2:
- Finding 1
- Finding 2

# 4. Conclusion

In conclusion, this study demonstrates...

## References

[1] Smith, J. (2024). "Sample Study"
[2] Johnson, A. (2023). "Another Study"

## Appendix

Additional notes and footnotes[^1].

[^1]: This is a footnote.
EOF

echo "Test document created: /tmp/test_structure.md"
echo ""

# 2. Extract metadata with structure
echo "Extracting metadata with document structure:"
curl -s "http://localhost:$PORT/local-analysis/metadata?file_path=/tmp/test_structure.md" | python -m json.tool
echo ""

echo "=== Test Complete ==="