#!/bin/bash

# Knowledge Graph JSON을 Cypher로 변환하는 스크립트

# 사용법 확인
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <json_file> [output_file] [--clear-db] [--no-indexes]"
    echo ""
    echo "Examples:"
    echo "  $0 knowledge_graph.json"
    echo "  $0 knowledge_graph.json output.cypher"
    echo "  $0 knowledge_graph.json output.cypher --clear-db"
    echo "  $0 /path/to/0003_chunked/knowledge_graph.json --clear-db"
    exit 1
fi

# 스크립트 디렉토리
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Python 스크립트 실행
cd "$BACKEND_DIR"
python -m utils.kg_to_cypher "$@"
