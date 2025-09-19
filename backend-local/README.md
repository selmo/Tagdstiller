# Backend Local Analysis Server

This directory provides a standalone FastAPI server that exposes only the
`/local-analysis/knowledge-graph` endpoint from the original backend. Unlike the
full backend, this variant 수행은 **LLM 기반 구조 분석만 실행**하며 Knowledge Graph를
구성하거나 저장하지 않습니다.

## Project layout

```
backend-local/
  backend/                # Copied application modules reused by the slim server
    main.py               # FastAPI entry point for the local-analysis server
    routers/knowledge_graph.py  # LLM 구조 분석 라우터 (KG 미생성)
  README.md               # This guide
  requirements.txt        # Python dependencies (same as backend)
```

## Installation

```bash
cd backend-local
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Running the server

```bash
cd backend-local/backend
uvicorn main:app --reload --port 58000
# or simply run ../start_local_backend.sh
```

The server exposes the following endpoint:

- `POST /local-analysis/knowledge-graph`
- `GET  /local-analysis/knowledge-graph`

Both routes trigger LLM 구조 분석을 수행하고 `llm_analysis` 결과와 분석 산출물 경로를
반환합니다. 나머지 프로젝트/키워드/KG API는 포함되어 있지 않습니다.

### 응답 파일 구조

- `llm_structure_analysis.json`: LLM 분석 본문 (프롬프트 준수 여부 검사 가능)
- `llm_structure_response.json`: API 응답 요약 및 저장된 파일 목록
- 기타 파싱 산출물(`parsing_results.json`, 각 파서별 텍스트 등)이 필요 시 함께 반환됩니다.
