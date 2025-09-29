# Backend Local Analysis Server

고급 문서 분석을 위한 독립 실행형 FastAPI 서버입니다. **청크 기반 구조 분석**, **다중 파서 지원**, **LLM 통합 분석**을 제공하는 완전한 문서 처리 시스템입니다.

## 🚀 주요 기능

### 📄 지능형 문서 처리
- **다중 파서 지원**: PyMuPDF, Docling, python-docx, BeautifulSoup4
- **청크 기반 분석**: 대용량 문서를 구조적 단위로 분할하여 처리
- **자동 청킹**: LLM max_tokens 기반 자동 청킹 결정
- **구조 인식**: 제목, 섹션, 장(Chapter) 단위 경계 보존

### 🧠 LLM 통합 분석
- **다중 LLM 지원**: OpenAI, Gemini, Ollama
- **스마트 토큰 관리**: 동적 문서 크기 조정 및 토큰 최적화
- **마크다운 지원**: 마크다운 형식 문서 구조 정확한 해석
- **오류 복구**: LLM 호출 실패 시 자동 폴백

### 📊 분석 결과 관리
- **개별 로깅**: 각 청크별 독립적인 프롬프트 및 로그 파일
- **상세 보고서**: 청크 분석 통계 및 처리 성능 리포트
- **파일 추적**: 생성된 모든 파일의 경로 자동 기록

## 📁 프로젝트 구조

```
backend-local/
├── backend/
│   ├── main.py                    # FastAPI 서버 진입점
│   ├── routers/
│   │   └── knowledge_graph.py     # 문서 분석 API 라우터
│   ├── services/
│   │   ├── document_chunker.py    # 구조적 문서 분할
│   │   ├── chunk_analyzer.py      # 청크 단위 분석
│   │   ├── chunk_prompt_manager.py # 청크별 프롬프트 관리
│   │   └── local_file_analyzer.py # LLM 기반 분석
│   └── prompts/
│       └── templates.py           # 분석용 프롬프트 템플릿
├── README.md                      # 이 문서
└── start_local_backend.sh        # 서버 실행 스크립트
```

## ⚡ 설치 및 실행

### 설치
```bash
cd backend-local
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 서버 실행
```bash
# 방법 1: 직접 실행
cd backend-local/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 방법 2: 스크립트 사용
./start_local_backend.sh
```

서버가 실행되면 http://localhost:8000 에서 접근 가능합니다.

## 🌐 API 엔드포인트

### 📋 기본 정보
- `GET /` - 서버 상태 확인

### 📄 문서 분석
- `POST /local-analysis/knowledge-graph` - 완전한 구조 분석 (청킹 + LLM)
- `GET /local-analysis/knowledge-graph` - 동일 기능 (GET 방식)

## 📝 사용 예시

### 기본 분석
```bash
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "directory": "/output/results"
  }'
```

### 고급 옵션
```bash
curl -X POST "http://localhost:8000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/large_document.pdf",
    "directory": "/output/results",
    "use_chunking": true,
    "max_chunk_size": 30000,
    "llm": {
      "provider": "gemini",
      "model": "gemini-2.0-flash-exp",
      "max_tokens": 8000,
      "api_key": "your-api-key"
    },
    "analysis_types": ["structure", "summary", "keywords"]
  }'
```

### GET 방식 (간단 분석)
```bash
curl -G "http://localhost:8000/local-analysis/knowledge-graph" \
  --data-urlencode "file_path=/path/to/document.pdf" \
  --data-urlencode "directory=/output/results"
```

## 📊 출력 파일 구조

### 단일 문서 분석
```
/output/results/
├── document_analysis.json         # 종합 분석 결과
├── llm_structure_analysis.json    # LLM 구조 분석
├── llm_structure_response.json    # API 응답 요약
├── parsing_results.json           # 파싱 결과
├── docling.md                     # Docling 파서 결과 (마크다운)
└── pymupdf4llm.md                 # PyMuPDF 파서 결과 (마크다운)
```

### 청킹 분석 (대용량 문서)
```
/output/results/
├── document_analysis.json         # 종합 분석 결과
├── chunk_analysis/                # 청킹 분석 디렉토리
│   ├── chunk_analysis_report.json # 청킹 분석 보고서
│   ├── chunk_structure.json       # 문서 구조 정보
│   ├── chunks_text/               # 청크 텍스트 파일들
│   │   ├── chunk_1.txt
│   │   ├── chunk_2.txt
│   │   └── ...
│   ├── chunks_prompts/            # 청크별 프롬프트
│   │   ├── chunk_1_prompt.txt
│   │   ├── chunk_2_prompt.txt
│   │   └── ...
│   └── chunks_logs/               # 청크별 실행 로그
│       ├── chunk_1_executions.jsonl
│       ├── chunk_2_executions.jsonl
│       └── ...
└── saved_files.json              # 생성된 파일 목록
```

## ⚙️ 설정 옵션

### LLM 설정
- **provider**: `"openai"`, `"gemini"`, `"ollama"`
- **model**: LLM 모델명
- **max_tokens**: 최대 토큰 수 (청킹 기준값)
- **temperature**: 생성 온도 (기본: 0.2)
- **api_key**: API 키

### 청킹 옵션
- **use_chunking**: 강제 청킹 활성화 (기본: false, 자동 결정)
- **max_chunk_size**: 청크 최대 크기 (기본: 50000)
- **analysis_types**: 분석 타입 배열

### 파일 처리 옵션
- **force_reparse**: 강제 재파싱
- **force_reanalyze**: 강제 재분석
- **directory**: 출력 디렉토리 경로

## 🔧 환경 변수

```bash
# LLM API 키 설정
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"

# 오프라인 모드 (외부 API 호출 스킵)
export OFFLINE_MODE=true
export SKIP_EXTERNAL_CHECKS=true
```

## 🎯 특징 및 장점

### 📈 성능 최적화
- **자동 청킹**: 문서 크기와 LLM 토큰 한계를 고려한 지능형 분할
- **병렬 처리**: 청크별 독립적인 LLM 호출로 처리 속도 향상
- **캐시 활용**: 중복 분석 방지를 위한 결과 캐싱

### 🛡️ 안정성
- **오류 복구**: LLM 호출 실패 시 자동 재시도 및 폴백
- **상세 로깅**: 모든 처리 단계의 상세 로그 기록
- **파일 추적**: 생성된 모든 파일의 경로 자동 기록

### 🔍 정확성
- **구조 보존**: 문서의 논리적 구조를 유지한 청킹
- **컨텍스트 유지**: 섹션 경계를 넘나드는 내용 혼재 방지
- **다중 검증**: 여러 파서의 결과를 종합한 신뢰성 있는 분석
