# Backend Local Analysis Server

고급 문서 분석을 위한 독립 실행형 FastAPI 서버입니다. **청크 기반 구조 분석**, **다중 파서 지원**, **LLM 통합 분석**, **고급 OCR 시스템**을 제공하는 완전한 문서 처리 시스템입니다.

## 🎉 최신 업데이트 (2025-11-03)
- **🎚️ 3-Level 추출 깊이 (NEW)**: brief/standard/deep 선택으로 10-80개 엔티티 범위 조절
- **🔁 자동 재시도 (NEW)**: Rate limit 초과 시 exponential backoff로 자동 재시도 (최대 3회)
- **🚀 2-Phase KG 추출**: 엔티티 먼저 추출 → 관계 추출로 **43% 더 많은 엔티티**
- **🔥 청킹 기반 완전 KG 추출**: 구조 단위 분해로 문서 전체 상세 엔티티/관계 추출
- **⛔ 핵심 오류 시 중단**: JSON 파싱 실패, LLM 호출 실패 시 전체 프로세스 즉시 중단
- **🐛 Phase별 디버그**: Phase 1/2 프롬프트, 응답, 파싱 결과 개별 저장
- **🔍 스캔 문서 자동 감지**: 텍스트 밀도 기반 자동 OCR 모드 전환
- **🌏 다국어 OCR 지원**: EasyOCR (한글 최적) + Tesseract (범용)
- **🖼️ 적응형 이미지 전처리**: 다중 전처리 기법으로 OCR 품질 최적화
- **⚡ 스마트 엔진 선택**: auto/easyocr/tesseract 자동 폴백
- **📊 Gemini 안정화**: 비스트리밍 모드로 완전한 응답 보장

## 🚀 주요 기능

### 📄 지능형 문서 처리
- **다중 파서 지원**: PyMuPDF, Docling, python-docx, BeautifulSoup4
- **OCR 통합 파서 (NEW)**: Docling + EasyOCR/Tesseract 자동 조합
  - 스캔 문서 자동 감지 및 전체 페이지 OCR
  - 한글+영문 혼합 텍스트 최적화
  - 적응형 이미지 전처리 (4가지 기법)
- **청크 기반 분석**: 대용량 문서를 구조적 단위로 분할하여 처리
- **자동 청킹**: LLM max_tokens 기반 자동 청킹 결정
- **구조 인식**: 제목, 섹션, 장(Chapter) 단위 경계 보존

### 🧠 LLM 통합 분석
- **다중 LLM 지원**: OpenAI, Gemini, Ollama
- **Gemini 최적화 (NEW)**: 비스트리밍 모드로 안정성 향상
- **자동 재시도 (NEW)**: Rate limit (429) 초과 시 exponential backoff (2s → 4s → 8s)
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

### 🔗 Knowledge Graph (NEW)
- `POST /local-analysis/full-knowledge-graph` - 문서 전체를 Knowledge Graph로 변환 (요약 버전)
- `GET /local-analysis/full-knowledge-graph` - 동일 기능 (GET 방식)
- `POST /local-analysis/full-knowledge-graph-chunked` - 구조 기반 청킹으로 상세 KG 추출 (완전 버전)

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

### Knowledge Graph 생성 (NEW)
```bash
# 기본 사용 (일반 문서)
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "directory": "/output/results",
    "domain": "general"
  }'

# 기술 문서용 KG
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/technical_doc.pdf",
    "directory": "/output/results",
    "domain": "technical",
    "save_format": "all",
    "llm": {
      "provider": "gemini",
      "model": "gemini-2.0-flash-exp",
      "api_key": "your-api-key"
    }
  }'

# 학술 논문용 KG
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/research_paper.pdf",
    "directory": "/output/results",
    "domain": "academic",
    "include_structure": true
  }'

# GET 방식 (간단 호출)
curl -G "http://localhost:8000/local-analysis/full-knowledge-graph" \
  --data-urlencode "file_path=/path/to/document.pdf" \
  --data-urlencode "domain=business" \
  --data-urlencode "save_format=cypher"
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

### Knowledge Graph 출력 (NEW)
```
/output/results/
├── knowledge_graph.json           # Knowledge Graph JSON 형식
├── knowledge_graph.cypher         # Cypher 쿼리 (Neo4j/Memgraph용)
├── knowledge_graph.graphml        # GraphML XML 형식
├── parsing_results.json           # 파싱 결과
├── llm_structure_analysis.json    # 구조 분석 (선택)
├── docling.md                     # Docling 파서 결과
└── pymupdf4llm.md                 # PyMuPDF 파서 결과
```

**knowledge_graph.json 구조:**
```json
{
  "success": true,
  "file_path": "/path/to/document.pdf",
  "domain": "technical",
  "graph": {
    "nodes": [
      {
        "id": "entity_1",
        "type": "Technology",
        "properties": {
          "name": "FastAPI",
          "category": "framework"
        }
      }
    ],
    "edges": [
      {
        "id": "edge_1",
        "source": "entity_1",
        "target": "entity_2",
        "type": "DEPENDS_ON",
        "properties": {
          "relationship_name": "USES",
          "context": "API 구현"
        }
      }
    ]
  },
  "stats": {
    "entity_count": 45,
    "relationship_count": 78,
    "entity_types": {
      "Technology": 15,
      "API": 12,
      "Function": 18
    },
    "relationship_types": {
      "DEPENDS_ON": 25,
      "IMPLEMENTS": 20,
      "USES": 33
    },
    "density": 0.0382
  }
}
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

## 🔍 OCR 시스템 (NEW)

### 개요
스캔된 PDF 문서를 자동으로 감지하고 고품질 OCR을 적용하는 지능형 시스템입니다.

### 주요 특징

#### 1. 스캔 문서 자동 감지
시스템이 텍스트 품질을 자동으로 평가하여 스캔 문서를 감지합니다:
- **텍스트 밀도**: 페이지당 문자 수 측정
- **이미지 태그 비율**: Docling 출력의 이미지 플레이스홀더 개수
- **빈 페이지 감지**: 최소 텍스트만 포함된 페이지 식별
- **자동 모드 전환**: 스캔 문서로 판단 시 전체 페이지 OCR 자동 실행

#### 2. 듀얼 OCR 엔진
- **EasyOCR** (한글 최적화, 권장)
  - 딥러닝 기반 고정밀도 인식
  - 한글+영문 혼합 텍스트 탁월
  - GPU 가속 지원
  - 정확도 높음, 처리 속도 중간

- **Tesseract** (범용, 고속)
  - 전통적인 OCR 엔진
  - 빠른 처리 속도
  - 깨끗한 스캔본에 적합
  - 폴백 옵션으로 사용

- **Auto 모드** (기본값)
  - EasyOCR 우선 시도
  - 실패 시 Tesseract 자동 전환
  - 최적의 밸런스

#### 3. 적응형 이미지 전처리
여러 전처리 기법을 자동으로 시도하여 최상의 결과 선택:
1. **적응형 임계값 처리** (Adaptive Thresholding)
2. **양방향 필터링** (Bilateral Filtering)
3. **형태학적 연산** (Morphological Operations)
4. **선명화 필터** (Sharpening Filter)

### OCR 사용 방법

#### 기본 사용
```bash
# 스캔 문서 자동 감지 및 OCR
curl -X POST "http://localhost:58000/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/scanned.pdf",
    "directory": "/output/results",
    "force_reparse": true
  }'
```

#### OCR 엔진 선택
```bash
# EasyOCR 전용 (한글 문서 권장)
export OCR_ENGINE="easyocr"

# Tesseract 전용 (빠른 처리)
export OCR_ENGINE="tesseract"

# Auto 모드 (기본값)
export OCR_ENGINE="auto"
```

### OCR 설치

#### EasyOCR
```bash
pip install easyocr
# 첫 실행 시 모델 자동 다운로드 (~100MB)
```

#### Tesseract
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
apt-get install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng

# 설치 확인
tesseract --version
tesseract --list-langs | grep -E "kor|eng"
```

### OCR 출력 구조
```
/output/results/
├── docling_ocr/
│   ├── docling_ocr_text.txt          # 전체 OCR 텍스트
│   ├── docling_ocr_metadata.json     # OCR 통계 정보
│   ├── docling_ocr_structure.json    # 문서 구조
│   └── ocr_pages/                    # 페이지별 OCR 결과
│       ├── page_1.txt
│       ├── page_2.txt
│       └── ...
└── docling_ocr.md                    # OCR 텍스트 포함 마크다운
```

### 성능 지표
- **EasyOCR**: ~3-5초/페이지 (한글+영문)
- **Tesseract**: ~1-2초/페이지
- **전처리**: ~0.5-1초/페이지
- **감지 로직**: <0.1초

### 문제 해결

#### EasyOCR 메모리 오류
```python
# GPU 비활성화 (메모리 부족 시)
reader = easyocr.Reader(['ko', 'en'], gpu=False)
```

#### 낮은 OCR 품질
- 이미지 해상도 확인 (300 DPI 권장)
- 원본 스캔 품질 개선
- 전처리 알고리즘 튜닝

#### 느린 처리 속도
- Tesseract 모드 사용 (`OCR_ENGINE=tesseract`)
- GPU 활성화 (EasyOCR, CUDA 필요)
- 병렬 처리 설정

### 추가 정보
상세한 테스트 가이드는 `DOCLING_OCR_TEST_GUIDE.md`를 참조하세요.

## 🔗 Knowledge Graph 시스템 (NEW)

### 개요
문서 내용 전체를 엔티티와 관계로 추출하여 지식 그래프로 변환하는 시스템입니다.

**두 가지 추출 모드:**
1. **요약 버전** (`/full-knowledge-graph`): 문서 전체를 한 번에 분석, 핵심 엔티티/관계 추출
2. **완전 버전** (`/full-knowledge-graph-chunked`): 구조 단위로 청킹하여 모든 엔티티/관계 상세 추출

### 주요 특징

#### 1. 도메인별 맞춤 추출
시스템이 문서 도메인에 따라 최적화된 엔티티와 관계 타입을 사용합니다:

- **General (일반 문서)**:
  - 엔티티: Country, Policy, Demographic, Institution, Impact
  - 관계: ENTERED_PHASE, IMPLEMENTS, CAUSES, PROVIDES

- **Technical (기술 문서)**:
  - 엔티티: Technology, API, Function, Class, Database, Server
  - 관계: DEPENDS_ON, IMPLEMENTS, EXTENDS, USES, CALLS

- **Academic (학술 논문)**:
  - 엔티티: Author, Institution, Research_Method, Theory, Dataset
  - 관계: AUTHORED_BY, CITES, BUILDS_ON, PROVES, SUPPORTS

- **Business (비즈니스 문서)**:
  - 엔티티: Company, Product, Market, Stakeholder, Strategy
  - 관계: COMPETES_WITH, SUPPLIES_TO, PARTNERS_WITH, MANAGES

- **Legal (법률 문서)**:
  - 엔티티: Law, Regulation, Contract, Party, Obligation
  - 관계: GOVERNED_BY, SUBJECT_TO, OBLIGATED_TO, CITES_PRECEDENT

#### 2. 다양한 출력 형식
- **JSON**: 표준 그래프 데이터 형식 (nodes, edges)
- **Cypher**: Neo4j/Memgraph용 CREATE 쿼리
- **GraphML**: 범용 XML 그래프 형식
- **All**: 모든 형식 동시 생성

#### 3. 구조 정보 통합
문서 구조 분석 정보를 Knowledge Graph 추출 과정에 활용하여 더 정확한 엔티티/관계 추출이 가능합니다.

#### 4. 그래프 통계
생성된 Knowledge Graph의 다양한 통계 정보 제공:
- 엔티티 개수 및 타입별 분포
- 관계 개수 및 타입별 분포
- 그래프 밀도 (density)
- 엔티티 타입별 통계

### 사용 방법

#### 기본 사용
```bash
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/document.pdf",
    "domain": "general"
  }'
```

#### 도메인 지정
```bash
# 기술 문서
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -d '{"file_path": "/path/to/tech.pdf", "domain": "technical"}'

# 학술 논문
curl -X POST "http://localhost:8000/local-analysis/full-knowledge-graph" \
  -d '{"file_path": "/path/to/paper.pdf", "domain": "academic"}'
```

#### 출력 형식 선택
```bash
# Cypher 쿼리 생성
curl -G "http://localhost:8000/local-analysis/full-knowledge-graph" \
  --data-urlencode "file_path=/path/to/doc.pdf" \
  --data-urlencode "save_format=cypher"

# 모든 형식 생성
curl -G "http://localhost:8000/local-analysis/full-knowledge-graph" \
  --data-urlencode "file_path=/path/to/doc.pdf" \
  --data-urlencode "save_format=all"
```

### 출력 예시

**knowledge_graph.json**:
```json
{
  "success": true,
  "graph": {
    "nodes": [
      {"id": "tech_1", "type": "Technology", "properties": {...}},
      {"id": "api_1", "type": "API", "properties": {...}}
    ],
    "edges": [
      {"source": "tech_1", "target": "api_1", "type": "PROVIDES", "properties": {...}}
    ]
  },
  "stats": {
    "entity_count": 45,
    "relationship_count": 78,
    "density": 0.0382
  }
}
```

**knowledge_graph.cypher**:
```cypher
CREATE (n:Technology {id: 'tech_1', name: 'FastAPI', category: 'framework'});
CREATE (n:API {id: 'api_1', name: 'REST API', endpoint: '/api/v1'});
MATCH (a {id: 'tech_1'}), (b {id: 'api_1'})
CREATE (a)-[r:PROVIDES {context: '웹 API 제공'}]->(b);
```

### 그래프 데이터베이스 연동

생성된 Cypher 쿼리는 Neo4j 또는 Memgraph에 직접 실행 가능합니다:

```bash
# Neo4j 연동
cat knowledge_graph.cypher | cypher-shell -u neo4j -p password

# Memgraph 연동
cat knowledge_graph.cypher | mgconsole
```

### 🔥 청킹 기반 완전 KG 추출 (NEW)

#### 개요
문서를 구조 단위(Chapter/Section)로 청킹하여 **모든** 엔티티와 관계를 상세하게 추출하는 시스템입니다.

#### 주요 특징
- **구조 기반 청킹**: 단순 크기 분할이 아닌 문서 구조 단위로 분할
- **상세 추출**: 청크당 최소 15-20개 엔티티, 평균 2-3개 관계/엔티티
- **핵심 오류 중단**: LLM 호출 실패, JSON 파싱 실패 시 전체 프로세스 즉시 중단
- **디버그 파일**: 청크별 프롬프트, 응답, 파싱 결과, 오류 상세 정보 자동 저장
- **자동 병합**: 청크별 KG를 지능적으로 병합하여 중복 제거

#### 사용 방법

**기본 사용:**
```bash
FILE_PATH="/Users/selmo/TEMP/0003.pdf"
DIRECTORY="$(dirname "$FILE_PATH")/$(basename "$FILE_PATH" .pdf)_chunked"

curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "'"$FILE_PATH"'",
    "directory": "'"$DIRECTORY"'",
    "domain": "general",
    "max_chunk_tokens": 3000,
    "llm": {
      "provider": "gemini",
      "model": "models/gemini-2.0-flash",
      "api_key": "your-api-key",
      "max_tokens": 8192,
      "temperature": 0
    }
  }'
```

**중요 파라미터:**
- `max_chunk_tokens`: 청크당 최대 토큰 수 (권장: 3000-5000)
- `llm.max_tokens`: LLM 응답 최대 토큰 (Gemini 2.0 Flash: 8192)
- `domain`: 문서 도메인 (`general`, `technical`, `academic`, `business`, `legal`)
- `extraction_level`: 추출 깊이 (`brief`, `standard`, `deep`) - **NEW!**

**추출 레벨 사용 예시:**
```bash
# 빠른 개요 - 핵심 엔티티만 (10-20개)
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "doc.pdf", "extraction_level": "brief"}'

# 기본 분석 - 균형잡힌 추출 (30-50개, 기본값)
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "doc.pdf", "extraction_level": "standard"}'

# 심층 분석 - 완전한 지식 추출 (50-80개)
curl -X POST http://localhost:58000/local-analysis/full-knowledge-graph-chunked \
  -H 'Content-Type: application/json' \
  -d '{"file_path": "doc.pdf", "extraction_level": "deep"}'
```

#### 출력 구조
```
/output_directory/
├── knowledge_graph.json           # 병합된 완전한 KG
├── chunk_kg_debug/                # 청크별 디버그 디렉토리
│   ├── chunk_001_text.txt         # 청크 텍스트
│   ├── chunk_001_prompt.txt       # LLM 프롬프트
│   ├── chunk_001_response.txt     # LLM 원본 응답
│   ├── chunk_001_kg.json          # 파싱된 KG
│   ├── chunk_001_error.txt        # LLM 호출 오류 (실패 시)
│   ├── chunk_001_parse_error.txt  # JSON 파싱 오류 상세 (실패 시)
│   ├── chunk_001_exception.txt    # 예외 정보 (실패 시)
│   ├── chunk_002_text.txt
│   └── ...
└── parsing_results.json           # 파싱 결과
```

#### 오류 처리

시스템은 다음 핵심 오류 발생 시 **즉시 중단**하고 HTTP 500 에러를 반환합니다:

1. **LLM API 키 없음**: `"Gemini API 키가 없습니다"`
2. **LLM 호출 실패**: 네트워크 오류, 타임아웃 등
3. **JSON 파싱 실패**: max_tokens 초과로 응답이 잘린 경우
4. **빈 KG 결과**: 노드와 엣지가 모두 0개

각 오류는 상세한 디버그 파일(`*_error.txt`, `*_parse_error.txt`, `*_exception.txt`)에 기록됩니다.

#### max_tokens 문제 해결

**증상**: "LLM 응답 파싱 결과가 비어있습니다. JSON 형식 오류 또는 max_tokens 초과 가능성"

**원인**: LLM이 긴 JSON 응답을 생성하다가 토큰 제한에 걸려 응답이 중간에 잘림

**해결 방법:**
1. **프롬프트 이미 최적화됨**: 시스템은 8-12개 핵심 엔티티만 추출하도록 조정되어 있음
2. **청크 크기 권장**: `max_chunk_tokens: 3000`이 최적 (테스트 완료)
3. **더 큰 모델 사용 (선택)**: Gemini 1.5 Pro (최대 2M 토큰), GPT-4 Turbo (128K)

#### 성공 예시

```bash
# 성공적인 응답 (최적화된 프롬프트 사용)
{
  "success": true,
  "graph": {
    "nodes": [
      {"id": "chunk_001_node_001", "type": "Organization", "properties": {"name": "국토교통부 도로국"}},
      {"id": "chunk_001_node_002", "type": "Document", "properties": {"name": "도로터널 결로대책 가이드라인"}},
      {"id": "chunk_001_node_003", "type": "Concept", "properties": {"name": "결로"}},
      {"id": "chunk_001_node_004", "type": "Concept", "properties": {"name": "안전 확보"}},
      {"id": "chunk_001_node_005", "type": "Concept", "properties": {"name": "하해저 장대 도로터널"}},
      {"id": "chunk_001_node_006", "type": "Data", "properties": {"name": "1km"}},
      ...  # 총 53개 엔티티
    ],
    "edges": [
      {"source": "chunk_001_node_001", "target": "chunk_001_node_002", "type": "PUBLISHED_BY"},
      {"source": "chunk_001_node_002", "target": "chunk_001_node_003", "type": "ADDRESSES"},
      {"source": "chunk_001_node_002", "target": "chunk_001_node_005", "type": "APPLIES_TO"},
      ...  # 총 43개 관계
    ]
  },
  "stats": {
    "entity_count": 53,
    "relationship_count": 43,
    "entity_types": {"Organization": 3, "Document": 3, "Concept": 34, "Data": 2, "Method": 1, "Location": 6, "Person": 2, "Date": 2},
    "relationship_types": {"PUBLISHED_BY": 1, "ADDRESSES": 1, "CAUSES": 1, "APPLIES_TO": 2, "MITIGATES": 1, ...},
    "density": 0.0156
  },
  "chunking_stats": {
    "total_chunks": 1,
    "successful_extractions": 1,
    "max_chunk_tokens": 3000
  }
}
```

**2-Phase 추출 시스템 (2025-11-03 최종):**
- **Phase 1 (엔티티 추출)**: 30-60개 포괄적 엔티티 추출, 관계 없음
- **Phase 2 (관계 추출)**: Phase 1 엔티티 ID 참조하여 관계만 추출
- **장점**:
  - 엔티티 수 43% 증가 (관계 JSON 없어서 토큰 절약)
  - 관계 정확도 향상 (이미 추출된 엔티티 참조)
  - LLM 호출 2회지만 총 시간은 비슷 (각 호출이 더 간단)
- **실제 결과**:
  - 작은 문서 (3K 토큰): 67개 엔티티, 44개 관계
  - 중간 문서 (4K 토큰): 60개 엔티티, 47개 관계
- **핵심**: 단계 분리 → 각 단계 최적화 → 전체 효율 극대화

**3-Level 추출 깊이 (NEW 2025-11-03):**
- **brief (간략)**: 10-20개 핵심 엔티티만 추출 (빠른 분석, 주요 주제만)
- **standard (기본)**: 30-50개 균형잡힌 엔티티 추출 (기본값, 권장)
- **deep (심층)**: 100-300+개 포괄적 엔티티 추출 (상세 분석, 모든 세부 사항)
- **사용법**: API 요청에 `"extraction_level": "brief"/"standard"/"deep"` 추가
- **선택 기준**:
  - 빠른 개요 필요 시 → `brief`
  - 일반적인 분석 → `standard` (기본값)
  - 완전한 지식 추출 필요 시 → `deep` (기존 239개 수준)

### 활용 시나리오

1. **문서 네트워크 분석**: 여러 문서의 KG를 통합하여 문서 간 연결 관계 파악
2. **지식 검색**: 그래프 쿼리를 통한 복잡한 지식 탐색
3. **추천 시스템**: 엔티티 관계 기반 관련 문서/개념 추천
4. **시각화**: Cytoscape, Gephi 등으로 지식 그래프 시각화
5. **온톨로지 구축**: 도메인 특화 지식 온톨로지 자동 생성
6. **완전 지식 추출**: 청킹 기반 시스템으로 문서의 모든 개념과 관계를 빠짐없이 추출

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

## 📚 추가 문서

- **[EXTRACTION_LEVELS.md](EXTRACTION_LEVELS.md)**: 3-Level 엔티티 추출 시스템 상세 문서
  - Brief/Standard/Deep 각 레벨의 특징과 사용법
  - 기술적 구현 세부사항
  - API 사용 예시 및 테스트 방법
- **[DOCLING_OCR_TEST_GUIDE.md](DOCLING_OCR_TEST_GUIDE.md)**: Docling OCR 통합 테스트 가이드
- **[LOCAL_ANALYSIS_USAGE.md](LOCAL_ANALYSIS_USAGE.md)**: 로컬 파일 분석 API 사용법
